import math
import re
from typing import List, Dict, Any

from services.openrouter_embeddings import embed_texts

STOPWORDS = {
    "the","a","an","and","or","to","of","in","on","for","with","at","by","from","as",
    "is","are","was","were","be","been","it","this","that","these","those","we","you",
    "your","our","they","their","i","he","she","them","not","can","will","may","also",
    "into","about","over","under","between","within","during","after","before",
    "department","faculty","university","islamabad","air","course","guide","schedule","week",
    "chapter","topics","covered","plan","lecture","lectures"
}

def _norm(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[-/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _nontrivial_line(line: str) -> bool:
    t = _norm(line)
    if len(t) < 6:
        return False
    toks = re.findall(r"[a-z0-9]{2,}", t)
    toks = [x for x in toks if x not in STOPWORDS and not x.isdigit()]
    return len(toks) >= 2

def extract_plan_phrases(plan_text: str, max_phrases: int = 30) -> List[str]:
    lines = [x.strip("•*- \t\r\n") for x in (plan_text or "").splitlines()]
    lines = [x for x in lines if _nontrivial_line(x)]

    if not lines:
        s = _norm(plan_text or "")
        parts = re.split(r"[.;:\n]+", s)
        parts = [p for p in parts if _nontrivial_line(p)]
        lines = parts

    seen, out = set(), []
    for x in lines:
        k = _norm(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x.strip())
        if len(out) >= max_phrases:
            break
    return out

def extract_delivered_chunks(delivered_text: str, max_chunks: int = 60, chunk_chars: int = 800) -> List[str]:
    t = (delivered_text or "").strip()
    t = re.sub(r"\n{3,}", "\n\n", t)
    paras = [p.strip() for p in t.split("\n\n") if p.strip()]

    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) + 2 <= chunk_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = p
        if len(chunks) >= max_chunks:
            break

    if buf and len(chunks) < max_chunks:
        chunks.append(buf)

    if not chunks and t:
        for i in range(0, min(len(t), max_chunks * chunk_chars), chunk_chars):
            chunks.append(t[i:i+chunk_chars])

    return chunks[:max_chunks]

def _cos(a: List[float], b: List[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a)
    nb = sum(y*y for y in b)
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))

def semantic_coverage(
    plan_text: str,
    delivered_text: str,
    threshold: float = 0.78,
    max_plan_phrases: int = 30,
    max_chunks: int = 60,
) -> Dict[str, Any]:
    plan_phrases = extract_plan_phrases(plan_text, max_plan_phrases)
    delivered_chunks = extract_delivered_chunks(delivered_text, max_chunks)

    if not plan_phrases:
        return {"coverage": 0.0, "matched": [], "missing": [], "audit": {"reason": "no_plan_phrases"}}

    if not delivered_chunks:
        return {"coverage": 0.0, "matched": [], "missing": plan_phrases, "audit": {"reason": "no_delivered_chunks"}}

    plan_emb = embed_texts(plan_phrases)
    chunk_emb = embed_texts(delivered_chunks)

    pv, cv = plan_emb["vectors"], chunk_emb["vectors"]

    matched, missing, top_scores = [], [], []

    for i, phrase in enumerate(plan_phrases):
        best, best_j = -1.0, -1
        for j in range(len(delivered_chunks)):
            s = _cos(pv[i], cv[j])
            if s > best:
                best, best_j = s, j

        top_scores.append({
            "phrase": phrase,
            "best_score": round(float(best), 4),
            "best_chunk_index": best_j,
        })

        (matched if best >= threshold else missing).append(phrase)

    coverage = len(matched) / max(1, len(plan_phrases))

    return {
        "coverage": float(coverage),
        "matched": matched,
        "missing": missing,
        "audit": {
            "threshold": threshold,
            "plan_phrases": plan_phrases,
            "delivered_chunks_count": len(delivered_chunks),
            "top_scores": top_scores,
            "embed_meta": {
                "plan": plan_emb.get("meta"),
                "delivered": chunk_emb.get("meta"),
            },
        },
    }
