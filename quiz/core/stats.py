import json
from pathlib import Path
from datetime import datetime

QUIZ_STATS = Path.home() / ".local/share/quiz-daemon/quiz_stats.json"
SIYAVULA_STATS = Path.home() / ".local/share/quiz-daemon/siyavula_stats.json"
QUIZ_STATS.parent.mkdir(parents=True, exist_ok=True)


def _load(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except:
        pass
    return default


def _save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(path)


def get_siyavula_stats():
    return _load(SIYAVULA_STATS, {})


def get_quiz_stats():
    return _load(QUIZ_STATS, {})


def record_result(subject, topic, section, correct, blank):
    stats = get_quiz_stats()
    key = f"{subject}||{topic}||{section}"
    if key not in stats:
        stats[key] = {
            "subject": subject,
            "topic": topic,
            "section": section,
            "correct": 0,
            "wrong": 0,
            "blank": 0,
        }
    if blank:
        stats[key]["blank"] += 1
    elif correct:
        stats[key]["correct"] += 1
    else:
        stats[key]["wrong"] += 1
    stats[key]["last_seen"] = datetime.now().isoformat()
    _save(QUIZ_STATS, stats)


def get_weak_sections(stats, n=5):
    scored = []
    for key, v in stats.items():
        total = v["correct"] + v["wrong"]
        if total == 0:
            continue
        acc = v["correct"] / total
        scored.append((acc, key, v))
    scored.sort(key=lambda x: x[0])
    return scored[:n]
