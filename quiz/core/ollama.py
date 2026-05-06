import ollama, json, re, math

MODEL = "llama3.2"
GRADE_MODEL = "mistral"
OPTS = {"num_thread": 4, "num_predict": 2048}

# ── accounting synonyms ───────────────────────────────────────────
ACCOUNTING_SYNONYMS = {
    "cost price": ["cost", "historical cost", "original cost", "purchase price"],
    "diminishing balance": [
        "reducing balance",
        "diminishing value",
        "book value method",
        "DBV",
    ],
    "straight line": ["SLD", "fixed instalment", "equal instalment"],
    "carrying value": ["book value", "net book value", "written down value", "NBV"],
    "depreciation": ["wear and tear", "amortisation", "write-off"],
    "residual value": ["scrap value", "salvage value", "trade-in value"],
    "trade receivables": ["debtors", "accounts receivable"],
    "trade payables": ["creditors", "accounts payable"],
    "retained income": ["retained earnings", "retained profit"],
    "income approach": ["revenue approach", "turnover method"],
}

def _synonym_hint_for_grader():
    return "\n".join(f'"{t}" = {", ".join(s)}' for t, s in ACCOUNTING_SYNONYMS.items())

# ── helpers ───────────────────────────────────────────────────────
def _chat(prompt, max_tokens=2048):
    resp = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={**OPTS, "num_predict": max_tokens},
    )
    return resp["message"]["content"].strip()

def _sanitize(blob):
    blob = re.sub(r"\\([a-zA-Z]+)", r"\\\\$1", blob)
    blob = re.sub(r'\\(?!["\\/bfnrtu0-9])', r"\\\\", blob)
    blob = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", blob)
    return blob

def _parse_json(raw):
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")
    blob = match.group(0)
    try:
        return json.loads(_sanitize(blob))
    except:
        pass
    result = {}
    for key in [
        "question",
        "difficulty",
        "topic",
        "section",
        "answer",
        "expected_keywords",
    ]:
        m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', blob)
        if m:
            result[key] = m.group(1)
    if "question" in result:
        return result
    raise ValueError("Could not parse JSON")

# ── question generation ───────────────────────────────────────────
MCQ_TRIGGERS = [
    "sketch",
    "draw",
    "graph",
    "plot",
    "diagram",
    "construct",
    "number line",
    "axes",
    "coordinate",
    "label the",
]

def _needs_mcq(prompt):
    return any(t in prompt.lower() for t in MCQ_TRIGGERS)

def generate_question(prompt):
    try:
        if _needs_mcq(prompt):
            prompt = re.sub(
                r"Respond ONLY in valid JSON.*",
                "The question must be multiple choice since it involves a visual/sketch task.\n"
                "Respond ONLY in valid JSON, no markdown:\n"
                '{"question": "...", "difficulty": "easy|medium|hard", "topic": "...", "section": "...", "answer": "A", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}}',
                prompt,
                flags=re.DOTALL,
            )
        prompt += "\nIMPORTANT: Write all scientific notation using ^ for exponents e.g. 5.98 x 10^24, NOT 5.98 · 10. Never truncate exponents."
        raw = _chat(prompt)
        return _parse_json(raw)
    except Exception as e:
        print(f"[ollama] generate error: {e}")
        return None

