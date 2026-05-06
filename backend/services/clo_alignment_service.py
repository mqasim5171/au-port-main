import math
import re
from typing import List, Dict, Any

from services.openrouter_embeddings import embed_texts


# ------------------------- helpers -------------------------

STOPWORDS = {
    "the","a","an","and","or","to","of","in","on","for","with","at","by","from","as",
    "is","are","was","were","be","been","it","this","that","these","those","we","you",
    "your","our","they","their","i","he","she","them","not","can","will","may","also",
    "course","assessment","quiz","assignment","exam","project","evaluation"
}

def _norm(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[-/]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _tokens(text: str):
    return [
        w for w in re.findall(r"[a-z0-9]{2,}", _norm(text))
        if w not in STOPWORDS and not w.isdigit()
    ]

def _cos(a, b) -> float:
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))

def _clean_items(items: List[str]) -> List[str]:
    out, seen = [], set()
    for x in items:
        t = x.strip()
        k = _norm(t)
        if not t or k in seen:
            continue
        seen.add(k)
        out.append(t)
    return out


# ------------------------- CORE ENGINE -------------------------

def run_clo_alignment(
    clos: List[str],
    assessments: List[Dict[str, str]],
    threshold: float = 0.65,
) -> Dict[str, Any]:

    clos = _clean_items(clos)
    assessment_names = _clean_items([a["name"] for a in assessments])

    if not clos or not assessment_names:
        return {
            "avg_top": 0.0,
            "flags": ["no_clos_or_assessments"],
            "pairs": [],
            "alignment": {},
            "clos": clos,
            "assessments": assessment_names,
            "audit": {"reason": "empty_input"},
        }

    # -------- embeddings --------
    clo_emb = embed_texts(clos)
    ass_emb = embed_texts(assessment_names)

    clo_vecs = clo_emb["vectors"]
    ass_vecs = ass_emb["vectors"]

    pairs = []
    alignment = {}
    top_scores = []

    for i, clo in enumerate(clos):
        best_score = -1.0
        best_j = -1

        for j, ass in enumerate(assessment_names):
            s = _cos(clo_vecs[i], ass_vecs[j])
            if s > best_score:
                best_score = s
                best_j = j

        best_ass = assessment_names[best_j] if best_j >= 0 else ""

        score = round(float(best_score), 4)
        passed = bool(score >= threshold)

        pairs.append({
            "clo": clo,
            "assessment": best_ass,
            "similarity": score,
        })

        # ✅ FIXED STRUCTURE (THIS IS THE KEY PART)
        alignment[clo] = {
            "best_assessment": {
                "question": best_ass,
                "score": score,
                "passed": passed,
            },
            "score": score,
            "passed": passed,
        }

        top_scores.append(score)

    avg_top = sum(top_scores) / max(1, len(top_scores))

    flags = []
    if avg_top < threshold:
        flags.append("low_overall_alignment")

    weak = [p for p in pairs if p["similarity"] < threshold]
    if weak:
        flags.append("weak_clo_mappings")

    audit = {
        "threshold": threshold,
        "avg_top_similarity": round(float(avg_top), 4),
        "total_clos": len(clos),
        "total_assessments": len(assessment_names),
        "weak_mappings": weak,
        "embedding_meta": {
            "clo": clo_emb.get("meta"),
            "assessments": ass_emb.get("meta"),
        },
    }

    return {
        "avg_top": round(float(avg_top), 4),
        "flags": flags,
        "pairs": pairs,
        "alignment": alignment,
        "clos": clos,
        "assessments": assessment_names,
        "audit": audit,
    }
