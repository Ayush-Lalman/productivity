import random, requests, io, fitz, pytesseract, re
from PIL import Image, ImageEnhance, ImageFilter
from bs4 import BeautifulSoup
from pathlib import Path

SUBJECT = "Accounting"

URLS_GR11 = ["https://stanmorephysics.com/accounting-grade-11/"]
URLS_GR10 = ["https://stanmorephysics.com/accounting-grade-10/"]

SKIP_KEYWORDS = [
    "SCOPE", "ATP", "POA", "TIMETABLE", "GUIDELINES",
    "TEACHER", "LEARNER", "SUPPORT", "JIT", "STEP-AHEAD",
    "MEMO", "SOLUTION", "AFDELING", "MINUTE", "Nommer",
    "Skryf", "Dui", "getal", "woorde", "netjies"
]

WANT_PROVINCES = ["KZN", "GP", "GAUTENG"]
WANT_PAPERS    = ["P1", "P2", "QP", "MARCH", "JUNE", "SEPT", "NOV"]

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
        
        # Filter for Accounting only
        subject_topics = [t for t in topics if t['subject'].lower() == 'accounting']
        
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
            print(f"[accounting] PRIORITY: Lowest tier (0-40%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
        elif r < 0.9 and middle:
            selected = random.choice(middle)
            print(f"[accounting] PRIORITY: Middle tier (40-70%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
        elif highest:
            selected = random.choice(highest)
            print(f"[accounting] PRIORITY: Highest tier (70-100%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
    except Exception as e:
        print(f"[accounting] Priority error: {e}")
    return None

def _generate_question_for_topic(topic_name):
    """Generate a question for a specific accounting topic"""
    print(f"[accounting] Generating question for priority topic: {topic_name}")
    # Fallback to past paper
    return _get_past_paper_question()

# ============================================
# PAST PAPER FUNCTIONS
# ============================================

def _is_wanted(href, text):
    combined = (href + " " + text).upper()
    if not href.endswith('.pdf'): return False
    if any(k in combined for k in SKIP_KEYWORDS): return False
    has_province = any(p in combined for p in WANT_PROVINCES)
    has_paper = any(p in combined for p in WANT_PAPERS)
    return has_province and has_paper

def _fetch_pdf_links(urls):
    seen, links = set(), []
    for url in urls:
        try:
            r = requests.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.text.strip()
                if href in seen: continue
                if not _is_wanted(href, text): continue
                seen.add(href)
                links.append((text or href.split('/')[-1], href))
        except Exception as e:
            print(f"[accounting] fetch error {url}: {e}")
    print(f"[accounting] found {len(links)} papers")
    return links

def _clean_text(text):
    patterns = [
        r'AFDELING [A-C]:\s*\d+\s*MINUTE',
        r'Nommer\s*elke\s*teks',
        r'Skryf\s*die\s*titel',
        r'Dui\s*die\s*getal\s*woorde',
        r'Skryf\s*netjies\s*en\s*leesbaar',
        r'BL\.\s*\d+',
        r'[A-Z\s]+INST\S*',
        r'Copyright reserved',
        r'Please turn over',
        r'PTO',
        r'\d+\s*MINUTE\s*',
        r'VEVCCEEF.*',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _is_meaningful_content(text):
    if len(text) < 50:
        return False
    instruction_keywords = ['AFDELING', 'MINUTE', 'Nommer', 'Skryf', 'Dui', 'getal']
    instruction_count = sum(1 for kw in instruction_keywords if kw in text)
    if instruction_count > 2:
        return False
    return True

def _extract_questions_from_chunk(chunk):
    lines = chunk.split('\n')
    questions = []
    current_q = []
    for line in lines:
        line = line.strip()
        if not line:
            if current_q:
                q_text = ' '.join(current_q)
                if _is_meaningful_content(q_text):
                    questions.append(q_text)
                current_q = []
            continue
        if re.match(r'^\d+\.?\s', line) or re.match(r'^\(?\d+\)?\s', line):
            if current_q:
                q_text = ' '.join(current_q)
                if _is_meaningful_content(q_text):
                    questions.append(q_text)
                current_q = []
        current_q.append(line)
    if current_q:
        q_text = ' '.join(current_q)
        if _is_meaningful_content(q_text):
            questions.append(q_text)
    return questions

def _ocr_pdf_bytes(data, max_pages=20):
    chunks = []
    try:
        doc = fitz.open(stream=data, filetype='pdf')
        for i, page in enumerate(doc):
            if i >= max_pages: break
            text = page.get_text().strip()
            if len(text) < 100:
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes('png'))).convert('L')
                img = ImageEnhance.Contrast(img).enhance(2.0)
                img = img.filter(ImageFilter.SHARPEN)
                text = pytesseract.image_to_string(img, config='--psm 6')
            cleaned = _clean_text(text)
            if _is_meaningful_content(cleaned):
                words = cleaned.split()
                for j in range(0, len(words), 100):
                    chunk = " ".join(words[j:j+100])
                    if len(chunk) > 100:
                        chunks.append(chunk)
    except Exception as e:
        print(f"[accounting] OCR error: {e}")
    return chunks

def _get_paper_chunks(url):
    if url in _paper_cache: return _paper_cache[url]
    try:
        r = requests.get(url, timeout=20)
        chunks = _ocr_pdf_bytes(r.content)
        _paper_cache[url] = chunks
        print(f"[accounting] {len(chunks)} content chunks from {url.split('/')[-1]}")
    except Exception as e:
        print(f"[accounting] paper fetch error: {e}")
        _paper_cache[url] = []
    return _paper_cache[url]

def _get_past_paper_question():
    links = _fetch_pdf_links(URLS_GR11)
    if not links:
        links = _fetch_pdf_links(URLS_GR10)
    if not links:
        print("[accounting] no papers found")
        return None

    label, url = random.choice(links)
    print(f"[accounting] using past paper: {label}")

    chunks = _get_paper_chunks(url)
    if not chunks:
        print("[accounting] no content chunks")
        return None

    for _ in range(10):
        anchor = random.choice(chunks)
        if _is_meaningful_content(anchor) and len(anchor) > 100:
            break
    
    questions = _extract_questions_from_chunk(anchor)
    if questions:
        question_text = random.choice(questions)
    else:
        question_text = anchor
    
    return {
        "question": question_text[:2000],
        "answer": "Provide your answer in Accounting",
        "difficulty": "medium",
        "topic": "Accounting Comprehension",
        "section": "Past Paper",
        "source": "STANMORE past paper",
        "subject": SUBJECT,
        "paper": label,
        "type": "past_paper",
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
    print("[accounting] No priority topics found, using past paper")
    return _get_past_paper_question()
