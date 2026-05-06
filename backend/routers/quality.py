from core.rbac import require_roles
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import SessionLocal
from schemas.quality import QualityOut
from .auth import get_current_user
from services.quality_service import compute_quality_scores
from services.exception_service import log_exception
from models.quality import QualityScore
from models.course import Course
from datetime import datetime
import uuid
import json
from core.rbac import require_roles

router = APIRouter(prefix="/courses", tags=["Quality"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_quality_out(score: QualityScore) -> QualityOut:
    suggestions = json.loads(score.suggestions) if score.suggestions else []

    return QualityOut(
        course_id=score.course_id,
        overall_score=score.overall_score or 0,
        completeness_score=score.completeness_score or 0,
        alignment_score=score.alignment_score or 0,
        feedback_score=score.feedback_score or 0,
        grading_score=score.grading_score or 0,
        suggestions=suggestions,
    )


@router.get("/{course_id}/quality-score", response_model=QualityOut)
def get_quality_score(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec", "hod", "course_lead")),
):
    score = (
        db.query(QualityScore)
        .filter(QualityScore.course_id == course_id)
        .order_by(QualityScore.created_at.desc())
        .first()
    )

    if not score:
        raise HTTPException(status_code=404, detail="No quality score found for this course")

    return _to_quality_out(score)


@router.post("/{course_id}/recompute", response_model=QualityOut)
def recompute_quality(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec", "hod", "course_lead")),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    try:
        scores = compute_quality_scores(course_id=course_id, db=db)

    except Exception as e:
        log_exception(
            db=db,
            course_id=course_id,
            upload_id=None,
            module="quality",
            error_type="quality_computation_failed",
            message=str(e),
            severity="high",
        )

        raise HTTPException(
            status_code=500,
            detail="Quality computation failed. The issue has been logged for QEC review.",
        )

    try:
        new_score = QualityScore(
            id=str(uuid.uuid4()),
            course_id=course_id,
            overall_score=scores["overall_score"],
            completeness_score=scores["completeness_score"],
            alignment_score=scores["alignment_score"],
            feedback_score=scores["feedback_score"],
            grading_score=scores["grading_score"],
            suggestions=json.dumps(scores["suggestions"]),
            created_at=datetime.utcnow(),
            generated_at=datetime.utcnow(),
        )

        db.add(new_score)
        db.commit()
        db.refresh(new_score)

    except Exception as e:
        db.rollback()

        log_exception(
            db=db,
            course_id=course_id,
            upload_id=None,
            module="quality",
            error_type="quality_save_failed",
            message=str(e),
            severity="high",
        )

        raise HTTPException(
            status_code=500,
            detail="Quality score was computed but could not be saved.",
        )

    return QualityOut(
        course_id=new_score.course_id,
        overall_score=new_score.overall_score,
        completeness_score=new_score.completeness_score,
        alignment_score=new_score.alignment_score,
        feedback_score=new_score.feedback_score,
        grading_score=new_score.grading_score,
        suggestions=scores["suggestions"],
    )