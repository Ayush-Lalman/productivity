#!/usr/bin/env python3
"""
Generic Delphi Code Grader
Works for ANY Delphi code: string handling, arrays, text files, databases, OOP
"""

import re
import subprocess
import tempfile
from pathlib import Path

# ============================================
# DELPHI SYNTAX VALIDATION
# ============================================

# Required Delphi syntax patterns (generic)
REQUIRED_PATTERNS = {
    "var_section": r"\bvar\s+",
    "begin_end": r"\bbegin\b.*\bend\.\s*$",
    "assignment": r":=",
    "semicolon": r";",
}

# Common Delphi keywords by topic
TOPIC_PATTERNS = {
    "string_handling": {
        "pos": r"Pos\s*\(",
        "copy": r"Copy\s*\(",
        "length": r"Length\s*\(",
        "delete": r"Delete\s*\(",
        "insert": r"Insert\s*\(",
    },
    "arrays": {
        "array_declare": r"array\s+of",
        "array_index": r"\[\d+\]",
        "for_loop": r"\bfor\b.*\bdo\b",
    },
    "text_files": {
        "assignfile": r"AssignFile\s*\(",
        "reset": r"Reset\s*\(",
        "rewrite": r"Rewrite\s*\(",
        "readln": r"ReadLn\s*\(",
        "writeln": r"WriteLn\s*\(",
        "closefile": r"CloseFile\s*\(",
    },
    "if_statement": {
        "if_then": r"\bif\b.*\bthen\b",
        "if_else": r"\bif\b.*\bthen\b.*\belse\b",
    },
    "loops": {
        "for": r"\bfor\b.*\bdo\b",
        "while": r"\bwhile\b.*\bdo\b",
        "repeat": r"\brepeat\b.*\buntil\b",
    },
}


def detect_topic(code):
    """Auto-detect what the code is trying to do"""
    code_lower = code.lower()
    topics_found = []

    for topic, patterns in TOPIC_PATTERNS.items():
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, code_lower, re.IGNORECASE):
                topics_found.append(topic)
                break

    # Remove duplicates and return most specific
    return list(set(topics_found))


def validate_delphi_syntax(code):
    """Check if code has basic Delphi syntax"""
    errors = []

    # Check for var section
    if not re.search(REQUIRED_PATTERNS["var_section"], code, re.IGNORECASE):
        errors.append("Missing 'var' section")

    # Check for begin/end
    if not re.search(REQUIRED_PATTERNS["begin_end"], code, re.DOTALL):
        errors.append("Missing 'begin' or 'end'")

    # Check for assignment operator
    if not re.search(REQUIRED_PATTERNS["assignment"], code):
        errors.append("No assignment operator (:=) found")

    return errors


def compile_delphi_check(code):
    """Try to check Delphi syntax using external compiler (optional)"""
    # This would require a Delphi compiler installed
    # For now, skip actual compilation
    return True, "Compilation check passed (simulated)"


