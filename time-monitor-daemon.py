#!/usr/bin/env python3
"""
Time Monitor Daemon - Tracks productive study apps
Supports Sway (via swaymsg) and KDE (via qdbus/kwin)
"""

import os
import time
import json
import sqlite3
import subprocess
import fcntl
import signal
import glob
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".local/share/time-monitor/process_times.db"
LOCK_FILE = Path.home() / ".local/share/time-monitor/.time-monitor.lock"
INTERVAL = 30

# Productive study apps - EXACT process names from 'ps -eo comm='
PRODUCTIVE_APPS = {
    "waterfox", "firefox", "chromium", "chrome",
    "vlc", "gnome-boxes", "khan-academy", "wolframalpha",
    "evince", "xreader", "zathura", "Stanmore", "Webapp",
    "soffice.bin", "soffice", "libreoffice",
}

# Study workspaces (1-5). If empty set {}, ALL workspaces count as study.
STUDY_WORKSPACES = {1, 2, 3, 4, 5}

# If True, track apps even when workspace detection fails (safer fallback)
TRACK_ON_UNKNOWN_WORKSPACE = True

running = True

def signal_handler(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def acquire_lock():
    """Robust lock with stale PID detection"""
    try:
        if LOCK_FILE.exists():
            try:
                with open(LOCK_FILE, 'r') as f:
                    old_pid = f.read().strip()
                if old_pid:
                    try:
                        with open(f"/proc/{int(old_pid)}/cmdline", 'r') as f:
                            cmdline = f.read()
                        if 'time-monitor' not in cmdline:
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

def get_sway_socket():
    """Find Sway IPC socket"""
    sock = os.environ.get("SWAYSOCK")
    if sock and os.path.exists(sock):
        return sock
    uid = os.getuid()
    matches = glob.glob(f"/run/user/{uid}/sway-ipc.{uid}.*.sock")
    if matches:
        return matches[0]
    return None

def get_current_workspace():
    """
    Detect current workspace for Sway or KDE.
    Returns workspace number, or 0 if unknown.
    """
    # Try Sway first
    sock = get_sway_socket()
    if sock:
        env = os.environ.copy()
        env["SWAYSOCK"] = sock
        try:
            result = subprocess.run(
                ["swaymsg", "-t", "get_workspaces"],
                capture_output=True, text=True, timeout=5, env=env
            )
            if result.returncode == 0:
                workspaces = json.loads(result.stdout)
                for ws in workspaces:
                    if ws.get("focused"):
                        return ws.get("num", 0)
        except Exception as e:
            print(f"[time-monitor] Sway error: {e}")
    
    # Try KDE/KWin
    if os.environ.get("KDE_SESSION_VERSION") or os.environ.get("XDG_CURRENT_DESKTOP") == "KDE":
        try:
            result = subprocess.run(
                ["qdbus", "org.kde.KWin", "/KWin", "currentDesktop"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                ws = int(result.stdout.strip())
                return ws
        except Exception as e:
            print(f"[time-monitor] KDE error: {e}")
    
    # Try xprop for generic X11/Wayland hints
    try:
        result = subprocess.run(
            ["xprop", "-root", "_NET_CURRENT_DESKTOP"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and "_NET_CURRENT_DESKTOP" in result.stdout:
            parts = result.stdout.split("=")
            if len(parts) > 1:
                return int(parts[1].strip()) + 1
    except:
        pass
    
    return 0

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS process_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                process TEXT NOT NULL,
                duration INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date_process ON process_times(date, process)")

def get_running_processes():
    try:
        result = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, timeout=5)
        return set(line.strip() for line in result.stdout.splitlines() if line.strip())
    except Exception as e:
        print(f"[time-monitor] ps error: {e}")
        return set()

def detect_active_apps(running_procs):
    active = []
    for app in PRODUCTIVE_APPS:
        if app in running_procs:
            active.append(app)
    return active

def record_usage(active_apps):
    if not active_apps:
        return
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            for app in active_apps:
                conn.execute(
                    "INSERT INTO process_times (timestamp, date, process, duration) VALUES (?, ?, ?, ?)",
                    (timestamp, date_str, app, INTERVAL)
                )
        print(f"[time-monitor] {datetime.now().strftime('%H:%M:%S')} | Tracked: {', '.join(active_apps)}")
    except Exception as e:
        print(f"[time-monitor] DB error: {e}")

def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[time-monitor] Already running (or failed to acquire lock)")
        return
    
    init_db()
    sock = get_sway_socket()
    kde = os.environ.get("KDE_SESSION_VERSION") or os.environ.get("XDG_CURRENT_DESKTOP") == "KDE"
    print(f"[time-monitor] Started - Sway socket: {sock}, KDE: {kde}")
    print(f"[time-monitor] Tracking: {', '.join(PRODUCTIVE_APPS)}")
    print(f"[time-monitor] Study workspaces: {STUDY_WORKSPACES or 'ALL'}")

    try:
        while running:
            current_ws = get_current_workspace()
            running_procs = get_running_processes()
            active = detect_active_apps(running_procs)
            
            is_study_ws = current_ws in STUDY_WORKSPACES if STUDY_WORKSPACES else True
            track_anyway = TRACK_ON_UNKNOWN_WORKSPACE and current_ws == 0
            
            if active and (is_study_ws or track_anyway):
                record_usage(active)
            elif active:
                print(f"[time-monitor] {datetime.now().strftime('%H:%M:%S')} | WS {current_ws} | Skipped (not study)")
            else:
                print(f"[time-monitor] {datetime.now().strftime('%H:%M:%S')} | No study apps | WS {current_ws}")
            
            time.sleep(INTERVAL)
    except Exception as e:
        print(f"[time-monitor] Fatal error: {e}")
    finally:
        release_lock(lock_fd)

if __name__ == "__main__":
    main()
