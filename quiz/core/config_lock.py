import json, fcntl, time
from pathlib import Path

CONFIG_FILE = Path.home() / ".local/share/app-blocker/config.json"
LOCK_FILE = Path.home() / ".local/share/app-blocker/.config.lock"


def read_config():
    for attempt in range(10):
        try:
            lock = open(LOCK_FILE, "w")
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            try:
                data = json.loads(CONFIG_FILE.read_text())
                return data
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
                lock.close()
        except BlockingIOError:
            time.sleep(0.05)
        except Exception as e:
            print(f"[config_lock] read error: {e}")
            time.sleep(0.05)
    return None


def write_config(data):
    for attempt in range(10):
        try:
            lock = open(LOCK_FILE, "w")
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                tmp = CONFIG_FILE.with_suffix(".tmp")
                tmp.write_text(json.dumps(data, indent=2))
                tmp.rename(CONFIG_FILE)
                return True
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
                lock.close()
        except BlockingIOError:
            time.sleep(0.05)
        except Exception as e:
            print(f"[config_lock] write error: {e}")
            time.sleep(0.05)
    return False
