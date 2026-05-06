#!/usr/bin/env python3
"""
Life Orientation - AI-powered questions using Mistral
Topics: Career choices, Health, Social issues, Citizenship, Study skills
"""

import random
import json
import re
from pathlib import Path
from datetime import datetime
import ollama

SUBJECT = "LO"
MODEL = "mistral"

# LO topics with weights (40% Career, 30% Health/Social, 30% Citizenship/Study)
TOPICS = [
    ("Career choices and pathways", 0.4),
    ("Health and wellbeing", 0.15),
    ("Social and environmental issues", 0.15),
    ("Citizenship and democracy", 0.15),
    ("Study skills and time management", 0.15),
]

STATS_DB = Path.home() / ".local/share/quiz-daemon/lo_stats.json"

def load_stats():
    if STATS_DB.exists():
        try:
            with open(STATS_DB, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_stats(stats):
    STATS_DB.write_text(json.dumps(stats, indent=2))

def record_result(topic, correct):
    stats = load_stats()
    if topic not in stats:
        stats[topic] = {"correct": 0, "wrong": 0, "last_seen": None}
    if correct:
        stats[topic]["correct"] += 1
    else:
        stats[topic]["wrong"] += 1
    stats[topic]["last_seen"] = datetime.now().isoformat()
    save_stats(stats)

def get_weakest_topic():
    stats = load_stats()
    weakest = "Career choices and pathways"  # default
    lowest_acc = 1.0
    for topic, data in stats.items():
        total = data["correct"] + data["wrong"]
        acc = data["correct"] / total if total > 0 else 0.5
        if acc < lowest_acc:
            lowest_acc = acc
            weakest = topic
    return weakest, lowest_acc

def generate_question(topic):
    prompt = f"""Generate ONE Grade 11 Life Orientation exam question about: {topic}

The question must:
- Be realistic and relevant to South African learners
- Test understanding, not just recall
- Apply to real-life situations
- Be worth 2-4 marks

Respond with ONLY valid JSON:
{{"question": "Your question here", "answer": "Model answer here", "difficulty": "easy/medium/hard"}}"""

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 300}
        )
        raw = response["message"]["content"].strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return {
                "question": data.get("question", f"Discuss {topic} in relation to your own life."),
                "answer": data.get("answer", "Answer must be well-reasoned and practical."),
                "difficulty": data.get("difficulty", "medium"),
                "topic": topic,
                "section": "Life Orientation",
                "source": "AI generated (Mistral)",
                "subject": SUBJECT,
                "type": "theory",
                "time_limit": 600
            }
    except Exception as e:
        print(f"[LO] AI error: {e}")
    
    return {
        "question": f"Discuss the importance of {topic} for a Grade 11 learner.",
        "answer": "Answer must include practical examples and personal reflection.",
        "difficulty": "medium",
        "topic": topic,
        "section": "Life Orientation",
        "source": "AI generated (fallback)",
        "subject": SUBJECT,
        "type": "theory",
        "time_limit": 600
    }

def get_question():
    """Return a question based on weakest topic (70% chance) or random (30% chance)"""
    
    weakest, acc = get_weakest_topic()
    
    # 70% chance to focus on weakest topic if accuracy is low
    if acc < 0.7 and random.random() < 0.7:
        print(f"[LO] PRIORITY: {weakest} ({acc:.0%})")
        return generate_question(weakest)
    
    # Otherwise random weighted by topic weights
    topics, weights = zip(*TOPICS)
    topic = random.choices(topics, weights=weights)[0]
    print(f"[LO] Random: {topic}")
    return generate_question(topic)