# ── numerical helpers ─────────────────────────────────────────────
def _extract_number(text):
    if not text:
        return None
    text = str(text).replace(",", ".")
    matches = re.findall(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?", text)
    if matches:
        try:
            return float(matches[0])
        except:
            return None
    return None

def _numbers_close(a, b, tolerance=0.05):
    if a is None or b is None:
        return False
    if b == 0:
        return abs(a) < 1e-9
    return abs(a - b) / abs(b) <= tolerance

# === VAGUE ANSWER SAFEGUARD ===
def _is_vague_answer(question, answer):
    if "differentiate" not in question.lower() and "difference between" not in question.lower():
        return False, None
    answer_lower = answer.lower()
    if "function" not in answer_lower and "purpose" not in answer_lower and "both" not in answer_lower:
        return True, "You described hardware, not function."
    if "non-volatile" not in answer_lower and "retain" not in answer_lower and "without power" not in answer_lower:
        return True, "Missing: both devices retain data when power is off."
    if len(answer.split()) < 25:
        return True, f"Answer too short ({len(answer.split())} words). Need context."
    return False, None

# ── grading ───────────────────────────────────────────────────────
def grade_answer(
    question, answer, correct_answer=None, expected_keywords=None, practical=False
):
    # Vague answer safeguard
    vague, reason = _is_vague_answer(question, answer)
    if vague:
        return {"correct": False, "partial": False, "feedback": f"❌ VAGUE. {reason} Marked wrong."}

    # ── practical (Delphi) ────────────────────────────────────────
    if practical:
        prompt = f"""You are grading a Grade 11 Delphi programming answer.
Question: {question}
Expected concepts: {', '.join(expected_keywords or [])}
Student answer:
{answer}

RULES - MARK CORRECT ONLY IF ALL ARE TRUE:
1. Valid Delphi syntax (var, begin, end, semicolons)
2. If question asks for Pos() - MUST be present
3. If question asks for SubStr() or Copy() - MUST be present
4. If question asks for BOTH - BOTH must be present
5. Proper variable declarations
6. Edge cases handled (e.g., if Pos returns 0)

If ANY required function is missing -> WRONG
If code is pseudo-code or English description -> WRONG
If missing var/begin/end -> WRONG
You MUST respond with ONLY this exact JSON and nothing else, no explanation:
{{"correct": true, "partial": false, "feedback": "one sentence"}}"""

    else:
        # ── Afrikaans Vraestel 3 — deduction-based grading ──────
        is_afr_p3 = (
            "vraestel 3" in str(question).lower()
            or "vraestel 3" in str(correct_answer or "").lower()
            or (
                "afrikaans" in str(question).lower()
                and any(
                    w in str(question).lower()
                    for w in ["opstel", "transaksioneel", "skryfwerk", "skryf ongeveer"]
                )
            )
        )

        if is_afr_p3:
            MAX_MARKS = 20
            prompt = f"""Jy is 'n NSC Afrikaans Huistaal Vraestel 3 nasiener.

Gebruik 'n AFTREKKINGSTELSEL:
- Begin by {MAX_MARKS}/20 (volpunte)
- Trek 1 punt af vir elke taalfout (spelling, grammatika, sinsbou, werkwoordvorme)
- Trek 1 punt af vir elke stylfout (woordkeuse, register, herhaling)
- Trek 5 punte af as die formaat verkeerd is (bv. opstel het geen paragrawe nie, of transaksionele teks het verkeerde struktuur)
- Minimum telling is 0

Vraag: {question}
Leerder se antwoord:
{answer}

Bereken:
1. Lys ELKE fout wat jy gevind het (taal of styl)
2. Formaatstraf: ja/nee en hoekom
3. Finale telling: {MAX_MARKS} minus aftrekkings
4. Persentasie: finale/20 x 100

Reël: >50% = korrek (quota), <=50% = verkeerd

Jy MOET reageer met SLEGS hierdie presiese JSON en niks anders nie:
{{"correct": true, "partial": false, "feedback": "telling: X/20 (Y%) — [lys foute hier]"}}"""

            for attempt in range(3):
                try:
                    resp = ollama.chat(
                        model=GRADE_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        options={"num_thread": 4, "num_predict": 800},
                    )
                    raw = resp["message"]["content"].strip()
                    parsed = _parse_json(raw)
                    if "correct" not in parsed:
                        continue
                    return parsed
                except Exception as e:
                    print(f"[ollama] afr_p3 grade attempt {attempt+1} error: {e}")
            return {
                "correct": False,
                "partial": False,
                "feedback": "Kon nie nasien nie — kyk self.",
            }

        # ── Paper 3 (essay/writing) — intro-only grading ─────────
        is_p3 = (
            "paper 3" in str(question).lower()
            or "paper 3" in str(correct_answer or "").lower()
        )
        if not is_p3:
            is_p3 = any(
                w in str(correct_answer or "").lower()
                for w in [
                    "essay",
                    "transactional",
                    "creative writing",
                    "approximately",
                    "words",
                ]
            )

        if is_p3:
            paragraphs = [p.strip() for p in str(answer).split("\n") if p.strip()]
            intro = paragraphs[0] if paragraphs else answer
            intro_words = intro.split()
            incoherent = (
                len(intro_words) < 10
                or len(set(intro_words)) < 5
                or not any(c in intro for c in ".!?")
            )
            read_full = incoherent
            grading_text = answer if read_full else intro
            depth_note = (
                "NOTE: Full essay read due to incoherent introduction."
                if read_full
                else "NOTE: Only the introduction was assessed (NSC marker style). If intro is strong, full essay assumed coherent."
            )

            prompt = f"""You are an NSC English Home Language Paper 3 marker.
{depth_note}

Question: {question}
Text assessed:
{grading_text[:1200]}

Mark according to NSC rubric:
- Does the introduction establish a clear topic/argument/narrative hook?
- Is the register appropriate for the task type (essay/transactional/creative)?
- Is the language controlled and purposeful?

If intro is strong and coherent: mark CORRECT (assume essay delivers).
If intro is weak, off-topic, or incoherent: mark WRONG with specific feedback.
Partial credit if intro shows some structure but lacks control.

You MUST respond with ONLY this exact JSON and nothing else:
{{"correct": true, "partial": false, "feedback": "one sentence"}}"""

            for attempt in range(3):
                try:
                    resp = ollama.chat(
                        model=GRADE_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        options={"num_thread": 4, "num_predict": 600},
                    )
                    raw = resp["message"]["content"].strip()
                    parsed = _parse_json(raw)
                    if "correct" not in parsed:
                        continue
                    return parsed
                except Exception as e:
                    print(f"[ollama] p3 grade attempt {attempt+1} error: {e}")
            return {
                "correct": False,
                "partial": False,
                "feedback": "Could not grade P3 — check manually.",
            }

        # ── MCQ short-circuit ─────────────────────────────────────
        if str(answer).strip().upper() in ["A", "B", "C", "D"] and correct_answer:
            sl = str(answer).strip().upper()
            cl = str(correct_answer).strip().upper()[0]
            if sl == cl:
                return {
                    "correct": True,
                    "partial": False,
                    "feedback": f"✅ Correct! The answer is {cl}.",
                }
            else:
                return {
                    "correct": False,
                    "partial": False,
                    "feedback": f"❌ Wrong. You chose {sl}, the correct answer is {cl}.",
                }

        # ── numerical short-circuit ───────────────────────────────
        is_lit = any(
            w in str(question).lower()
            for w in [
                "macbeth",
                "tsotsi",
                "paper 2",
                "paper2",
                "character",
                "theme",
                "literary device",
                "stanza",
                "essay",
                "discuss",
                "argue",
                "analyse",
                "analyze",
                "shakespeare",
                "fugard",
                "contextual",
            ]
        )
        student_num = None if is_lit else _extract_number(str(answer))
        expected_num = _extract_number(str(correct_answer)) if correct_answer else None

        if student_num is not None and expected_num is not None:
            if _numbers_close(student_num, expected_num):
                return {
                    "correct": True,
                    "partial": False,
                    "feedback": f"✅ Correct! ({correct_answer})",
                }
            else:
                extra = (
                    f"\nNOTE: correct answer is {expected_num:.4g}, "
                    f"student answered {student_num:.4g} — does NOT match within 5%."
                )
        else:
            extra = ""

        # ── subject detection ─────────────────────────────────────
        q = str(question).lower()
        is_physics = any(
            w in q
            for w in [
                "newton",
                "force",
                "energy",
                "wave",
                "electric",
                "gravit",
                "momentum",
                "current",
                "voltage",
                "optic",
                "thermodynam",
            ]
        )
        is_lang = not is_lit and any(
            w in q
            for w in [
                "passage",
                "text",
                "read",
                "extract",
                "skrywer",
                "teks",
                "comprehension",
                "indruk",
                "advertis",
                "afrikaans",
                "english",
                "poem",
                "stanza",
            ]
        )
        is_lo = any(
            w in q
            for w in [
                "orientation",
                "community",
                "career",
                "health",
                "life skills",
                "citizenship",
                "principal",
                "school policy",
            ]
        )
        is_acc = any(
            w in q
            for w in [
                "depreciation",
                "ledger",
                "balance sheet",
                "income statement",
                "debit",
                "credit",
                "vat",
                "journal",
            ]
        )
        syn_hint = _synonym_hint_for_grader() if is_acc else ""

        # ── build rule string ─────────────────────────────────────
        rules = []
        if is_lit:
            rules.append(
                "LITERATURE: mark CORRECT only if the student makes a clear argument WITH textual evidence. "
                "Vague or generic answers with no reference to the text = WRONG. "
                "For essay/theme/character: require at least one specific example or quote. "
                "For contextual questions: answer must directly address the quoted line. "
                "Partial credit if argument present but evidence is weak."
            )
        if is_lang:
            rules.append(
                "LANG: mark CORRECT if student shows ANY valid understanding of the text. "
                "Wording does NOT need to match reference. "
                "Mark WRONG only if answer is completely irrelevant."
            )
        if is_lo:
            rules.append(
                "LO: mark CORRECT if answer is sensible and practical. "
                "Any reasonable response addressing the question = correct."
            )
        if is_acc and syn_hint:
            rules.append(f"ACCOUNTING SYNONYMS — treat as equivalent:\n{syn_hint}")
        is_maths = any(
            w in q
            for w in [
                "equation",
                "solve",
                "calculate",
                "simplify",
                "factorise",
                "complete the square",
                "quadratic",
                "trigonometry",
                "geometry",
                "differentiate",
                "integrate",
                "sine",
                "cosine",
                "tangent",
                "logarithm",
                "exponent",
                "inequality",
            ]
        )
        is_exact = any(
            w in q
            for w in [
                "define",
                "definition",
                "difference between",
                "what is meant",
                "explain the term",
                "give two",
                "give three",
                "list",
                "name two",
                "name three",
                "state",
                "what does",
                "what are",
            ]
        )

        if is_physics:
            rules.append(
                "PHYSICS FORMULA: end feedback with the formula used e.g. 'Formula: F = ma'."
            )
            rules.append(
                "CA MARKS: if student shows correct formula and substitution but wrong final answer: partial=true. "
                "If student shows wrong formula or no working: correct=false, partial=false."
            )
        else:
            rules.append(
                "NO FORMULA: do NOT include any formula or equation in feedback."
            )

        if is_maths:
            rules.append(
                "MATHS CA: check arithmetic strictly. "
                "If method is correct (right technique, right setup) but arithmetic wrong: partial=true, correct=false. "
                "If method is wrong: correct=false, partial=false. "
                "If both method and answer correct: correct=true. "
                "NEVER mark correct if the final value is wrong even if method looks right."
            )

        if is_exact:
            rules.append(
                "EXACT TERMINOLOGY: this is a definition/recall question. "
                "Mark CORRECT only if answer uses precise terminology matching the reference. "
                "Vague or paraphrased answers without key terms = WRONG. "
                "No partial credit for definitions — either the term is correct or it is not."
            )

        if is_acc:
            rules.append(
                "ACCOUNTING EXACT: wrong account name or wrong side of entry = WRONG. "
                "Method marks apply for correct journal structure even if one account wrong."
            )

        rules.append(
            "DEFAULT: mark CORRECT if core idea matches reference, even if wording differs."
        )

        rule_str = "\n".join(f"- {r}" for r in rules)

        prompt = f"""Grade this Grade 11 answer. These rules are ABSOLUTE and override your own judgment:

{rule_str}

Question: {question}
Reference answer: {correct_answer or "use subject knowledge"}
Student answer: {answer}{extra}

If wrong answer but correct method/formula/substitution shown: set partial=true, correct=false.
You MUST respond with ONLY this exact JSON and nothing else, no explanation:
{{"correct": true, "partial": false, "feedback": "one sentence"}}"""

    # ── send to Mistral ───────────────────────────────────────────
    for attempt in range(3):
        try:
            resp = ollama.chat(
                model=GRADE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"num_thread": 4, "num_predict": 600},
            )
            raw = resp["message"]["content"].strip()
            parsed = _parse_json(raw)
            if "correct" not in parsed:
                print(
                    f"[ollama] grade attempt {attempt+1}: missing 'correct' key, got: {parsed}"
                )
                continue
            return parsed
        except Exception as e:
            print(f"[ollama] grade attempt {attempt+1} error: {e}")
    try:
        is_correct = any(
            w in raw.lower() for w in ["correct", "right", "yes", "well done"]
        )
        return {"correct": is_correct, "partial": False, "feedback": raw[:200]}
    except:
        return {
            "correct": False,
            "partial": False,
            "feedback": "Could not grade — check your answer manually.",
        }

