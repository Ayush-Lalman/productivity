#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, json, threading, time, tempfile, subprocess, os
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".local/bin"))
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from quiz.core import quota, stats as statsmod
from quiz.core.ollama import grade_answer, roast
from quiz.core.text_viewer import show_text

QUIZ_QUEUE = Path.home() / ".local/share/quiz-daemon/pending_question.json"

def load_json(path, default):
    try:
        if path.exists(): return json.loads(path.read_text())
    except: pass
    return default

class QuizWindow(QMainWindow):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.time_left = q.get("time_limit", 600)
        self.submitted = False
        self.closed_early = False
        self.setWindowTitle("Quiz")
        self.setMinimumSize(600, 500)
        
        # Show passage in popup window if present
        passage = q.get("passage")
        if passage:
            show_text(passage, f"Passage - {q.get('topic', 'Extract')}")
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Question
        raw_question = q.get("question", "No question")
        cleaned_question = self.clean_text(raw_question)
        ql = QLabel(cleaned_question)
        ql.setWordWrap(True)
        ql.setStyleSheet("font-size:14px; padding:10px; background:#313244; border-radius:8px;")
        layout.addWidget(ql)
        
        # Answer area
        self.answer = QTextEdit()
        self.word_count_label = QLabel("Words: 0")
        self.word_count_label.setStyleSheet("color: #6c7086; font-size: 11px; font-style: italic;")
        layout.addWidget(self.word_count_label)
        self.answer.textChanged.connect(self.update_word_count)
        self.word_target = q.get("word_target", 0)
        if self.word_target:
            self.word_count_label.setText(f"Words: 0 / {self.word_target}")
        self.answer.setPlaceholderText("Type your answer here...")
        layout.addWidget(self.answer)
        
        # Buttons
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("Copy Q&A")
        copy_btn.clicked.connect(self.copy_all)
        btn_layout.addWidget(copy_btn)
        self.submit_btn = QPushButton("Submit")
        self.submit_btn.clicked.connect(self.submit)
        btn_layout.addWidget(self.submit_btn)
        report_btn = QPushButton("Report")
        report_btn.clicked.connect(self.show_report)
        btn_layout.addWidget(report_btn)
        layout.addLayout(btn_layout)
        
        self.status = QLabel("Ready")
        layout.addWidget(self.status)
        
        # Timer
        self.timer_label = QLabel(self._fmt(self.time_left))
        self.timer_label.setStyleSheet("font-size:16px; font-weight:bold;")
        layout.addWidget(self.timer_label)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
    
    def closeEvent(self, event):
        if not self.submitted:
            self.closed_early = True
            self.timer.stop()
            quota.blank(high_stakes=self.q.get("high_stakes", False))
            statsmod.record_result(
                self.q.get("subject"), 
                self.q.get("topic", ""), 
                self.q.get("section", ""), 
                False, 
                True
            )
            print("[GUI] Window closed without submission — blank penalty applied")
        event.accept()
    
    def clean_text(self, text):
        if not text:
            return ""
        import re
        cleaned = re.sub(r'[^a-zA-Z0-9\s\.\,\!\?\'\"]', ' ', str(text))
        cleaned = re.sub(r'\s+', ' ', cleaned)
        if len(cleaned.strip()) < 10:
            return "[Question text corrupted]"
        return cleaned.strip()
    
    def copy_all(self):
        question = self.q.get("question", "No question")
        answer = self.answer.toPlainText()
        subject = self.q.get("subject", "Unknown")
        topic = self.q.get("topic", "Unknown")
        feedback = self.status.text()
        full_text = f"Subject: {subject} - {topic}\n\nQuestion: {question}\n\nMy Answer:\n{answer}\n\nFeedback:\n{feedback}\n\n---"
        clipboard = QApplication.clipboard()
        clipboard.setText(full_text)
        self.status.setText("Copied to clipboard!")
        self.status.setStyleSheet("color:#a6e3a1")
        QTimer.singleShot(2000, lambda: self.status.setText("Ready"))
    
    def update_word_count(self):
        if hasattr(self, "answer"):
            text = self.answer.toPlainText()
            words = len(text.split())
            if hasattr(self, "word_count_label"):
                self.word_count_label.setText(f"Words: {words}")
                if hasattr(self, "word_target") and self.word_target:
                    target_min = self.word_target - 50
                    target_max = self.word_target + 50
                    if words < target_min:
                        self.word_count_label.setStyleSheet("color: #f38ba8; font-size: 11px;")
                    elif words > target_max:
                        self.word_count_label.setStyleSheet("color: #fab387; font-size: 11px;")
                    else:
                        self.word_count_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
                else:
                    self.word_count_label.setStyleSheet("color: #6c7086; font-size: 11px;")
    
    def _fmt(self, s):
        return f"{s//60}:{s%60:02d}"
    
    def _tick(self):
        if self.submitted:
            return
        self.time_left -= 1
        self.timer_label.setText(self._fmt(self.time_left))
        if self.time_left <= 30:
            self.timer_label.setStyleSheet("color:#f38ba8;font-size:16px;font-weight:bold;")
        if self.time_left <= 0:
            self.submit(timed_out=True)
    
    def submit(self, timed_out=False):
        if self.submitted:
            return
        self.submitted = True
        self.timer.stop()
        self.submit_btn.setEnabled(False)
        
        answer = self.answer.toPlainText().strip()
        blank = not answer or timed_out
        
        if blank:
            quota.blank(high_stakes=self.q.get("high_stakes", False))
            statsmod.record_result(self.q.get("subject"), self.q.get("topic",""), self.q.get("section",""), False, True)
            self.status.setText("Blank answer! -40 min")
            self.status.setStyleSheet("color:#f38ba8")
        else:
            self.status.setText("Grading...")
            result = grade_answer(
                question=self.q.get("question"),
                answer=answer,
                correct_answer=self.q.get("answer"),
                expected_keywords=self.q.get("expected_keywords"),
                practical=self.q.get("type") == "practical"
            )
            correct = result.get("correct", False)
            if correct:
                quota.correct(high_stakes=self.q.get("high_stakes", False))
                statsmod.record_result(self.q.get("subject"), self.q.get("topic",""), self.q.get("section",""), True, False)
                self.status.setText("Correct! +20 min")
                self.status.setStyleSheet("color:#a6e3a1")
            else:
                quota.wrong(high_stakes=self.q.get("high_stakes", False))
                statsmod.record_result(self.q.get("subject"), self.q.get("topic",""), self.q.get("section",""), False, False)
                self.status.setText("Wrong! -10 min")
                self.status.setStyleSheet("color:#f38ba8")
    
    def show_report(self):
        QMessageBox.information(self, "Report", "Check ~/.local/share/quiz-daemon/ for stats")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    q = load_json(QUIZ_QUEUE, None)
    if not q:
        print("No pending question")
        sys.exit(0)
    win = QuizWindow(q)
    win.show()
    sys.exit(app.exec())
