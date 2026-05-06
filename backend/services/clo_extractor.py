# services/clo_extractor.py
import re
from typing import List, Tuple


# -------------------- QUESTION DETECTION --------------------

QUESTION_PATTERNS = [
    r"^q\s*\d+\s*[:\.\)]",          # Q1:, Q2. , Q3)
    r"^question\s*\d+",             # Question 1
    r"^\d+\s*[:\.\)]",              # 1:, 2.
    r"^[a-z]\s*[:\.\)]",            # a), b)
]


def _is_question_header(line: str) -> bool:
    l = line.lower().strip()
    for pat in QUESTION_PATTERNS:
        if re.match(pat, l):
            return True
    return False


# -------------------- MAIN EXTRACTOR --------------------

def extract_clos_and_assessments(text: str) -> Tuple[List[str], List[str]]:
    """
    Extract:
      - CLO lines (if present)
      - Assessment questions (Q1, Question 1, 1., a), etc.)

    Returns: (clos, assessments)
    """

    if not text:
        return [], []

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # -------- CLO extraction (unchanged logic, safer) --------
    clos: List[str] = []
    for line in lines:
        if re.match(r"(?i)\bclo\s*\d+", line):
            clos.append(line.strip())

    # -------- Assessment extraction (FIXED) --------
    assessments: List[str] = []
    current: List[str] = []

    for line in lines:
        if _is_question_header(line):
            if current:
                assessments.append(" ".join(current))
                current = []
            current.append(line)
        else:
            if current:
                current.append(line)

    if current:
        assessments.append(" ".join(current))

    return clos, assessments
