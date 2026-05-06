#!/usr/bin/env python3
"""
Question History Logger - Stores past questions for offline review
"""

import json
from pathlib import Path
from datetime import datetime

LOG_DIR = Path.home() / ".local/share/quiz-daemon/history"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_question(question_data):
    """Save a question to the history log"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOG_DIR / f"question_{timestamp}.json"
        
        # Add timestamp to question data
        question_data["logged_at"] = timestamp
        question_data["logged_at_readable"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, 'w') as f:
            json.dump(question_data, f, indent=2)
        
        # Also append to a daily log for easy browsing
        daily_log = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        with open(daily_log, 'a') as f:
            f.write(json.dumps(question_data) + '\n')
        
        print(f"[logger] Saved question to {log_file.name}")
        return True
    except Exception as e:
        print(f"[logger] Error: {e}")
        return False

def get_recent_questions(limit=10):
    """Get the most recent questions"""
    questions = []
    for log_file in sorted(LOG_DIR.glob("question_*.json"), reverse=True)[:limit]:
        try:
            with open(log_file, 'r') as f:
                questions.append(json.load(f))
        except:
            pass
    return questions

def get_today_questions():
    """Get all questions from today"""
    today = datetime.now().strftime("%Y-%m-%d")
    daily_log = LOG_DIR / f"{today}.jsonl"
    if not daily_log.exists():
        return []
    
    questions = []
    with open(daily_log, 'r') as f:
        for line in f:
            try:
                questions.append(json.loads(line.strip()))
            except:
                pass
    return questions

def view_last_question():
    """Display the last asked question"""
    questions = get_recent_questions(1)
    if questions:
        q = questions[0]
        print("=" * 60)
        print(f"LAST QUESTION ({q.get('logged_at_readable', 'Unknown')})")
        print("=" * 60)
        print(f"Subject: {q.get('subject', 'N/A')}")
        print(f"Topic: {q.get('topic', 'N/A')}")
        print(f"Paper: {q.get('paper', 'N/A')}")
        print(f"Difficulty: {q.get('difficulty', 'N/A')}")
        print("-" * 60)
        print("QUESTION:")
        print(q.get('question', 'N/A')[:500])
        if q.get('diagram') or q.get('visual_image'):
            print("-" * 60)
            print("NOTE: This question had a diagram/image")
        print("=" * 60)
    else:
        print("No questions logged yet")

def list_questions():
    """List all logged questions with timestamps"""
    questions = get_recent_questions(20)
    if not questions:
        print("No questions found")
        return
    
    print(f"{'TIMESTAMP':<20} {'SUBJECT':<15} {'TOPIC':<30}")
    print("-" * 65)
    for q in questions:
        ts = q.get('logged_at_readable', 'Unknown')[:16]
        subject = q.get('subject', 'N/A')[:14]
        topic = q.get('topic', 'N/A')[:28]
        print(f"{ts:<20} {subject:<15} {topic:<30}")
