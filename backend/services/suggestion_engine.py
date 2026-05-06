# backend/services/suggestion_engine.py

from sqlalchemy.orm import Session
from typing import List

from models.course_execution import WeeklyExecution
from models.student_feedback import StudentFeedback

# Optional (safe)
try:
    from models.assessment import Assessment, AssessmentCLOAlignment
except Exception:
    Assessment = None
    AssessmentCLOAlignment = None


def generate_suggestions(db: Session, course_id: str, course_name: str) -> List[str]:
    """
    Generate AI-driven suggestions using:
    - Weekly execution (course_id)
    - CLO alignment (course_id)
    - Student survey feedback (course_name)
    """

    suggestions: List[str] = []

    # ---------------------------------------------------
    # 1. Weekly execution gaps
    # ---------------------------------------------------
    weak_weeks = (
        db.query(WeeklyExecution)
        .filter(
            WeeklyExecution.course_id == course_id,
            WeeklyExecution.coverage_percent < 80
        )
        .all()
    )

    for w in weak_weeks:
        suggestions.append(
            f"Week {w.week_number} covered only {int(w.coverage_percent)}% of planned content."
        )

    # ---------------------------------------------------
    # 2. CLO alignment weaknesses
    # ---------------------------------------------------
    if AssessmentCLOAlignment and Assessment:
        weak = (
            db.query(AssessmentCLOAlignment)
            .join(Assessment, Assessment.id == AssessmentCLOAlignment.assessment_id)
            .filter(
                Assessment.course_id == course_id,
                AssessmentCLOAlignment.coverage_percent < 70
            )
            .count()
        )

        if weak > 0:
            suggestions.append(
                "Some assessments show weak CLO alignment. Review CLO mapping and question design."
            )

    # ---------------------------------------------------
    # 3. Student survey feedback (NO JOIN, CORRECT)
    # ---------------------------------------------------
    negative_feedback = (
        db.query(StudentFeedback)
        .filter(
            StudentFeedback.course_name.ilike(f"%{course_name}%"),
            StudentFeedback.sentiment == "negative"
        )
        .count()
    )

    if negative_feedback >= 3:
        suggestions.append(
            "Multiple students expressed negative feedback. Review teaching clarity, pacing, and engagement."
        )

    # ---------------------------------------------------
    # 4. Fallback (always return something)
    # ---------------------------------------------------
    if not suggestions:
        suggestions.append(
            "No major quality issues detected. Continue monitoring execution, assessments, and student feedback."
        )

    return suggestions
