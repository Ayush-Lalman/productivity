import random, requests, io, fitz, pytesseract, re, json
from PIL import Image, ImageEnhance, ImageFilter
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

SUBJECT = "Afrikaans"
LEVEL = "HL"

# Paper 1 and Paper 3 only
URLS_GR10 = ["https://stanmorephysics.com/afrikaans-grade-10/"]
URLS_GR11 = ["https://stanmorephysics.com/afrikaans-grade-11/"]
URLS_GR12 = ["https://stanmorephysics.com/afrikaans-grade-12/"]

ALL_URLS = URLS_GR10 + URLS_GR11 + URLS_GR12

# Paper filters
WANT_PAPERS = ["P1", "P3", "PAPER-1", "PAPER-3"]
SKIP_PAPERS = ["P2", "PAPER-2"]

# Keywords to filter out (exam instructions)
INSTRUCTION_KEYWORDS = [
    "AFDELING", "MINUTE", "Nommer", "Skryf", "Dui", "getal", "woorde", "netjies",
    "INSTRUCTIONS", "SECTION", "MARKS", "TIME", "COPYRIGHT", "PTO", "TURN OVER",
    "ANSWER ALL", "NUMBER THE ANSWERS", "LEAVE ONE LINE", "CALCULATOR",
    "ROUND OFF", "SHOW ALL CALCULATIONS", "BL. ", "VEVCCEEF"
]

SKIP_KEYWORDS = [
    "SCOPE", "ATP", "POA", "TIMETABLE", "GUIDELINES",
    "TEACHER", "LEARNER", "SUPPORT", "JIT", "STEP-AHEAD",
    "MEMO", "SOLUTION"
]

WANT_PROVINCES = ["KZN", "GP", "GAUTENG"]

_paper_cache = {}

# ============================================
# SKILL TRACKING
# ============================================

SKILLS_DB = Path.home() / ".local/share/quiz-daemon/afrikaans_skills.json"

def load_skills():
    if SKILLS_DB.exists():
        try:
            with open(SKILLS_DB, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "editing": {"correct": 0, "wrong": 0, "last_seen": None},
        "photo_literacy": {"correct": 0, "wrong": 0, "last_seen": None},
        "summary": {"correct": 0, "wrong": 0, "last_seen": None},
        "comprehension": {"correct": 0, "wrong": 0, "last_seen": None},
        "essay": {"correct": 0, "wrong": 0, "last_seen": None},
        "letter": {"correct": 0, "wrong": 0, "last_seen": None},
        "dialogue": {"correct": 0, "wrong": 0, "last_seen": None},
        "picture_writing": {"correct": 0, "wrong": 0, "last_seen": None},
        "obituary": {"correct": 0, "wrong": 0, "last_seen": None},
        "eulogy": {"correct": 0, "wrong": 0, "last_seen": None}
    }

def save_skills(skills):
    SKILLS_DB.write_text(json.dumps(skills, indent=2))

def record_skill_result(skill, correct):
    skills = load_skills()
    if skill in skills:
        if correct:
            skills[skill]["correct"] += 1
        else:
            skills[skill]["wrong"] += 1
        skills[skill]["last_seen"] = datetime.now().isoformat()
        save_skills(skills)

def get_skill_accuracy(skill):
    skills = load_skills()
    if skill in skills:
        total = skills[skill]["correct"] + skills[skill]["wrong"]
        if total > 0:
            return skills[skill]["correct"] / total
    return 0.5

def get_weakest_skill():
    skills = load_skills()
    weakest = None
    lowest_acc = 1.0
    for skill, data in skills.items():
        total = data["correct"] + data["wrong"]
        if total > 0:
            acc = data["correct"] / total
        else:
            acc = 0.5
        if acc < lowest_acc:
            lowest_acc = acc
            weakest = skill
    return weakest, lowest_acc

# ============================================
# OCR FILTERING
# ============================================

def is_instruction_line(line):
    """Check if a line is an exam instruction (not a question)"""
    line_upper = line.upper()
    for kw in INSTRUCTION_KEYWORDS:
        if kw in line_upper:
            return True
    # Too short lines are likely not questions
    if len(line.strip()) < 30:
        return True
    return False

def filter_instructions(text):
    """Remove instruction lines from OCR text"""
    lines = text.split('\n')
    filtered_lines = []
    for line in lines:
        if not is_instruction_line(line):
            filtered_lines.append(line)
    result = '\n'.join(filtered_lines)
    # Also remove common patterns
    patterns = [
        r'Copyright reserved.*',
        r'Please turn over.*',
        r'PTO.*',
        r'BL\.\s*\d+.*',
    ]
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    return result.strip()

def is_actual_question(text):
    """Check if text looks like a real question (not instructions)"""
    if len(text) < 50:
        return False
    
    # Must contain question indicators
    q_indicators = [
        '?', 'vraag', 'vrae', 'skryf', 'bespreek', 'verduidelik', 
        'waarom', 'hoe', 'wat', 'noem', 'gee', 'bereken', 'bepaal'
    ]
    text_lower = text.lower()
    has_indicator = any(kw in text_lower for kw in q_indicators)
    if not has_indicator:
        return False
    
    # Check instruction density
    instruction_count = sum(1 for kw in INSTRUCTION_KEYWORDS if kw.lower() in text_lower)
    if instruction_count > 3:
        return False
    
    return True

