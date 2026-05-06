import random
from pathlib import Path
from quiz.core.files import extract_chunks
from quiz.core import ollama as ai

SUBJECT    = "IT"
STUDIES_IT = Path.home() / "studies/IT"
_content   = None

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
        
        # Filter for IT only
        subject_topics = [t for t in topics if t['subject'].lower() == 'it']
        
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
            print(f"[IT] PRIORITY: Lowest tier (0-40%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
        elif r < 0.9 and middle:
            selected = random.choice(middle)
            print(f"[IT] PRIORITY: Middle tier (40-70%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
        elif highest:
            selected = random.choice(highest)
            print(f"[IT] PRIORITY: Highest tier (70-100%) - {selected['topic']} ({selected['accuracy']:.0f}%)")
            return selected
    except Exception as e:
        print(f"[IT] Priority error: {e}")
    return None

def _generate_question_for_topic(topic_name):
    """Generate a question for a specific IT topic by forcing the AI"""
    print(f"[IT] Generating question for priority topic: {topic_name}")
    
    # Force the AI to generate a question on this specific topic
    c = _load_content()
    atp_pool = c["atp_gr11"] if (c["atp_gr11"] and random.random() < 0.75) else c["atp_gr10"]
    if not atp_pool:
        atp_pool = c["atp_gr11"] + c["atp_gr10"]
    
    if not atp_pool:
        print("[IT] no ATP content loaded")
        return None
    
    # Pick a random ATP chunk and hope it's relevant
    atp_anchor = random.choice(atp_pool)
    practical = random.random() < 0.5
    
    if practical:
        matched = _best_handbook_match(atp_anchor, c["handbook"], top_n=2)
        handbook_ctx = "\n---\n".join(matched)
        prompt = f"""You are a South African Grade 11 IT exam question generator for Paper 1 (Delphi practical).
Focus specifically on the topic: {topic_name}
The question MUST be based on this ATP syllabus excerpt:
\"\"\"
{atp_anchor[:600]}
\"\"\"
Relevant Delphi handbook reference:
\"\"\"
{handbook_ctx[:800]}
\"\"\"
Generate ONE practical Delphi coding question that tests {topic_name}.
Respond ONLY in valid JSON, no markdown:
{{"question": "...", "difficulty": "easy|medium|hard", "topic": "...", "section": "...", "answer": "...", "expected_keywords": ["kw1", "kw2"]}}"""
    else:
        theory_ctx = random.choice(c["theory"]) if c["theory"] else ""
        prompt = f"""You are a South African Grade 11 IT exam question generator for Paper 2 (theory).
Focus specifically on the topic: {topic_name}
The question MUST be based on this ATP syllabus excerpt:
\"\"\"
{atp_anchor[:600]}
\"\"\"
Supporting theory content:
\"\"\"
{theory_ctx[:600]}
\"\"\"
Generate ONE theory question that tests {topic_name} following NSC Paper 2 style.
Respond ONLY in valid JSON, no markdown:
{{"question": "...", "difficulty": "easy|medium|hard", "topic": "...", "section": "...", "answer": "..."}}"""
    
    q = ai.generate_question(prompt)
    if q:
        q["subject"] = SUBJECT
        q["type"] = "practical" if practical else "theory"
        # Ensure topic is set properly
        if "topic" not in q or not q["topic"]:
            q["topic"] = topic_name
    return q

# ============================================
# EXISTING FUNCTIONS (unchanged)
# ============================================

def _load_content():
    global _content
    if _content is not None: return _content
    _content = {"handbook": [], "atp_gr11": [], "atp_gr10": [], "theory": []}
    for f in STUDIES_IT.iterdir():
        name = f.name.lower()
        chunks = extract_chunks(f)
        if "delphi" in name or "handbook" in name:
            _content["handbook"].extend(chunks)
        elif any(x in name for x in ["gr 11", "gr11", " 11 "]):
            _content["atp_gr11"].extend(chunks)
        elif any(x in name for x in ["gr 10", "gr10", " 10 "]):
            _content["atp_gr10"].extend(chunks)
        elif f.suffix == ".epub":
            _content["theory"].extend(chunks)
    print(f"[IT] handbook:{len(_content['handbook'])} theory:{len(_content['theory'])} "
          f"atp11:{len(_content['atp_gr11'])} atp10:{len(_content['atp_gr10'])}")
    return _content

def _keywords(text, min_len=4):
    stopwords = {"with","that","this","from","have","been","will","their",
                 "which","they","there","when","what","used","using","into",
                 "should","would","could","about","after","before","other"}
    words = text.lower().split()
    return {w.strip(".,;:()[]") for w in words
            if len(w) >= min_len and w not in stopwords}

def _best_handbook_match(atp_chunk, handbook_chunks, top_n=3):
    if not handbook_chunks: return []
    atp_kw = _keywords(atp_chunk)
    scored = []
    for chunk in handbook_chunks:
        overlap = len(atp_kw & _keywords(chunk))
        scored.append((overlap, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    result = [c for score, c in scored[:top_n] if score > 0]
    return result if result else random.sample(handbook_chunks, min(top_n, len(handbook_chunks)))

def get_question(practical=None):
    """Three-tier priority: weakest topics first, then AI-generated"""
    
    # Try priority system first
    priority_topic = _get_priority_topic()
    if priority_topic:
        return _generate_question_for_topic(priority_topic['topic'])
    
    # Fallback to existing logic
    print("[IT] No priority topics found, using standard generation")
    
    c = _load_content()
    if practical is None:
        practical = random.random() < 0.5

    atp_pool = c["atp_gr11"] if (c["atp_gr11"] and random.random() < 0.75) else c["atp_gr10"]
    if not atp_pool:
        atp_pool = c["atp_gr11"] + c["atp_gr10"]

    if not atp_pool:
        print("[IT] no ATP content loaded")
        return None

    atp_anchor = random.choice(atp_pool)

    if practical:
        matched = _best_handbook_match(atp_anchor, c["handbook"], top_n=2)
        handbook_ctx = "\n---\n".join(matched)
        prompt = f"""You are a South African Grade 11 IT exam question generator for Paper 1 (Delphi practical).

The question MUST be based on this ATP syllabus excerpt:
\"\"\"
{atp_anchor[:600]}
\"\"\"

Relevant Delphi handbook reference:
\"\"\"
{handbook_ctx[:800]}
\"\"\"

Generate ONE practical Delphi coding question that:
- Matches real NSC Paper 1 style — short, specific, ONE clear task only
- Names the EXACT Delphi function or operation to use
- Is appropriate for Grade 11 Paper 1
- Does NOT ask the student to explain theory
- Does NOT ask for a full program or GUI design
- If the ATP mentions file handling, the question MUST test text file operations
- The answer MUST include complete valid Delphi syntax: var declarations with semicolons, begin, end; and proper := assignments
- The answer MUST handle edge cases e.g. if Pos returns 0, if file does not exist

Respond ONLY in valid JSON, no markdown:
{{"question": "...", "difficulty": "easy|medium|hard", "topic": "...", "section": "...", "answer": "...", "expected_keywords": ["kw1", "kw2"]}}"""
    else:
        theory_ctx = random.choice(c["theory"]) if c["theory"] else ""
        prompt = f"""You are a South African Grade 11 IT exam question generator for Paper 2 (theory).

The question MUST be based on this ATP syllabus excerpt:
\"\"\"
{atp_anchor[:600]}
\"\"\"

Supporting theory content:
\"\"\"
{theory_ctx[:600]}
\"\"\"

Generate ONE theory question that strictly follows NSC Paper 2 style:
- Use EXACT NSC instruction words: Define, Explain, Describe, Differentiate between, Give an example of, Motivate, Discuss, List, Name
- Include mark allocation in the question
- Question must test ONE specific concept only
- Answer must use EXACT NSC terminology

Respond ONLY in valid JSON, no markdown:
{{"question": "...", "difficulty": "easy|medium|hard", "topic": "...", "section": "...", "answer": "..."}}"""

    q = ai.generate_question(prompt)
    if q:
        PAT_TRIGGERS = [
            "user interface", "gui", "form", "design a", "create a program",
            "develop a", "application that", "user account", "login form",
            "registration", "database application", "full program",
            "complete program", "main menu", "multiple forms", "splash screen"
        ]
        question_lower = q.get("question", "").lower()
        if any(t in question_lower for t in PAT_TRIGGERS):
            print(f"[IT] filtered PAT question: {q.get('question','')[:60]}...")
            return None
        q["subject"] = SUBJECT
        q["type"] = "practical" if practical else "theory"
    return q

# Expected keywords for common IT topics
EXPECTED_KEYWORDS = {
    "differentiate between a hard drive and a storage device": [
        "hard drive", "storage device", "specific type", "broader category",
        "magnetic platters", "non-volatile", "long-term storage"
    ],
    "differentiate between ram and rom": [
        "volatile", "non-volatile", "temporary", "permanent", "read/write", "read-only"
    ],
    "define hardware and software": [
        "physical components", "programs", "instructions", "tangible", "intangible"
    ]
}

def check_keywords(answer, topic):
    answer_lower = answer.lower()
    topic_lower = topic.lower()
    for key, keywords in EXPECTED_KEYWORDS.items():
        if key in topic_lower:
            missing = [kw for kw in keywords if kw.lower() not in answer_lower]
            if missing:
                return False, f"Missing keywords: {', '.join(missing[:3])}"
            return True, "All keywords present"
    return True, "No keyword check defined"

def validate_answer_completeness(question, answer):
    answer_lower = answer.lower()
    question_lower = question.lower()
    if len(answer) < 50:
        return False, "Answer too short - provide complete code with var, begin, end"
    required_parts = ['var', 'begin', 'end']
    missing = [p for p in required_parts if p not in answer_lower]
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    if 'pos' in question_lower and 'substr' in question_lower:
        if 'pos' not in answer_lower:
            return False, "Missing Pos() function - required by question"
        if 'substr' not in answer_lower and 'copy' not in answer_lower:
            return False, "Missing SubStr() or Copy() function - required by question"
    if 'file' in question_lower or 'text file' in question_lower:
        file_ops = ['assign', 'reset', 'rewrite', 'append', 'readln', 'writeln', 'closefile']
        has_file_ops = any(op in answer_lower for op in file_ops)
        if not has_file_ops:
            return False, f"Missing file operations - need Assign, Reset/Rewrite, CloseFile"
    return True, "Complete"

def grade_it_answer(question, answer, correct_answer=None, expected_keywords=None):
    is_complete, msg = validate_answer_completeness(question, answer)
    if not is_complete:
        return {"correct": False, "feedback": msg, "roast": f"❌ {msg}"}
    if expected_keywords:
        answer_lower = answer.lower()
        missing = [kw for kw in expected_keywords if kw.lower() not in answer_lower]
        if missing:
            return {"correct": False, "feedback": f"Missing: {', '.join(missing[:3])}", "roast": f"❌ Missing required elements: {', '.join(missing[:3])}"}
    return {"correct": True, "feedback": "Complete and correct!", "roast": "✅ Good job!"}
