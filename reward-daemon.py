#!/usr/bin/env python3
"""
Reward Daemon - Calculates study time, distributes per-app quotas, handles daily reset
"""

import os
import time
import json
import sqlite3
import fcntl
import signal
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_FILE = Path.home() / ".local/share/app-blocker/config.json"
DAILY_CAP_FILE = Path.home() / ".local/share/app-blocker/daily_cap.json"
LOCK_FILE = Path.home() / ".local/share/reward-system/.reward.lock"
DB_PATH = Path.home() / ".local/share/time-monitor/process_times.db"

INTERVAL = 30
running = True

# Study apps and conversion ratios (seconds of study = 1 second of gaming)
STUDY_APPS = {
    "waterfox": 6.0,
    "firefox": 6.0,
    "chromium": 6.0,
    "chrome": 6.0,
    "vlc": 16.0,
    "okular": 16.0,
    "gnome-boxes": 6.0,
    "khan-academy": 6.0,
    "wolframalpha": 6.0,
    "evince": 16.0,
    "xreader": 16.0,
    "zathura": 16.0,
    "Stanmore": 6.0,
    "Webapp": 6.0,
    "soffice.bin": 16.0,
    "soffice": 16.0,
    "libreoffice": 16.0,
}

def signal_handler(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def acquire_lock():
    try:
        if LOCK_FILE.exists():
            try:
                with open(LOCK_FILE, 'r') as f:
                    old_pid = f.read().strip()
                if old_pid:
                    try:
                        with open(f"/proc/{int(old_pid)}/cmdline", 'r') as f:
                            cmdline = f.read()
                        if 'reward-daemon' not in cmdline:
                            LOCK_FILE.unlink(missing_ok=True)
                    except (OSError, ValueError, FileNotFoundError):
                        LOCK_FILE.unlink(missing_ok=True)
            except:
                try:
                    LOCK_FILE.unlink(missing_ok=True)
                except:
                    pass
        
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except (BlockingIOError, OSError):
        return None

def release_lock(lock_fd):
    try:
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            LOCK_FILE.unlink(missing_ok=True)
    except:
        pass

def get_study_seconds(today):
    if not DB_PATH.exists():
        return 0
    total = 0
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        for app, ratio in STUDY_APPS.items():
            row = conn.execute(
                "SELECT SUM(duration) FROM process_times WHERE date=? AND process=?",
                (today, app)
            ).fetchone()
            raw = row[0] if row and row[0] else 0
            total += int(raw / ratio)
        conn.close()
    except Exception as e:
        print(f"[reward] DB error: {e}")
    return total

def read_daily_cap():
    if not DAILY_CAP_FILE.exists():
        return None
    try:
        with open(DAILY_CAP_FILE, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
            return data
    except Exception as e:
        print(f"[reward] Read error: {e}")
        return None

def write_daily_cap(data):
    try:
        with open(DAILY_CAP_FILE, 'w') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"[reward] Write error: {e}")

def get_next_reset_time():
    now = datetime.now()
    reset = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if now >= reset:
        reset += timedelta(days=1)
    return reset

def check_reset():
    data = read_daily_cap()
    if not data:
        now = datetime.now()
        write_daily_cap({
            "earned_today": 0,
            "max_cap": 7200,
            "reset_time": get_next_reset_time().isoformat(),
            "gaming_used": 0,
            "last_reset_date": "2000-01-01"
        })
        return True

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    last_reset = data.get("last_reset_date", "2000-01-01")
    reset_time_str = data.get("reset_time", "2000-01-01T00:00:00")
    
    try:
        reset_time = datetime.fromisoformat(reset_time_str)
    except:
        reset_time = datetime(2000, 1, 1)

    needs_reset = (last_reset != today_str) or (now >= reset_time and last_reset != today_str)

    if needs_reset:
        zero_quotas()
        write_daily_cap({
            "earned_today": 0,
            "max_cap": 7200,
            "reset_time": get_next_reset_time().isoformat(),
            "gaming_used": 0,
            "last_reset_date": today_str
        })
        print(f"[reward] Daily reset: {today_str}")
        return True

    return False

def zero_quotas():
    try:
        with open(CONFIG_FILE, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            cfg = json.load(f)
            for section in ["blacklist", "windows_games", "steam_games"]:
                for app in cfg.get(section, {}):
                    cfg[section][app] = 0
            f.seek(0)
            f.truncate()
            json.dump(cfg, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
            print("[reward] Zeroed quotas")
    except Exception as e:
        print(f"[reward] Zero error: {e}")

def update_earned():
    today = datetime.now().strftime("%Y-%m-%d")
    study_seconds = get_study_seconds(today)

    data = read_daily_cap() or {}
    data["earned_today"] = study_seconds
    data["max_cap"] = max(data.get("max_cap", 7200), study_seconds)
    write_daily_cap(data)

def distribute():
    data = read_daily_cap()
    if not data:
        return

    remaining = max(0, data.get("earned_today", 0) - data.get("gaming_used", 0))
    if remaining <= 0:
        return

    try:
        with open(CONFIG_FILE, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            cfg = json.load(f)

            total_apps = 0
            for section in ["blacklist", "windows_games", "steam_games"]:
                total_apps += len(cfg.get(section, {}))

            if total_apps == 0:
                fcntl.flock(f, fcntl.LOCK_UN)
                return

            per_app = remaining // total_apps
            remainder = remaining % total_apps

            for section in ["blacklist", "windows_games", "steam_games"]:
                for app in cfg.get(section, {}):
                    cfg[section][app] = per_app

            i = 0
            for section in ["blacklist", "windows_games", "steam_games"]:
                for app in cfg.get(section, {}):
                    if i < remainder:
                        cfg[section][app] += 1
                        i += 1
                    else:
                        break
                if i >= remainder:
                    break

            f.seek(0)
            f.truncate()
            json.dump(cfg, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)

            print(f"[reward] Distributed {remaining}s across {total_apps} apps (~{per_app}s each)")
    except Exception as e:
        print(f"[reward] Distribution error: {e}")

def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[reward] Already running")
        return

    print("Reward Daemon started")

    try:
        while running:
            check_reset()
            update_earned()
            distribute()

            data = read_daily_cap() or {}
            earned = data.get("earned_today", 0)
            used = data.get("gaming_used", 0)
            remaining = max(0, earned - used)

            print(f"[reward] {datetime.now().strftime('%H:%M:%S')} | Earned: {earned//60}m | Used: {used//60}m | Left: {remaining//60}m")

            time.sleep(INTERVAL)
    except Exception as e:
        print(f"[reward] Fatal error: {e}")
    finally:
        release_lock(lock_fd)

if __name__ == "__main__":
    main()
