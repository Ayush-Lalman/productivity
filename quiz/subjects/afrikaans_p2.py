#!/usr/bin/env python3
"""
Afrikaans Paper 2 - Literature (AI-powered)
"""

import random
import json
import re
from pathlib import Path
from datetime import datetime
import ollama

SUBJECT = "Afrikaans Paper 2"

BASE_DIR = Path.home() / "studies/afrikaans/papier 2"
DRAMA_FILE = BASE_DIR / "drama/die laaste karretjiegraf.txt"
POEMS_DIR = BASE_DIR / "poems"
SHORT_STORIES_DIR = BASE_DIR / "short_stories"

STATS_DB = Path.home() / ".local/share/quiz-daemon/afrikaans_p2_stats.json"

MODEL = "mistral"
MIN_PASSAGE_LEN = 200
MAX_PASSAGE_LEN = 500

def load_stats():
    if STATS_DB.exists():
        try:
            with open(STATS_DB, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"drama": {}, "poems": {}, "short_stories": {}}

def save_stats(stats):
    STATS_DB.write_text(json.dumps(stats, indent=2))

def record_result(category, title, correct):
    stats = load_stats()
    if category not in stats:
        stats[category] = {}
    if title not in stats[category]:
        stats[category][title] = {"correct": 0, "wrong": 0, "last_seen": None}
    if correct:
        stats[category][title]["correct"] += 1
    else:
        stats[category][title]["wrong"] += 1
    stats[category][title]["last_seen"] = datetime.now().isoformat()
    save_stats(stats)

def get_accuracy(category, title):
    stats = load_stats()
    if category in stats and title in stats[category]:
        data = stats[category][title]
        total = data["correct"] + data["wrong"]
        if total > 0:
            return data["correct"] / total
    return 0.5

def get_weakest_item():
    stats = load_stats()
    lowest_acc = 1.0
    weakest_category = None
    weakest_title = None
    for category, items in stats.items():
        for title, data in items.items():
            total = data["correct"] + data["wrong"]
            acc = data["correct"] / total if total > 0 else 0.5
            if acc < lowest_acc:
                lowest_acc = acc
                weakest_category = category
                weakest_title = title
    return weakest_category, weakest_title, lowest_acc

def read_drama():
    try:
        with open(DRAMA_FILE, 'r', encoding='utf-8') as f:
            text = f.read()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        print(f"[afrikaans_p2] Error reading drama: {e}")
        return None

def get_drama_title():
    return "Die Laaste Karretjiegraf"

def get_random_passage(text):
    if not text:
        return None
    text_len = len(text)
    if text_len <= MIN_PASSAGE_LEN:
        return text
    
    start = random.randint(0, max(0, text_len - MAX_PASSAGE_LEN))
    end = start + random.randint(MIN_PASSAGE_LEN, min(MAX_PASSAGE_LEN, text_len - start))
    end = min(end, text_len)
    
    for i in range(min(end, text_len - 1), max(start, end - 50), -1):
        if text[i] in ' .!?;:':
            end = i + 1
            break
    
    passage = text[start:end].strip()
    if len(passage) < MIN_PASSAGE_LEN and text_len > MIN_PASSAGE_LEN:
        passage = text[:MIN_PASSAGE_LEN]
    return passage

def get_poem_files():
    if not POEMS_DIR.exists():
        return []
    return list(POEMS_DIR.glob("*.txt"))

def read_poem(poem_file):
    try:
        with open(poem_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[afrikaans_p2] Error reading poem: {e}")
        return None

def get_poem_title(filepath):
    name = filepath.stem.replace('_', ' ').replace('-', ' ')
    name = name.replace('.txt', '').strip()
    return name

def generate_question_with_ai(passage, title, category):
    prompt = f"""Jy is 'n Afrikaans Huistaal Graad 11 eksaminator.

BELANGRIK: Die vraag MOET in Afrikaans wees. Gebruik GEEN Engels nie. Die antwoord moet ook in Afrikaans wees.

Die volgende is 'n uittreksel uit die {category} '{title}':
\"\"\"
{passage[:400]}
\"\"\"

Genereer EEN vraag gebaseer op hierdie uittreksel. Die vraag moet:
- Pas by NSC Vraestel 2 styl (literatuur)
- Toets begrip, analise, of interpretasie
- Tussen 2 en 4 punte werd wees
- 'n Antwoord hê wat direk uit die teks bewys kan word

Respond met SLEGS JSON, geen verduideliking nie:
{{"question": "...", "marks": 2, "expected_keywords": ["woord1", "woord2"], "answer": "..."}}"""

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 500}
        )
        raw = response["message"]["content"].strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return {
                "question": data.get("question", f"Wat gebeur in hierdie uittreksel uit {title}?"),
                "answer": data.get("answer", "Antwoord gebaseer op die teks."),
                "difficulty": "medium",
                "topic": f"{category.capitalize()} - {title}",
                "section": "Uittreksel analise",
                "source": "AI gegenereer",
                "subject": SUBJECT,
                "type": "literature",
                "time_limit": 600,
                "expected_keywords": data.get("expected_keywords", [])
            }
    except Exception as e:
        print(f"[afrikaans_p2] AI error: {e}")
    
    return {
        "question": f"Bespreek die betekenis van die volgende uittreksel uit {title}.",
        "answer": "Antwoord moet bewys uit die teks gebruik.",
        "difficulty": "medium",
        "topic": f"{category.capitalize()} - {title}",
        "section": "Uittreksel analise",
        "source": "AI gegenereer (fallback)",
        "subject": SUBJECT,
        "type": "literature",
        "time_limit": 600
    }

def generate_drama_question():
    text = read_drama()
    if not text:
        return None
    passage = get_random_passage(text)
    title = get_drama_title()
    q = generate_question_with_ai(passage, title, "drama")
    q["passage"] = passage
    q["question"] = f"{q['question']}\n\n🔍 Die uittreksel verskyn in 'n pop-up venster."
    return q

def generate_poem_question(poem_file=None):
    if not poem_file:
        poems = get_poem_files()
        if not poems:
            return None
        poem_file = random.choice(poems)
    text = read_poem(poem_file)
    if not text:
        return None
    passage = get_random_passage(text)
    title = get_poem_title(poem_file)
    q = generate_question_with_ai(passage, title, "gedig")
    q["passage"] = passage
    q["question"] = f"{q['question']}\n\n🔍 Die uittreksel verskyn in 'n pop-up venster."
    return q

def get_question():
    weakest_cat, weakest_title, acc = get_weakest_item()
    if weakest_cat and weakest_title and acc < 0.7:
        print(f"[afrikaans_p2] PRIORITY: {weakest_cat} '{weakest_title}' ({acc:.0%})")
        if weakest_cat == "drama":
            return generate_drama_question()
        elif weakest_cat == "poems":
            for poem_file in get_poem_files():
                if weakest_title.lower() in get_poem_title(poem_file).lower():
                    return generate_poem_question(poem_file)
            return generate_poem_question()
    
    print("[afrikaans_p2] No weak items, selecting randomly")
    categories = []
    weights = []
    if read_drama():
        categories.append("drama")
        weights.append(0.5)
    if get_poem_files():
        categories.append("poems")
        weights.append(0.5)
    if not categories:
        return None
    category = random.choices(categories, weights=weights)[0]
    if category == "drama":
        return generate_drama_question()
    return generate_poem_question()