# ── roast ─────────────────────────────────────────────────────────
def roast(question):
    prompt = f"""The student was asked: "{question}"
They left it completely blank and let the timer run out.
Write a savage but funny roast (3-4 sentences) like a disappointed sarcastic teacher.
Do not be genuinely cruel, but do not hold back."""
    try:
        return _chat(prompt, max_tokens=200)
    except Exception as e:
        return f"You left it blank. I have no words. ({e})"

def blank_roast(question_topic=""):
    """Return a brutal roast for blank answers"""
    import random
    roasts = [
        "This answer is your future: empty, desolate, and wrong.",
        "The void is empty. So is your answer. Coincidence?",
        "You left it blank? Even a feature phone has more features than your answer.",
        "Your answer had 0 words. My disappointment has infinite.",
        "Skill issue. The answer was literally in the question.",
        "Congratulations. You've achieved nothing. Literally.",
        "The blank stares back at you. And judges you.",
        f"You couldn't even guess? '{question_topic}' is in the NAME. Skill issue.",
        "I've seen more effort in a brick.",
        "Your answer is like your gaming time after this: nonexistent.",
    ]
    return random.choice(roasts)

def clean_latex_question(question_text):
    """Remove LaTeX delimiters that confuse students"""
    import re
    cleaned = re.sub(r"\\\(|\\\)|\\\[|\\\]", "", question_text)
    return cleaned

