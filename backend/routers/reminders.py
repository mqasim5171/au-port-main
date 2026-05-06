from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from core.db import SessionLocal
from routers.auth import get_current_user
from core.rbac import require_roles
from models.course import Course
from models.uploads import Upload
from models.completeness import CompletenessRun
from models.quality import QualityScore


router = APIRouter(prefix="/reminders", tags=["Reminders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _latest_completeness(db: Session, course_id: str):
    return (
        db.query(CompletenessRun)
        .filter(CompletenessRun.course_id == course_id)
        .order_by(CompletenessRun.created_at.desc())
        .first()
    )


def _latest_quality(db: Session, course_id: str):
    return (
        db.query(QualityScore)
        .filter(QualityScore.course_id == course_id)
        .order_by(QualityScore.created_at.desc())
        .first()
    )


@router.get("/overview")
def reminders_overview(
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec", "hod")),
):
    now = datetime.now(timezone.utc)
    courses = db.query(Course).all()

    reminders = []
    escalations = []

    for course in courses:
        course_id = course.id

        uploads = (
            db.query(Upload)
            .filter(Upload.course_id == course_id)
            .order_by(Upload.created_at.desc())
            .all()
        )

        latest_upload = uploads[0] if uploads else None
        latest_completeness = _latest_completeness(db, course_id)
        latest_quality = _latest_quality(db, course_id)

        course_label = f"{course.course_code} - {course.course_name}"

        # Case 1: No upload at all
        if not latest_upload:
            reminders.append({
                "course_id": course_id,
                "course": course_label,
                "type": "missing_upload",
                "severity": "high",
                "message": "No course folder has been uploaded yet.",
                "action": "Faculty should upload the course folder for QA review.",
            })
            escalations.append({
                "course_id": course_id,
                "course": course_label,
                "type": "no_upload_escalation",
                "severity": "critical",
                "message": "Course has no uploaded QA evidence.",
                "action": "QEC or HOD should follow up with the assigned instructor.",
            })
            continue

        # Case 2: Upload is old
        created_at = latest_upload.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        if created_at and created_at < now - timedelta(days=14):
            reminders.append({
                "course_id": course_id,
                "course": course_label,
                "type": "stale_upload",
                "severity": "medium",
                "message": "Latest course upload is older than 14 days.",
                "action": "Faculty should upload the latest course evidence.",
            })

        # Case 3: Completeness missing or weak
        if not latest_completeness:
            reminders.append({
                "course_id": course_id,
                "course": course_label,
                "type": "completeness_not_checked",
                "severity": "medium",
                "message": "Completeness check has not been generated.",
                "action": "Run folder completeness check.",
            })
        else:
            result = latest_completeness.result_json or {}
            score = float(result.get("score_percent") or 0)

            if score < 50:
                escalations.append({
                    "course_id": course_id,
                    "course": course_label,
                    "type": "low_completeness",
                    "severity": "critical",
                    "message": f"Folder completeness is very low at {score}%.",
                    "action": "QEC should review missing folder components immediately.",
                })
            elif score < 80:
                reminders.append({
                    "course_id": course_id,
                    "course": course_label,
                    "type": "incomplete_folder",
                    "severity": "high",
                    "message": f"Folder completeness is {score}%.",
                    "action": "Faculty should upload missing required artifacts.",
                })

        # Case 4: Quality score missing or low
        if not latest_quality:
            reminders.append({
                "course_id": course_id,
                "course": course_label,
                "type": "quality_not_computed",
                "severity": "medium",
                "message": "Quality score has not been computed yet.",
                "action": "Run quality score recomputation.",
            })
        else:
            overall = float(latest_quality.overall_score or 0)

            if overall < 50:
                escalations.append({
                    "course_id": course_id,
                    "course": course_label,
                    "type": "low_quality_score",
                    "severity": "critical",
                    "message": f"Overall quality score is critically low at {overall}%.",
                    "action": "HOD/QEC should review this course.",
                })
            elif overall < 70:
                reminders.append({
                    "course_id": course_id,
                    "course": course_label,
                    "type": "weak_quality_score",
                    "severity": "high",
                    "message": f"Overall quality score is below target at {overall}%.",
                    "action": "Faculty should review suggestions and improve course evidence.",
                })

    return {
        "generated_at": now.isoformat(),
        "total_reminders": len(reminders),
        "total_escalations": len(escalations),
        "reminders": reminders,
        "escalations": escalations,
    }