from services.semantic_compare import semantic_coverage

def run_grading_fairness(
    answers: list[dict],
    grades: list[int],
    threshold: float = 0.8,
):
    sims = []
    for i in range(len(answers)):
        for j in range(i + 1, len(answers)):
            sem = semantic_coverage(
                answers[i]["text"],
                answers[j]["text"],
                threshold=threshold,
            )
            sims.append({
                "i": i,
                "j": j,
                "similarity": sem["coverage"],
                "grade_diff": abs(grades[i] - grades[j]),
            })

    flagged = [x for x in sims if x["similarity"] >= threshold and x["grade_diff"] >= 20]

    fairness_score = max(0, 100 - (len(flagged) * 10))

    return {
        "fairness_score": fairness_score,
        "flagged_cases": flagged,
        "total_pairs": len(sims),
    }
