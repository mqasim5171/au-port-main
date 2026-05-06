from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import statistics, json, uuid

from core.db import get_db
from routers.auth import get_current_user

from models.assessment import Assessment, AssessmentCLOAlignment
from models.student_submission import StudentSubmission
from models.grading_audit import GradingAudit
from services.assessment_service import ai_extract_questions

router = APIRouter(tags=["Grading Audit"])

@router.post("/assessments/{assessment_id}/run-grading-audit")
def run_grading_audit(assessment_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        aid = uuid.UUID(assessment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid assessment_id")

    assessment = db.get(Assessment, aid)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    subs = (
        db.query(StudentSubmission)
        .filter(StudentSubmission.assessment_id == aid, StudentSubmission.obtained_marks.isnot(None))
        .all()
    )
    if not subs:
        raise HTTPException(status_code=400, detail="No graded submissions to audit")

    marks = [int(s.obtained_marks) for s in subs if s.obtained_marks is not None]
    mean_val = statistics.mean(marks)
    median_val = statistics.median(marks)
    std_val = statistics.pstdev(marks) if len(marks) > 1 else 0.0

    lower = mean_val - 2 * std_val
    upper = mean_val + 2 * std_val
    outliers = [m for m in marks if m < lower or m > upper]

    # Per-question stats from evidence_json["parsed"]["per_question"]
    per_q = {}
    for s in subs:
        parsed = (s.evidence_json or {}).get("parsed") or {}
        for row in (parsed.get("per_question") or []):
            qno = int(row.get("question_no") or 0)
            got = float(row.get("marks_awarded") or 0.0)
            if qno <= 0:
                continue
            per_q.setdefault(qno, []).append(got)

    per_question_stats = {
        str(qno): {
            "avg": round(statistics.mean(vals), 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "count": len(vals),
        }
        for qno, vals in sorted(per_q.items())
    }

    # CLO achievement: use AssessmentCLOAlignment.per_question (question_no -> clo)
    align = db.query(AssessmentCLOAlignment).filter(AssessmentCLOAlignment.assessment_id == aid).first()
    q_to_clo = {}
    if align and align.per_question:
        for row in (align.per_question or []):
            qno = int(row.get("question_no") or 0)
            clo = str(row.get("clo") or row.get("clo_code") or "").strip()
            if qno > 0 and clo:
                q_to_clo[qno] = clo

    # Get question max marks (best effort: re-extract questions from latest file)
    qpack = ai_extract_questions(db, assessment)
    q_json = qpack.get("questions_json") or {}
    q_max = {}
    for q in (q_json.get("questions") or []):
        try:
            qno = int(q.get("question_no"))
            qmax = float(q.get("marks") or 0)
            q_max[qno] = qmax
        except Exception:
            pass

    clo_sum = {}
    clo_max = {}
    for s in subs:
        parsed = (s.evidence_json or {}).get("parsed") or {}
        for row in (parsed.get("per_question") or []):
            qno = int(row.get("question_no") or 0)
            got = float(row.get("marks_awarded") or 0.0)
            clo = q_to_clo.get(qno)
            if not clo:
                continue
            clo_sum[clo] = clo_sum.get(clo, 0.0) + got
            clo_max[clo] = clo_max.get(clo, 0.0) + float(q_max.get(qno, 0.0))

    clo_achievement = {}
    for clo, total_got in clo_sum.items():
        total_max = clo_max.get(clo, 0.0) or 0.0
        clo_achievement[clo] = round((total_got / total_max) * 100.0, 2) if total_max else 0.0

    def store(metric: str, value_obj):
        db.add(GradingAudit(
            assessment_id=aid,
            metric=metric,
            value=json.dumps(value_obj),
        ))

    store("distribution", {"marks": marks, "mean": mean_val, "median": median_val, "std": std_val, "max_marks": assessment.max_marks})
    store("outliers", {"count": len(outliers), "values": outliers, "lower": lower, "upper": upper})
    store("per_question", per_question_stats)
    store("clo_achievement", clo_achievement)

    db.commit()
    return {"status": "ok", "saved_metrics": ["distribution","outliers","per_question","clo_achievement"]}

@router.get("/assessments/{assessment_id}/grading-audit")
def get_grading_audit(assessment_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        aid = uuid.UUID(assessment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid assessment_id")

    rows = (
        db.query(GradingAudit)
        .filter(GradingAudit.assessment_id == aid)
        .order_by(GradingAudit.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "metric": r.metric,
            "value": json.loads(r.value),
            "notes": r.notes,
            "created_at": r.created_at,
        }
        for r in rows
    ]
