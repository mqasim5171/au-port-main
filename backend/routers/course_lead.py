# backend/routers/course_lead.py

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from core.rbac import require_roles
from models.user import User
from models.course import Course
from models.course_staff import CourseStaff
from models.course_execution import WeeklyPlan

from routers.auth import get_current_user

from services.course_guide_service import (
    save_upload,
    extract_text_best_effort,
    ensure_weekly_plans,
    set_course_guide_metadata,
)

router = APIRouter(prefix="/course-lead", tags=["Course Lead"])

COURSE_LEAD_DEP = require_roles("course_lead", "admin")


def _role_value(user: User) -> str:
    return str(getattr(user, "role", "") or "").lower()


def _ensure_course_lead_access(db: Session, course_id: str, user: User):
    role = _role_value(user)

    if "admin" in role:
        return

    row = (
        db.query(CourseStaff)
        .filter(
            CourseStaff.course_id == course_id,
            CourseStaff.user_id == user.id,
            CourseStaff.role == "COURSE_LEAD",
        )
        .first()
    )

    if not row:
        raise HTTPException(403, "Not assigned as Course Lead for this course")


@router.get("/my-courses")
def my_courses(
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    role = _role_value(me)

    if "admin" in role:
        return db.query(Course).order_by(Course.course_code.asc()).all()

    course_ids = [
        x.course_id
        for x in db.query(CourseStaff)
        .filter(
            CourseStaff.user_id == me.id,
            CourseStaff.role == "COURSE_LEAD",
        )
        .all()
    ]

    if not course_ids:
        return []

    return (
        db.query(Course)
        .filter(Course.id.in_(course_ids))
        .order_by(Course.course_code.asc())
        .all()
    )


@router.post("/courses/{course_id}/course-guide/upload")
def upload_course_guide(
    course_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(404, "Course not found")

    _ensure_course_lead_access(db, course_id, me)

    filename = file.filename or ""

    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX course guide files are allowed.",
        )

    saved_path = save_upload(course_id, file)
    text = extract_text_best_effort(saved_path)

    if not text.strip():
        # Do not silently create useless weekly plans.
        # Tell frontend clearly that extraction failed.
        raise HTTPException(
            status_code=400,
            detail=(
                "No text could be extracted from this file. "
                "Please upload a text-based PDF/DOCX or check backend PDF parser dependencies."
            ),
        )

    ensure_weekly_plans(db, course_id, text, saved_path)

    set_course_guide_metadata(
        db=db,
        course=course,
        file_path=saved_path,
        extracted_text=text,
    )

    return {
        "ok": True,
        "path": saved_path,
        "text_len": len(text),
        "weeks_created": 16,
        "message": "Course guide uploaded and weekly plan generated successfully.",
    }


@router.get("/courses/{course_id}/weekly-plans")
def get_weekly_plans(
    course_id: str,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(404, "Course not found")

    _ensure_course_lead_access(db, course_id, me)

    plans = (
        db.query(WeeklyPlan)
        .filter(WeeklyPlan.course_id == course_id)
        .order_by(WeeklyPlan.week_number.asc())
        .all()
    )

    return plans