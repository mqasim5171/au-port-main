from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.db import SessionLocal
from core.rbac import require_roles
from models.course import Course
from models.quality import QualityScore
from models.uploads import Upload
from models.completeness import CompletenessRun


router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def latest_quality_for_course(db: Session, course_id: str):
    return (
        db.query(QualityScore)
        .filter(QualityScore.course_id == course_id)
        .order_by(QualityScore.created_at.desc())
        .first()
    )


def latest_completeness_for_course(db: Session, course_id: str):
    return (
        db.query(CompletenessRun)
        .filter(CompletenessRun.course_id == course_id)
        .order_by(CompletenessRun.created_at.desc())
        .first()
    )


@router.get("/overview")
def analytics_overview(
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec", "hod", "course_lead")),
):
    courses = db.query(Course).all()

    course_rows = []
    department_map = {}

    total_quality = 0
    scored_courses = 0
    at_risk = 0

    for course in courses:
        quality = latest_quality_for_course(db, course.id)
        completeness = latest_completeness_for_course(db, course.id)
        uploads_count = db.query(Upload).filter(Upload.course_id == course.id).count()

        overall = float(quality.overall_score or 0) if quality else 0
        completeness_score = (
            float(completeness.result_json.get("score_percent") or 0)
            if completeness and completeness.result_json
            else 0
        )

        if quality:
            total_quality += overall
            scored_courses += 1

        risk_level = "low"
        if overall < 50 or completeness_score < 50:
            risk_level = "critical"
            at_risk += 1
        elif overall < 70 or completeness_score < 80:
            risk_level = "medium"
            at_risk += 1

        row = {
            "course_id": course.id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "department": course.department,
            "semester": course.semester,
            "year": course.year,
            "overall_score": round(overall, 2),
            "completeness_score": round(completeness_score, 2),
            "alignment_score": round(float(quality.alignment_score or 0), 2) if quality else 0,
            "feedback_score": round(float(quality.feedback_score or 0), 2) if quality else 0,
            "grading_score": round(float(quality.grading_score or 0), 2) if quality else 0,
            "uploads_count": uploads_count,
            "risk_level": risk_level,
        }

        course_rows.append(row)

        dept = course.department or "Unknown"
        department_map.setdefault(dept, {"department": dept, "courses": 0, "quality_sum": 0, "at_risk": 0})
        department_map[dept]["courses"] += 1
        department_map[dept]["quality_sum"] += overall
        if risk_level in {"critical", "medium"}:
            department_map[dept]["at_risk"] += 1

    departments = []
    for dept in department_map.values():
        avg = dept["quality_sum"] / dept["courses"] if dept["courses"] else 0
        departments.append({
            "department": dept["department"],
            "courses": dept["courses"],
            "average_quality": round(avg, 2),
            "at_risk": dept["at_risk"],
        })

    course_rows.sort(key=lambda x: x["overall_score"])
    departments.sort(key=lambda x: x["average_quality"])

    return {
        "total_courses": len(courses),
        "scored_courses": scored_courses,
        "average_quality": round(total_quality / scored_courses, 2) if scored_courses else 0,
        "at_risk_courses": at_risk,
        "courses": course_rows,
        "departments": departments,
    }