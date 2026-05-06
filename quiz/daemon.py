#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quiz Daemon - Generates questions from subjects (Sway compatible)
"""

import os
import sys
import time
import random
import json
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.home() / ".local/bin"))

from quiz.subjects import maths, physics, it, accounting, lo, english, afrikaans, english_p2
from quiz.core.question_logger import log_question

QUIZ_QUEUE = Path.home() / ".local/share/quiz-daemon/pending_question.json"
LOCK = Path.home() / ".local/share/quiz-daemon/.lock"
QUIZ_QUEUE.parent.mkdir(parents=True, exist_ok=True)

if LOCK.exists():
    try:
        os.kill(int(LOCK.read_text()), 0)
        print("Already running")
        exit(1)
    except:
        LOCK.unlink()
LOCK.write_text(str(os.getpid()))
import atexit
atexit.register(lambda: LOCK.unlink(missing_ok=True))

SUBJECT_POOL = [
    (maths,   "Maths"),
    (physics, "Physics"),
    (physics, "Chemistry"),
    (it,      "IT theory",    {"practical": False}),
    (it,      "IT practical", {"practical": True}),
    (accounting, "Accounting"),
    (lo,         "LO"),
    (english,    "English P1/P3"),
    (english_p2, "English P2"),
    (afrikaans,  "Afrikaans"),
]

DIFFICULTY_TIME = {"easy": 600, "medium": 1200, "hard": 1800}
PAPER3_TIME = 1800
ENG_P2_TIME = 3600
AFK_P2_TIME = 5400

def save_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(path)

def get_current_workspace():
    """Get current Sway workspace number"""
    try:
        result = subprocess.run(['swaymsg', '-t', 'get_workspaces'], capture_output=True, text=True)
        workspaces = json.loads(result.stdout)
        for ws in workspaces:
            if ws.get('focused'):
                return ws.get('num')
    except:
        pass
    return None

def switch_to_workspace(ws_num):
    """Switch to specified workspace in Sway"""
    if ws_num is not None:
        try:
            subprocess.run(['swaymsg', 'workspace', str(ws_num)], capture_output=True)
        except:
            pass

def launch_gui():
    """Launch quiz GUI with Sway compatibility"""
    env = {**os.environ,
           "DISPLAY": ":0",
           "WAYLAND_DISPLAY": "wayland-0",
           "QT_QPA_PLATFORM": "xcb",
           "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
    
    # Save current workspace to return later
    original_ws = get_current_workspace()
    
    # Launch GUI
    proc = subprocess.Popen(
        ["python3", str(Path.home() / ".local/bin/quiz/gui.py")],
        env=env,
        start_new_session=True
    )
    
    # Wait a moment then return to original workspace
    time.sleep(1)
    if original_ws:
        switch_to_workspace(original_ws)
    
    return proc

print("Quiz Daemon started (Sway compatible)")

while True:
    try:
        module, name, *kwargs = random.choice(SUBJECT_POOL)
        kw = kwargs[0] if kwargs else {}
        print(f"Generating {name} question...")
        q = module.get_question(**kw) if kw else module.get_question()

        if q:
            if "Vraestel 3" in q.get("paper", ""):
                q["time_limit"] = 3600
            elif "Vraestel 1" in q.get("paper", "") and q.get("high_stakes"):
                q["time_limit"] = AFK_P2_TIME
            elif "Paper 2" in q.get("paper", ""):
                q["time_limit"] = ENG_P2_TIME
            elif "Paper 3" in q.get("paper", ""):
                q["time_limit"] = PAPER3_TIME
            elif q.get("subject") in ("Physics", "Chemistry") and q.get("difficulty") == "hard":
                q["time_limit"] = 1800
            elif q.get("subject") in ("Physics", "Chemistry"):
                q["time_limit"] = DIFFICULTY_TIME.get(q.get("difficulty", "medium"), 1200)
            else:
                q["time_limit"] = DIFFICULTY_TIME.get(q.get("difficulty", "medium"), 90)
            
            q["generated_at"] = datetime.now().isoformat()
            save_json(QUIZ_QUEUE, q)
            log_question(q)
            launch_gui()
            print(f"Fired: {name} | {q.get('topic')} | {q.get('difficulty')}")
        else:
            print(f"No question generated for {name}, skipping")

        wait = random.randint(600, 1800)
        print(f"Next quiz in {wait//60}min")
        time.sleep(wait)

    except Exception as e:
        print(f"Daemon error: {e}")
        time.sleep(60)
