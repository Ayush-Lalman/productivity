import random, requests, io, fitz, pytesseract, re, json
from PIL import Image, ImageEnhance, ImageFilter
from bs4 import BeautifulSoup
from pathlib import Path

SUBJECT = "Maths"

URLS_GR11 = ["https://stanmorephysics.com/mathematics-grade-11/"]
URLS_GR10 = ["https://stanmorephysics.com/mathematics-grade-10/"]

SKIP_KEYWORDS = [
    "SCOPE", "ATP", "POA", "TIMETABLE", "GUIDELINES",
    "TEACHER", "LEARNER", "SUPPORT", "JIT", "STEP-AHEAD",
    "MEMO", "SOLUTION", "INSTRUCTIONS", "QUESTION",
    "MARKS", "MINUTES", "SECTION", "ANSWER", "Copyright"
]

WANT_PROVINCES = ["KZN", "GP", "GAUTENG"]
WANT_PAPERS    = ["P1", "P2", "QP", "MARCH", "JUNE", "SEPT", "NOV"]

_paper_cache = {}

# ============================================
# THREE-TIER PRIORITY SYSTEM
# ============================================

def _get_priority_topic():
    """Return topic based on three-tier priority system (lowest accuracy = highest priority)"""
    try:
        from atp_comparator import get_all_topics_with_accuracy
        
        topics = get_all_topics_with_accuracy()
        if not topics:
            return None
        
        # Filter for Maths only (Paper 1, Grade 11 for equations)
        maths_topics = [t for t in topics if t['subject'].lower() == 'maths']
        
        if not maths_topics:
            return None
        
        # Categorize by accuracy
        lowest = []   # 0-40%
        middle = []   # 40-70%
        highest = []  # 70-100%
        
        for topic in maths_topics:
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
            print(f"[maths] PRIORITY: Lowest tier (0-40%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
        elif r < 0.9 and middle:
            selected = random.choice(middle)
            print(f"[maths] PRIORITY: Middle tier (40-70%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
        elif highest:
            selected = random.choice(highest)
            print(f"[maths] PRIORITY: Highest tier (70-100%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
    except Exception as e:
        print(f"[maths] Priority error: {e}")
    return None

def _generate_question_for_topic(topic_name):
    """Generate a question for a specific topic"""
    topic_lower = topic_name.lower()
    
    # Equations and inequalities questions
    if "equation" in topic_lower or "inequality" in topic_lower:
        questions = [
            {
                "question": "Solve for x: 2x + 5 = 13",
                "answer": "x = 4",
                "difficulty": "easy"
            },
            {
                "question": "Solve the quadratic equation: x² - 5x + 6 = 0",
                "answer": "x = 2 or x = 3",
                "difficulty": "medium"
            },
            {
                "question": "Solve the inequality: 3x - 7 > 2x + 5",
                "answer": "x > 12",
                "difficulty": "medium"
            },
            {
                "question": "Solve by completing the square: x² + 6x - 7 = 0",
                "answer": "x = -3 ± 4, so x = 1 or x = -7",
                "difficulty": "hard"
            }
        ]
        q = random.choice(questions)
        return {
            "question": q["question"],
            "answer": q["answer"],
            "difficulty": q["difficulty"],
            "topic": "Equations and inequalities",
            "section": "Equations and inequalities",
            "source": "ATP Priority Target",
            "subject": SUBJECT,
            "type": "priority_target",
            "time_limit": {"easy": 600, "medium": 900, "hard": 1200}[q["difficulty"]]
        }
    
    # Fallback to past paper
    return _get_past_paper_question()

# ============================================
# PAST PAPER FUNCTIONS
# ============================================

def _clean_text(text):
    patterns = [
        r'INSTRUCTIONS\s+AND\s+INFORMATION.*?(?=\d+\s*\.|\Z)',
        r'Read the following instructions carefully.*?(?=\d+\s*\.|\Z)',
        r'This question paper consists of.*?(?=\d+\s*\.|\Z)',
        r'Copyright reserved', r'Please turn over', r'PTO',
        r'MARKS:\s*\d+', r'TIME:\s*\d+\s*minutes', r'SECTION [A-C]:\s*\d+\s*MARKS',
        r'Answer ALL the questions', r'Number the answers correctly',
        r'Leave ONE line between two subquestions', r'You may use a non-programmable calculator',
        r'Show ALL calculations', r'Round off to TWO decimal places',
        r'\d+\s*[Mm][Aa][Rr][Kk][Ss]', r'\(?\d+\s*[Mm][Ii][Nn][Uu][Tt][Ee][Ss]?\)?',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _is_actual_question(text):
    if len(text) < 30:
        return False
    instruction_keywords = ['INSTRUCTIONS', 'MARKS', 'MINUTES', 'SECTION', 'Copyright', 'PTO']
    instruction_count = sum(1 for kw in instruction_keywords if kw in text.upper())
    if instruction_count > 2:
        return False
    question_indicators = [
        r'^\d+\.?\s', r'Calculate', r'Determine', r'Explain', r'What is',
        r'Define', r'State', r'Prove', r'Show that', r'Find', r'Compute',
        r'Solve', r'Simplify', r'Factorise', r'Expand'
    ]
    for indicator in question_indicators:
        if re.search(indicator, text, re.IGNORECASE):
            return True
    return False

def _extract_questions_from_chunk(chunk):
    lines = chunk.split('\n')
    questions = []
    current_q = []
    for line in lines:
        line = line.strip()
        if not line:
            if current_q:
                q_text = ' '.join(current_q)
                if _is_actual_question(q_text):
                    questions.append(q_text)
                current_q = []
            continue
        if re.match(r'^\d+\.?\d*\.?\s', line) or re.match(r'^\(\d+\)\s', line):
            if current_q:
                q_text = ' '.join(current_q)
                if _is_actual_question(q_text):
                    questions.append(q_text)
                current_q = []
        current_q.append(line)
    if current_q:
        q_text = ' '.join(current_q)
        if _is_actual_question(q_text):
            questions.append(q_text)
    return questions

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
            print(f"[maths] fetch error {url}: {e}")
    print(f"[maths] found {len(links)} papers")
    return links

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
            words = cleaned.split()
            for j in range(0, len(words), 100):
                chunk = " ".join(words[j:j+100])
                if _is_actual_question(chunk) and len(chunk) > 50:
                    chunks.append(chunk)
    except Exception as e:
        print(f"[maths] OCR error: {e}")
    return chunks

def _get_paper_chunks(url):
    if url in _paper_cache: return _paper_cache[url]
    try:
        r = requests.get(url, timeout=20)
        chunks = _ocr_pdf_bytes(r.content)
        _paper_cache[url] = chunks
        print(f"[maths] {len(chunks)} question chunks from {url.split('/')[-1]}")
    except Exception as e:
        print(f"[maths] paper fetch error: {e}")
        _paper_cache[url] = []
    return _paper_cache[url]

def _get_past_paper_question():
    links = _fetch_pdf_links(URLS_GR11)
    if not links:
        links = _fetch_pdf_links(URLS_GR10)
    if not links:
        print("[maths] no papers found")
        return None

    label, url = random.choice(links)
    print(f"[maths] using past paper: {label}")

    chunks = _get_paper_chunks(url)
    if not chunks:
        print("[maths] no question chunks")
        return None

    for _ in range(10):
        anchor = random.choice(chunks)
        if _is_actual_question(anchor) and len(anchor) > 80:
            break
    
    questions = _extract_questions_from_chunk(anchor)
    if questions:
        question_text = random.choice(questions)
    else:
        question_text = anchor
    
    if len(question_text) > 300:
        difficulty = "hard"
    elif len(question_text) > 150:
        difficulty = "medium"
    else:
        difficulty = "easy"
    
    return {
        "question": question_text[:3000],
        "answer": "Show your working step by step",
        "difficulty": difficulty,
        "topic": "Maths",
        "section": "Past Paper Question",
        "source": "STANMORE past paper",
        "subject": SUBJECT,
        "paper": label,
        "type": "past_paper",
        "time_limit": {"easy": 600, "medium": 900, "hard": 1200}[difficulty]
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
    print("[maths] No priority topics found, using past paper")
    return _get_past_paper_question()