def grade_delphi_code(user_code, question_prompt=""):
    """
    Grade any Delphi code based on:
    1. Basic syntax (var, begin, end, :=)
    2. Topic-specific keywords
    3. Logical structure
    """
    score = 100
    feedback = []

    # 1. Basic syntax validation
    syntax_errors = validate_delphi_syntax(user_code)
    if syntax_errors:
        score -= len(syntax_errors) * 15
        feedback.append(f"Syntax errors: {', '.join(syntax_errors)}")

    # 2. Detect what the code is trying to do
    topics = detect_topic(user_code)
    if not topics:
        feedback.append("⚠️ Could not determine the purpose of your code")
        score -= 20

    # 3. Check for common mistakes
    common_errors = [
        (r"if\s+\w+\s*\(", "Using variable as function (like ipos(stext))"),
        (r"=\s*0\s+then\s*$", "Missing assignment before comparison"),
        (r"\bend\s*;?\s*end\b", "Too many 'end' statements"),
        (r"begin\s*begin", "Nested 'begin' without proper structure"),
    ]

    for pattern, error_msg in common_errors:
        if re.search(pattern, user_code, re.IGNORECASE):
            score -= 20
            feedback.append(f"❌ {error_msg}")

    # 4. Topic-specific validation
    if "string_handling" in topics:
        if not re.search(r"Pos\s*\(|Copy\s*\(|Length\s*\(", user_code, re.IGNORECASE):
            score -= 30
            feedback.append(
                "❌ String handling question requires Pos(), Copy(), or Length()"
            )

    if "arrays" in topics:
        if not re.search(r"array\s+of|\[\d+\]", user_code, re.IGNORECASE):
            score -= 30
            feedback.append("❌ Array question requires array declaration or indexing")

    if "text_files" in topics:
        file_keywords = [
            "assignfile",
            "reset",
            "rewrite",
            "readln",
            "writeln",
            "closefile",
        ]
        found = any(re.search(kw, user_code, re.IGNORECASE) for kw in file_keywords)
        if not found:
            score -= 30
            feedback.append(
                "❌ Text file question requires file operations (AssignFile, Reset, ReadLn, etc.)"
            )

    if "if_statement" in topics:
        if not re.search(r"\bif\b.*\bthen\b", user_code, re.IGNORECASE):
            score -= 25
            feedback.append("❌ Missing 'if...then' structure")

    if "loops" in topics:
        loop_keywords = ["for", "while", "repeat"]
        found = any(re.search(kw, user_code, re.IGNORECASE) for kw in loop_keywords)
        if not found:
            score -= 25
            feedback.append("❌ Missing loop structure (for/while/repeat)")

    # 5. Check for empty else or missing implementation
    if re.search(r"else\s*begin\s*end", user_code, re.IGNORECASE):
        score -= 10
        feedback.append("⚠️ Empty else block - implement or remove")

    # 6. Check for commented code (partial implementation)
    if re.search(r"//.*TODO|//.*FIXME", user_code, re.IGNORECASE):
        feedback.append("⚠️ TODO/FIXME found - incomplete implementation")
        score -= 10

    # Cap score at 0
    score = max(0, score)

    # Determine grade level
    if score >= 90:
        grade = "Excellent"
    elif score >= 75:
        grade = "Good"
    elif score >= 60:
        grade = "Satisfactory"
    elif score >= 40:
        grade = "Needs Improvement"
    else:
        grade = "Inadequate"

    return {
        "score": score,
        "grade": grade,
        "feedback": feedback if feedback else ["✓ Code looks valid"],
        "detected_topics": topics,
        "is_valid": score >= 50,
    }


def get_exam_feedback(user_code, question_prompt=""):
    """Generate exam-style feedback (harsh but fair)"""
    result = grade_delphi_code(user_code, question_prompt)

    if result["score"] >= 90:
        feedback = "✓ Correct. Exam-ready code."
    elif result["score"] >= 75:
        feedback = "⚠️ Minor issues. Would lose 1-2 marks in exam."
    elif result["score"] >= 60:
        feedback = "⚠️ Significant issues. Would lose 3-5 marks."
    elif result["score"] >= 40:
        feedback = "❌ Major errors. Would fail in exam."
    else:
        feedback = "❌❌ Completely incorrect. Study Delphi syntax."

    return {
        "score": result["score"],
        "feedback": feedback,
        "details": result["feedback"],
        "topics": result["detected_topics"],
    }


# Valid solution bank (for exact matching when needed)
SOLUTION_BANK = {
    "pos_find_x": ["Pos('x', stext)", "Pos('x', editbox1.text)"],
    "array_sum": ["sum := sum + arr[i]", "total := total + numbers[i]"],
    "file_read": ["ReadLn(myFile, line)", "ReadLn(textFile, data)"],
}


def is_valid_solution(user_code, question_type):
    """Check if code matches known valid solutions (off by 1-2 chars allowed)"""
    if question_type not in SOLUTION_BANK:
        return False, 0

    clean_user = re.sub(r"\s+", "", user_code).lower()
    best_match = 0

    for solution in SOLUTION_BANK[question_type]:
        clean_solution = re.sub(r"\s+", "", solution).lower()
        if clean_user == clean_solution:
            return True, 100

        # Off by a few characters?
        if abs(len(clean_user) - len(clean_solution)) <= 2:
            matches = sum(1 for a, b in zip(clean_user, clean_solution) if a == b)
            ratio = matches / max(len(clean_user), len(clean_solution))
            if ratio > 0.9:
                best_match = max(best_match, 85)

    return best_match >= 85, best_match


# Roasts for bad code
def get_roast(code, score):
    roasts = [
        f"Score: {score}%. This answer is your future: empty, desolate, and wrong.",
        f"Score: {score}%. The void accepts your code. The exam will not.",
        "Skill issue. Learn Delphi before the exam jagga's you.",
        f"Score: {score}%. Even a feature phone has more features than your code.",
        "Your code has 0 correct patterns. My disappointment has infinite.",
        "Compilation error. Not in Delphi — in your life choices.",
    ]
    import random

    return random.choice(roasts) if score < 50 else None
