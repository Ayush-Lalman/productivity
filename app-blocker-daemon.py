#!/usr/bin/env python3
"""
App Blocker Daemon - Tracks game usage, kills when quota expires
Matches exact process names + substring matching for games
"""

import os
import time
import subprocess
import json
import fcntl
import signal
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / ".local/share/app-blocker"
CONFIG_FILE = CONFIG_DIR / "config.json"
DAILY_CAP_FILE = CONFIG_DIR / "daily_cap.json"
LOCK = CONFIG_DIR / ".blocker.lock"

INTERVAL = 5
running = True

# Known process name mappings (config name -> possible ps names or substrings)
PROCESS_ALIASES = {
    "java": ["java", "javaw"],
    "pcsx2-qt": ["pcsx2-qt", "pcsx2"],
    "sober": ["sober"],
    "firefox": ["firefox"],
    "Stardew Valley": ["Stardew", "StardewValley", "Stardew.bin"],
    "terraria": ["Terraria", "Terraria.bin.x8", "Terraria.bin.x86_64"],
    "Asphalt9": ["Asphalt9", "Asphalt9_Steam"],
    "TS4": ["TS4", "TS4_x64", "TS4_x64.exe"],
    "minecraft": ["java", "minecraft-launcher"],
    "steam": ["steam"],
}

def signal_handler(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def acquire_lock():
    try:
        lock_fd = open(LOCK, 'w')
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
            LOCK.unlink(missing_ok=True)
    except:
        pass

def read_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
            return data
    except:
        return {"blacklist": {}, "windows_games": {}, "steam_games": {}}

def read_daily_cap():
    try:
        with open(DAILY_CAP_FILE, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
            return data
    except:
        return {"earned_today": 0, "gaming_used": 0, "max_cap": 7200}

def write_daily_cap(data):
    try:
        with open(DAILY_CAP_FILE, 'w') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"[blocker] Write error: {e}")

def write_config(data):
    try:
        with open(CONFIG_FILE, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"[blocker] Config write error: {e}")

def get_running_processes():
    try:
        result = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, timeout=5)
        return set(line.strip() for line in result.stdout.splitlines() if line.strip())
    except:
        return set()

def find_running_games(ps_procs, config):
    """Find running games with their config keys and actual process names"""
    running = []
    
    for section in ["blacklist", "windows_games", "steam_games"]:
        for config_key in config.get(section, {}):
            aliases = PROCESS_ALIASES.get(config_key, [config_key])
            
            # Check if any alias matches as substring of any process name
            for alias in aliases:
                for proc in ps_procs:
                    if alias.lower() in proc.lower():
                        running.append((config_key, proc, section))
                        break
                else:
                    continue
                break
    
    return running

def kill_game(proc_name):
    """Kill by exact process name first, then try pattern"""
    killed = False
    try:
        subprocess.run(["pkill", "-9", "-x", proc_name], timeout=3)
        killed = True
    except:
        pass
    if not killed:
        try:
            subprocess.run(["pkill", "-9", "-f", proc_name], timeout=3)
            killed = True
        except:
            pass
    return killed

def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[blocker] Already running")
        return

    print("App Blocker started")

    try:
        while running:
            ps_procs = get_running_processes()
            config = read_config()
            daily_cap = read_daily_cap()
            
            running_games = find_running_games(ps_procs, config)
            
            earned = daily_cap.get("earned_today", 0)
            used = daily_cap.get("gaming_used", 0)
            max_cap = daily_cap.get("max_cap", 7200)
            total_remaining = max(0, min(earned, max_cap) - used)

            if running_games:
                game_info = [f"{g[0]}({g[1]})" for g in running_games]
                print(f"[blocker] {datetime.now().strftime('%H:%M:%S')} | Running: {game_info} | Total: {total_remaining}s")

                if total_remaining <= 0:
                    print("[blocker] NO TIME LEFT - Killing all games")
                    for config_key, proc_name, section in running_games:
                        if kill_game(proc_name):
                            print(f"[blocker] Killed: {proc_name}")
                else:
                    for config_key, proc_name, section in running_games:
                        app_quota = config.get(section, {}).get(config_key, 0)
                        
                        if app_quota <= 0:
                            print(f"[blocker] {config_key} quota exhausted - killing")
                            if kill_game(proc_name):
                                print(f"[blocker] Killed: {proc_name}")
                        else:
                            new_quota = max(0, app_quota - INTERVAL)
                            config[section][config_key] = new_quota
                            
                            used = min(used + INTERVAL, earned)
                            daily_cap["gaming_used"] = used
                            
                            print(f"[blocker] {config_key}: {app_quota}s → {new_quota}s | Total used: {used}s")
                    
                    write_config(config)
                    write_daily_cap(daily_cap)
            else:
                print(f"[blocker] {datetime.now().strftime('%H:%M:%S')} | No games | Remaining: {total_remaining}s")

            time.sleep(INTERVAL)
    except Exception as e:
        print(f"[blocker] Fatal error: {e}")
    finally:
        release_lock(lock_fd)

if __name__ == "__main__":
    main()
