#!/usr/bin/env python3
"""
English Module - Paper 1 & Paper 3, filter instructions only
"""

import random, requests, io, fitz, pytesseract, re
from PIL import Image, ImageEnhance, ImageFilter
from bs4 import BeautifulSoup
from pathlib import Path

SUBJECT = "English"

URLS_GR11 = ["https://stanmorephysics.com/english-grade-11/"]
URLS_GR10 = ["https://stanmorephysics.com/english-grade-10/"]

_paper_cache = {}

# ============================================
# THREE-TIER PRIORITY SYSTEM
# ============================================

def _get_priority_topic():
    """Return topic based on three-tier priority system"""
    try:
        from atp_comparator import get_all_topics_with_accuracy
        
        topics = get_all_topics_with_accuracy()
        if not topics:
            return None
        
        # Filter for English only
        subject_topics = [t for t in topics if t['subject'].lower() == 'english']
        
        if not subject_topics:
            return None
        
        # Categorize by accuracy
        lowest = []   # 0-40%
        middle = []   # 40-70%
        highest = []  # 70-100%
        
        for topic in subject_topics:
            acc = topic.get('accuracy', 100)
            if acc < 40:
                lowest.append(topic)
            elif acc < 70:
                middle.append(topic)
            else:
                highest.append(topic)
        
        # Weighted selection: 60% lowest, 30% middle, 10% highest
        r = random.random()
        if r < 0.6 and lowest:
            selected = random.choice(lowest)
            print(f"[english] PRIORITY: Lowest tier (0-40%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
        elif r < 0.9 and middle:
            selected = random.choice(middle)
            print(f"[english] PRIORITY: Middle tier (40-70%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
        elif highest:
            selected = random.choice(highest)
            print(f"[english] PRIORITY: Highest tier (70-100%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
    except Exception as e:
        print(f"[english] Priority error: {e}")
    return None

def _generate_question_for_topic(topic_name):
    """Generate a question for a specific English topic"""
    print(f"[english] Generating question for priority topic: {topic_name}")
    # Fallback to past paper
    return _get_past_paper_question()

# ============================================
# EXISTING FUNCTIONS (renamed)
# ============================================

def filter_instructions(text):
    lines = text.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        line_upper = line.upper()
        if any(keyword in line_upper for keyword in [
            'SECTION', 'INSTRUCTIONS', 'DO NOT', 'NUMBER THE ANSWERS',
            'ANSWER ALL', 'PLANNING', 'PROOFREAD', 'COPYRIGHT', 'PTO',
            'TURN OVER', 'MARKS:', 'TIME:', 'SPEND APPROXIMATELY',
            'WRITE DOWN THE NUMBER', 'BODY OF YOUR RESPONSE'
        ]):
            start_idx = i + 1
        else:
            if start_idx > 0 or i > 5:
                break
    filtered = '\n'.join(lines[start_idx:])
    return filtered[:2000]

def _is_wanted(href, text):
    if not href.endswith('.pdf'):
        return False
    return True

def _fetch_pdf_links(urls):
    seen, links = set(), []
    for url in urls:
        try:
            r = requests.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href in seen:
                    continue
                if not _is_wanted(href, ''):
                    continue
                seen.add(href)
                links.append((text or href.split('/')[-1], href))
        except Exception as e:
            print(f"[english] fetch error {url}: {e}")
    print(f"[english] found {len(links)} papers")
    return links

def _ocr_pdf_bytes(data, max_pages=20):
    chunks = []
    try:
        doc = fitz.open(stream=data, filetype='pdf')
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            text = page.get_text().strip()
            if len(text) < 100:
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes('png'))).convert('L')
                img = ImageEnhance.Contrast(img).enhance(2.0)
                img = img.filter(ImageFilter.SHARPEN)
                text = pytesseract.image_to_string(img, config='--psm 6')
            filtered = filter_instructions(text)
            if len(filtered) > 200:
                words = filtered.split()
                for j in range(0, len(words), 150):
                    chunk = " ".join(words[j:j+150])
                    if len(chunk) > 100:
                        chunks.append(chunk)
    except Exception as e:
        print(f"[english] OCR error: {e}")
    return chunks

def _get_paper_chunks(url):
    if url in _paper_cache:
        return _paper_cache[url]
    try:
        r = requests.get(url, timeout=20)
        chunks = _ocr_pdf_bytes(r.content)
        _paper_cache[url] = chunks
        print(f"[english] {len(chunks)} chunks from {url.split('/')[-1]}")
    except Exception as e:
        print(f"[english] paper fetch error: {e}")
        _paper_cache[url] = []
    return _paper_cache[url]

def _get_past_paper_question():
    links = _fetch_pdf_links(URLS_GR11)
    if not links:
        links = _fetch_pdf_links(URLS_GR10)
    if not links:
        print("[english] no papers found")
        return None

    label, url = random.choice(links)
    print(f"[english] using: {label}")

    chunks = _get_paper_chunks(url)
    if not chunks:
        print("[english] no chunks")
        return None

    anchor = random.choice(chunks)
    anchor = anchor[:2000]

    return {
        "question": anchor,
        "answer": "Answer based on the text above",
        "difficulty": "medium",
        "topic": "English",
        "section": "Paper 1/3",
        "source": "STANMORE past paper",
        "subject": SUBJECT,
        "type": "general",
        "time_limit": 900
    }

# ============================================
# MAIN GET_QUESTION
# ============================================

def get_question():
    """Three-tier priority: weakest topics first, then past papers"""
    
    # Try priority system first
    priority_topic = _get_priority_topic()
    if priority_topic:
        return _generate_question_for_topic(priority_topic['topic'])
    
    # Fallback to past papers
    print("[english] No priority topics found, using past paper")
    return _get_past_paper_question()