def is_blank_answer(answer):
    """Check if answer is effectively blank"""
    if not answer or len(answer.strip()) == 0:
        return True
    gibberish = ["wtf", "wrf", "asdf", "qwerty", "lol", "idk", "dunno", "what", "huh"]
    if answer.strip().lower() in gibberish:
        return True
    words = answer.strip().split()
    if len(words) == 1 and len(words[0]) < 3 and not any(c.isdigit() for c in words[0]):
        return True
    return False

def harsh_blank_roast(question_topic=""):
    """Return a brutal roast for blank or gibberish answers"""
    import random
    roasts = [
        "This answer is your future: empty, desolate, and wrong.",
        "The void is empty. So is your answer. Coincidence?",
        "You left it blank? Even a feature phone has more features than your answer.",
        f"You wrote gibberish. The question was about {question_topic}. Skill issue.",
        "Your answer had 0 correct characters. My disappointment has infinite.",
        "Congratulations. You've achieved nothing. Literally.",
        "The blank stares back at you. And judges you.",
        "WTF is not a mathematical constant. Try again.",
        "You saw dollar signs and panicked. The equation is right there.",
        "If you don't know, guess. But 'wrf'? That's not a guess. That's surrender.",
        "The exam will not accept keyboard smashing. Neither will I.",
    ]
    return random.choice(roasts)

def grade_delphi_code(question, answer, expected_keywords):
    """Strict grader for Delphi code"""
    prompt = f"""You are a strict Grade 11 IT Delphi examiner.

Question: {question}
Expected keywords/concepts: {', '.join(expected_keywords or [])}
Student's code:
{answer}

Mark CORRECT ONLY if:
1. The code is valid Delphi syntax
2. It uses the required functions (Pos, Copy, Length, etc.)
3. It has proper var declarations
4. It has begin/end blocks
5. It handles edge cases (e.g., if Pos = 0)
6. It is NOT vague or pseudo-code

Mark WRONG if:
- The code is pseudo-code or English description
- Missing required syntax elements
- No error handling where needed
- Too short or vague

Respond with ONLY this JSON:
{{"correct": true/false, "partial": false, "feedback": "one sentence explanation"}}"""
    
    return _call_ollama(prompt)
