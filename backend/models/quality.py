from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.orm import Session
import uuid
import json
from datetime import datetime, timezone

from core.base import Base
from models.assessment import Assessment
from models.grading_audit import GradingAudit


def gen_id() -> str:
    return str(uuid.uuid4())


# -----------------------------------------------------------------------------
# GRADING QUALITY SCORING FUNCTION
# -----------------------------------------------------------------------------
def compute_grading_quality_score(db: Session, course_id: str) -> float:
    """
    Computes grading consistency for a course based on assessment audits.

    Logic:
        - Fetch all assessments for course
        - For each, fetch latest 'distribution' audit
        - Extract std_dev from audit
        - Convert std_dev to a 0–1 score:
              score = 1 - (std / total_marks)
        - Lower std → more consistent grading → higher score
    """

    assessments = db.query(Assessment).filter_by(course_id=course_id).all()
    if not assessments:
        return 0.0

    scores = []

    for a in assessments:
        audit = (
            db.query(GradingAudit)
            .filter_by(assessment_id=a.id, metric="distribution")
            .order_by(GradingAudit.created_at.desc())
            .first()
        )

        if not audit:
            continue

        dist = json.loads(audit.value)
        std = dist.get("std", 0)

        # Avoid division by zero
        if a.total_marks and a.total_marks > 0:
            score = max(0.0, 1.0 - (std / a.total_marks))
        else:
            score = 0.0

        scores.append(score)

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


# -----------------------------------------------------------------------------
# QUALITY SCORE MODEL
# -----------------------------------------------------------------------------
class QualityScore(Base):
    __tablename__ = "quality_scores"

    id = Column(String, primary_key=True, default=gen_id)
    course_id = Column(String, nullable=False)  # UUID of the course

    overall_score = Column(Float)
    completeness_score = Column(Float)
    alignment_score = Column(Float)
    feedback_score = Column(Float)
    grading_score = Column(Float)  # ← you should store this too

    suggestions = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    generated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
