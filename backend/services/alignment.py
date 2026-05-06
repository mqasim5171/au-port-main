# services/alignment.py
from typing import List, Dict
from sentence_transformers import SentenceTransformer, util
import numpy as np

# Load once (will download model on first run)
_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def align_clos_to_assessments(clos: List[str], assessments: List[Dict[str, str]]) -> Dict:
    """
    clos: list[str]
    assessments: list[{"name": str}]
    Returns a dict with avg_top, flags, pairs, clos, assessments, alignment
    """
    ass_names = [a["name"] for a in assessments]

    if not clos or not ass_names:
        # return empty-ish shape
        return {
            "avg_top": 0.0,
            "flags": [],
            "pairs": [],
            "clos": clos,
            "assessments": assessments,
            "alignment": {}
        }

    # embeddings
    clo_emb = _MODEL.encode(clos, convert_to_tensor=True)
    ass_emb = _MODEL.encode(ass_names, convert_to_tensor=True)

    pairs = []
    top_scores = []

    # compute cosine similarity matrix
    sim_matrix = util.cos_sim(clo_emb, ass_emb).cpu().numpy()  # shape (len(clos), len(assessments))

    for i, clo in enumerate(clos):
        sims = sim_matrix[i]
        best_idx = int(sims.argmax())
        best_score = float(sims[best_idx])
        top_scores.append(best_score)
        pairs.append({
            "clo": clo,
            "assessment": ass_names[best_idx],
            "similarity": best_score
        })

    avg_top = float(np.mean(top_scores)) if top_scores else 0.0

    alignment = {
        p["clo"]: {"best_assessment": p["assessment"], "similarity": p["similarity"]}
        for p in pairs
    }

    return {
        "avg_top": avg_top,
        "flags": [],
        "pairs": [p for p in pairs],
        "clos": clos,
        "assessments": assessments,
        "alignment": alignment
    }
