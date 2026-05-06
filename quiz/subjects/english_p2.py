#!/usr/bin/env python3
"""
English Paper 2 - Literature
40% Poems, 40% Tsotsi, 20% Macbeth
"""

import random
import json
import re
import fitz
from pathlib import Path
import ollama

SUBJECT = "English Paper 2"
MODEL = "mistral"

PDF_DIR = Path.home() / "studies/english"
MACBETH_PDF = PDF_DIR / "Macbeth (William Shakespeare etc.) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
TSOTSI_PDF = PDF_DIR / "isbn_2900802142688 (Unknown) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
POEMS_PDF = PDF_DIR / "0e377eec-ff5c-4980-b4bd-d08c7173b061.pdf"

def extract_text(pdf_path, start_page, end_page):
    if not pdf_path.exists():
        return None
    text_parts = []
    try:
        doc = fitz.open(pdf_path)
        for i in range(start_page, min(end_page, len(doc))):
            text = doc[i].get_text()
            if text.strip():
                text_parts.append(text.strip())
        doc.close()
        return ' '.join(text_parts) if text_parts else None
    except Exception as e:
        print(f"[english_p2] Error: {e}")
        return None

def get_random_passage(text, length=400):
    if not text:
        return "No passage available."
    if len(text) <= length:
        return text
    start = random.randint(0, len(text) - length)
    end = start + length
    return text[start:end]

def generate_question(title, text_type, full_text):
    passage = get_random_passage(full_text, 500)
    prompt = f"""Generate ONE literature question about {title} for Grade 11 NSC Paper 2 ({text_type}).
The question must be analytical, testing understanding of character, theme, or literary device.
Respond with ONLY JSON: {{"question": "..."}}"""
    
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 200}
        )
        raw = response["message"]["content"].strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            question = data.get("question", f"Discuss a key theme in {title}.")
            return {
                "question": question,
                "answer": "Use evidence from the passage to support your answer.",
                "difficulty": "medium",
                "topic": f"{title}",
                "section": "Literature",
                "source": "AI generated",
                "subject": SUBJECT,
                "type": "literature",
                "time_limit": 600,
                "passage": f"EXTRACT FROM {title.upper()}:\n\n{passage}"
            }
    except Exception as e:
        print(f"[english_p2] AI error: {e}")
    
    return {
        "question": f"Discuss a key theme or character in {title}.",
        "answer": "Use evidence from the passage to support your answer.",
        "difficulty": "medium",
        "topic": f"{title}",
        "section": "Literature",
        "source": "AI generated",
        "subject": SUBJECT,
        "type": "literature",
        "time_limit": 600,
        "passage": f"EXTRACT FROM {title.upper()}:\n\n{passage}"
    }

def get_question():
    # 40% Poems, 40% Tsotsi, 20% Macbeth
    r = random.random()
    
    if r < 0.4:
        # Poems
        text = extract_text(POEMS_PDF, 3, 80)
        if text:
            return generate_question("Poetry", "poem", text)
        else:
            return get_question()  # retry
    
    elif r < 0.8:
        # Tsotsi
        text = extract_text(TSOTSI_PDF, 3, 200)
        if text:
            return generate_question("Tsotsi", "novel", text)
        else:
            return get_question()  # retry
    
    else:
        # Macbeth
        text = extract_text(MACBETH_PDF, 125, 240)
        if text:
            return generate_question("Macbeth", "play", text)
        else:
            return get_question()  # retry
