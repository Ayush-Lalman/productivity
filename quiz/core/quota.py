#!/usr/bin/env python3
"""
Quota Manager - Quiz answers affect max_cap and earned_today directly
No separate quiz_delta.json — that was the bug.
"""

import json
import time
import fcntl
from pathlib import Path
from datetime import date

CAP_FILE = Path.home() / ".local/share/app-blocker/daily_cap.json"
MAX_CAP = 7200  # 2 hours base
ABSOLUTE_MAX = 14400  # 4 hours absolute maximum

def _lock_and_update(updater):
    """Thread-safe update of daily cap"""
    for attempt in range(5):
        try:
            with open(CAP_FILE, 'r+') as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                data = json.load(f)
                today = str(date.today())
                
                # Reset if date changed
                reset_time = data.get("reset_time", "")
                if today not in reset_time:
                    data = {
                        "earned_today": 0,
                        "max_cap": MAX_CAP,
                        "reset_time": f"{today}T23:00:00",
                        "gaming_used": 0
                    }
                
                # Ensure max_cap exists
                if "max_cap" not in data:
                    data["max_cap"] = MAX_CAP
                if "earned_today" not in data:
                    data["earned_today"] = 0
                
                result = updater(data)
                
                # Apply bounds
                data["max_cap"] = max(0, min(data["max_cap"], ABSOLUTE_MAX))
                data["earned_today"] = max(0, min(data["earned_today"], data["max_cap"]))
                
                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=2)
                return result
        except Exception as e:
            print(f"[quota] Attempt {attempt+1} failed: {e}")
            time.sleep(0.2)
    return None

def correct(high_stakes=False):
    """Called when answer is correct - increases max_cap (earning potential)"""
    BONUS = 1200  # 20 minutes
    HS_BONUS = 2400  # 40 minutes
    
    q = HS_BONUS if high_stakes else BONUS
    
    def updater(data):
        old = data["max_cap"]
        data["max_cap"] = min(data["max_cap"] + q, ABSOLUTE_MAX)
        print(f"[quota] Correct! max_cap +{q//60} min ({old//60} -> {data['max_cap']//60} min)")
        return data["max_cap"]
    
    return _lock_and_update(updater)

def wrong(high_stakes=False):
    """Called when answer is wrong - decreases max_cap AND earned_today"""
    PENALTY = 600  # 10 minutes
    HS_PENALTY = 1800  # 30 minutes
    
    q = HS_PENALTY if high_stakes else PENALTY
    
    def updater(data):
        old_cap = data["max_cap"]
        old_earned = data["earned_today"]
        data["max_cap"] = max(0, data["max_cap"] - q)
        data["earned_today"] = max(0, data["earned_today"] - q)
        print(f"[quota] Wrong! max_cap -{q//60} min ({old_cap//60} -> {data['max_cap']//60} min)")
        print(f"[quota] Wrong! earned_today -{q//60} min ({old_earned//60} -> {data['earned_today']//60} min)")
        return data["max_cap"]
    
    return _lock_and_update(updater)

def blank(high_stakes=False):
    """Called when user submits nothing - big penalty to max_cap AND earned_today"""
    PENALTY = 2400  # 40 minutes
    HS_PENALTY = 3600  # 60 minutes
    
    q = HS_PENALTY if high_stakes else PENALTY
    
    def updater(data):
        old_cap = data["max_cap"]
        old_earned = data["earned_today"]
        data["max_cap"] = max(0, data["max_cap"] - q)
        data["earned_today"] = max(0, data["earned_today"] - q)
        print(f"[quota] Blank! max_cap -{q//60} min ({old_cap//60} -> {data['max_cap']//60} min)")
        print(f"[quota] Blank! earned_today -{q//60} min ({old_earned//60} -> {data['earned_today']//60} min)")
        return data["max_cap"]
    
    return _lock_and_update(updater)

def get_current_cap():
    """Get current max_cap in seconds"""
    try:
        with open(CAP_FILE, 'r') as f:
            data = json.load(f)
            return data.get("max_cap", MAX_CAP)
    except:
        return MAX_CAP

def get_earned_today():
    """Get earned gaming time (from study)"""
    try:
        with open(CAP_FILE, 'r') as f:
            data = json.load(f)
            return data.get("earned_today", 0)
    except:
        return 0

def get_remaining():
    """Get remaining gaming time today"""
    earned = get_earned_today()
    try:
        with open(CAP_FILE, 'r') as f:
            data = json.load(f)
            used = data.get("gaming_used", 0)
            return max(0, earned - used)
    except:
        return max(0, earned)