# ============================================
# PAPER FILTERING
# ============================================

def _is_wanted_paper(combined):
    combined_upper = combined.upper()
    if any(k in combined_upper for k in SKIP_PAPERS):
        return False
    return any(k in combined_upper for k in WANT_PAPERS)

def _is_wanted(href, text):
    combined = (href + " " + text).upper()
    if not href.endswith('.pdf'):
        return False
    if any(k in combined for k in SKIP_KEYWORDS):
        return False
    has_province = any(p in combined for p in WANT_PROVINCES)
    has_paper = _is_wanted_paper(combined)
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
                if href in seen:
                    continue
                if not _is_wanted(href, text):
                    continue
                seen.add(href)
                links.append((text or href.split('/')[-1], href))
        except Exception as e:
            print(f"[afrikaans] fetch error {url}: {e}")
    print(f"[afrikaans] found {len(links)} papers (P1/P3 only)")
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
            
            cleaned = _clean_text(text)
            filtered = filter_instructions(cleaned)
            
            if is_actual_question(filtered) and len(filtered) > 100:
                words = filtered.split()
                for j in range(0, len(words), 150):
                    chunk = " ".join(words[j:j+150])
                    if len(chunk) > 100:
                        chunks.append(chunk)
    except Exception as e:
        print(f"[afrikaans] OCR error: {e}")
    return chunks

def _get_paper_chunks(url):
    if url in _paper_cache:
        return _paper_cache[url]
    try:
        r = requests.get(url, timeout=20)
        chunks = _ocr_pdf_bytes(r.content)
        _paper_cache[url] = chunks
        print(f"[afrikaans] {len(chunks)} content chunks from {url.split('/')[-1]}")
    except Exception as e:
        print(f"[afrikaans] paper fetch error: {e}")
        _paper_cache[url] = []
    return _paper_cache[url]

def _get_past_paper_question():
    links = _fetch_pdf_links(ALL_URLS)
    if not links:
        print("[afrikaans] no papers found")
        return None

    label, url = random.choice(links)
    print(f"[afrikaans] using: {label}")

    chunks = _get_paper_chunks(url)
    if not chunks:
        print("[afrikaans] no content chunks")
        return None

    for _ in range(10):
        anchor = random.choice(chunks)
        if is_actual_question(anchor) and len(anchor) > 100:
            break
    
    # Determine paper type (P1 or P3) from URL
    paper_type = "P1" if "P1" in url.upper() or "PAPER-1" in url.upper() else "P3"
    
    return {
        "question": anchor[:2000],
        "answer": "Provide your answer in Afrikaans",
        "difficulty": "medium",
        "topic": f"Afrikaans {paper_type}",
        "section": "Past Paper",
        "source": "STANMORE past paper",
        "subject": SUBJECT,
        "paper": label,
        "type": "past_paper",
        "time_limit": 900
    }

def _get_skill_question(skill):
    """Generate a question based on the skill that needs practice"""
    questions = {
        "editing": "Verbeter die volgende sinne: (a) Hy het my gesien en toe het hy vir my gegroet. (b) Die man wat daar staan is my oom.",
        "photo_literacy": "Beskryf die prent in detail. Wat dink jy gebeur hier? Wat is die boodskap?",
        "summary": "Lees die volgende teks en gee 'n opsomming in 50-60 woorde.",
        "comprehension": "Beantwoord die volgende vrae oor die teks wat jy gelees het.",
        "essay": "Skryf 'n opstel van 300-350 woorde oor een van die volgende onderwerpe...",
        "letter": "Skryf 'n formele brief aan die redakteur oor...",
        "dialogue": "Skryf 'n dialoog tussen twee karakters wat...",
        "picture_writing": "Kyk na die prent en skryf 'n kort storie (100-150 woorde).",
        "obituary": "Skryf 'n doodsberig vir 'n bekende persoon.",
        "eulogy": "Skryf 'n lofrede vir 'n vriend wat oorlede is."
    }
    return {
        "question": questions.get(skill, questions["essay"]),
        "answer": "Antwoord sal beoordeel word op inhoud, taalgebruik en struktuur.",
        "difficulty": "medium",
        "topic": f"Afrikaans - {skill}",
        "section": "Skill Practice",
        "source": "Skill-based question",
        "subject": SUBJECT,
        "type": "skill_practice",
        "time_limit": 1200
    }

def get_question():
    """Get question based on weakest skill or fall back to past papers"""
    
    # Get weakest skill
    weakest_skill, acc = get_weakest_skill()
    
    # If a skill is below 70% accuracy, prioritize it
    if weakest_skill and acc < 0.7:
        print(f"[afrikaans] PRIORITY: Weakest skill '{weakest_skill}' ({acc:.0%})")
        return _get_skill_question(weakest_skill)
    
    # Priority from ATP comparator (if any)
    try:
        from atp_comparator import get_all_topics_with_accuracy
        topics = get_all_topics_with_accuracy()
        if topics:
            for topic in topics:
                if topic.get('subject', '').lower() == 'afrikaans' and topic.get('accuracy', 100) < 70:
                    print(f"[afrikaans] ATP PRIORITY: {topic['topic']} ({topic['accuracy']:.0%})")
                    return _get_past_paper_question()
    except:
        pass
    
    # Fallback to past papers
    print("[afrikaans] No weak skills found, using past paper")
    return _get_past_paper_question()
