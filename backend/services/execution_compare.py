from collections import Counter
from typing import List, Tuple, Dict, Any
import re

from services.semantic_compare import semantic_coverage

# -------------------- STOPWORDS --------------------
STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "being", "that", "this",
    "these", "those", "as", "at", "by", "from", "it", "its", "into",
    "we", "you", "they", "their", "our", "your", "can", "may", "should",
    "will", "would", "about", "over", "under", "between", "within",
    "also", "etc"
}

# -------------------- Helpers --------------------

def _clean_text(val: str) -> str:
    if val is None:
        return ""
    if not isinstance(val, str):
        val = str(val)
    val = val.replace("\x00", " ")
    val = val.lower()
    val = re.sub(r"[^a-z0-9\s\-]", " ", val)
    val = re.sub(r"\s+", " ", val).strip()
    return val


def _extract_plan_terms(plan_text: str) -> List[str]:
    """
    Extract phrases from plan text that represent expected topics/terms.
    We keep phrases short and meaningful; de-duplicate.
    """
    t = _clean_text(plan_text)
    if not t:
        return []

    # split into phrase candidates
    parts = re.split(r"[;\n•\-\–\—\.]", t)
    candidates: List[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        candidates.append(p)

    # normalize candidates
    out: List[str] = []
    seen = set()

    for c in candidates:
        toks = [w for w in c.split() if w and w not in STOPWORDS]
        if not toks:
            continue

        # keep max 8-token phrase to avoid noise
        phrase = " ".join(toks[:8]).strip()

        # ignore too short
        if len(phrase) < 4:
            continue

        if phrase not in seen:
            seen.add(phrase)
            out.append(phrase)

    return out[:150]


def _lexical_compare(plan_text: str, delivered_text: str) -> Tuple[float, List[str], List[str]]:
    """
    Simple lexical coverage:
      - Extract plan phrases (plan_terms)
      - Count as "matched" if phrase appears OR >= 2/3 keywords appear
    Returns:
      coverage (0..1), missing_terms, plan_terms
    """
    plan_terms = _extract_plan_terms(plan_text)
    delivered = _clean_text(delivered_text)

    if not plan_terms:
        return 0.0, [], []

    missing: List[str] = []
    matched = 0

    for term in plan_terms:
        if term in delivered:
            matched += 1
            continue

        kws = [w for w in term.split() if w and w not in STOPWORDS]
        if len(kws) >= 3:
            present = sum(1 for w in kws if w in delivered)
            if present / len(kws) >= 0.67:
                matched += 1
                continue

        missing.append(term)

    coverage = matched / max(len(plan_terms), 1)
    return float(coverage), missing[:200], plan_terms


# -------------------- Your hybrid logic (unchanged) --------------------

def compare_week_hybrid(
    plan_text: str,
    delivered_text: str,
    lexical_weight: float = 0.35,
    semantic_weight: float = 0.65,
    semantic_threshold: float = 0.78,
) -> Dict[str, Any]:

    lex_cov, lex_missing, lex_terms = _lexical_compare(plan_text, delivered_text)

    sem = semantic_coverage(
        plan_text=plan_text,
        delivered_text=delivered_text,
        threshold=semantic_threshold,
    )

    sem_cov = float(sem.get("coverage") or 0.0)
    final = (lexical_weight * lex_cov) + (semantic_weight * sem_cov)

    return {
        "coverage_final": round(final, 4),
        "coverage_lexical": round(lex_cov, 4),
        "coverage_semantic": round(sem_cov, 4),
        "missing_terms": sem.get("missing") or lex_missing,
        "matched_terms": sem.get("matched") or [],
        "plan_terms": sem.get("audit", {}).get("plan_phrases") or lex_terms,
        "audit": {
            "lexical_weight": lexical_weight,
            "semantic_weight": semantic_weight,
            "semantic_threshold": semantic_threshold,
            "semantic": sem.get("audit"),
        },
    }


def compare_week(plan_text: str, delivered_text: str):
    """
    IMPORTANT:
    weekly_zip_upload_service expects exactly 3 return values:
      coverage_score, missing_terms, plan_terms
    """
    out = compare_week_hybrid(plan_text, delivered_text)
    return (
        out["coverage_final"],
        out["missing_terms"],
        out["plan_terms"],
    )
