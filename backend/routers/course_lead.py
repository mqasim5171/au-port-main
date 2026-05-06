from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from models.user import User
from models.course import Course
from models.course_staff import CourseStaff
from models.course_execution import WeeklyPlan

from routers.auth import get_current_user

from services.course_guide_service import (
    save_upload,
    extract_text_best_effort,
    ensure_weekly_plans,
)

router = APIRouter(prefix="/course-lead", tags=["Course Lead"])


def _role(user: User) -> str:
    raw = (getattr(user, "role", "") or "").strip().lower()

    aliases = {
        "course lead": "course_lead",
        "faculty member": "faculty",
        "instructor": "faculty",
        "administrator": "admin",
        "superadmin": "admin",
    }

    return aliases.get(raw, raw)


def _ensure_course_lead_role(user: User):
    if _role(user) != "course_lead":
        raise HTTPException(
            status_code=403,
            detail="Only Course Lead can access this section.",
        )


def _ensure_course_exists(db: Session, course_id: str) -> Course:
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return course


def _ensure_course_lead_access(db: Session, course_id: str, user: User):
    """
    Strict access:
    - Admin is NOT allowed here.
    - QEC/HOD are NOT allowed here.
    - Only user assigned as COURSE_LEAD for this course can upload/view guide.
    """
    _ensure_course_lead_role(user)
    _ensure_course_exists(db, course_id)

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
        raise HTTPException(
            status_code=403,
            detail="Not assigned as Course Lead for this course.",
        )


@router.get("/my-courses")
def my_courses(
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """
    Returns only courses where the logged-in user is assigned as COURSE_LEAD.
    Admin intentionally does not receive all courses here because this module
    is for academic course guide work, not administrative control.
    """
    _ensure_course_lead_role(me)

    course_ids = [
        x.course_id
        for x in (
            db.query(CourseStaff)
            .filter(
                CourseStaff.user_id == me.id,
                CourseStaff.role == "COURSE_LEAD",
            )
            .all()
        )
    ]

    if not course_ids:
        return []

    return (
        db.query(Course)
        .filter(Course.id.in_(course_ids))
        .order_by(Course.course_code.asc())
        .all()
    )


@router.get("/courses/{course_id}/course-guide/status")
def course_guide_status(
    course_id: str,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    _ensure_course_lead_access(db, course_id, me)

    course = db.get(Course, course_id)

    plans_count = (
        db.query(WeeklyPlan)
        .filter(WeeklyPlan.course_id == course_id)
        .count()
    )

    course_guide_path = ""
    course_guide_text = ""

    if hasattr(course, "course_guide_path"):
        course_guide_path = course.course_guide_path or ""

    if hasattr(course, "course_guide_text"):
        course_guide_text = course.course_guide_text or ""

    return {
        "course_id": course_id,
        "course_code": course.course_code,
        "course_name": course.course_name,
        "course_guide_path": course_guide_path,
        "text_length": len(course_guide_text or ""),
        "weekly_plan_count": plans_count,
    }


@router.post("/courses/{course_id}/course-guide/upload")
def upload_course_guide(
    course_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    course = _ensure_course_exists(db, course_id)
    _ensure_course_lead_access(db, course_id, me)

    filename = file.filename or ""

    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX course guide files are allowed.",
        )

    saved_path = save_upload(course_id, file)
    text = extract_text_best_effort(saved_path) or ""

    ensure_weekly_plans(
        db,
        course_id,
        text or "(No text extracted — upload a text-based PDF/DOCX)",
    )

    if hasattr(course, "course_guide_path"):
        course.course_guide_path = saved_path

    if hasattr(course, "course_guide_text"):
        course.course_guide_text = text[:20000]

    db.commit()

    return {
        "ok": True,
        "message": "Course guide uploaded and weekly plans generated.",
        "path": saved_path,
        "text_len": len(text),
        "weeks_created": 16,
    }


@router.get("/courses/{course_id}/weekly-plans")
def get_weekly_plans(
    course_id: str,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    _ensure_course_lead_access(db, course_id, me)

    plans = (
        db.query(WeeklyPlan)
        .filter(WeeklyPlan.course_id == course_id)
        .order_by(WeeklyPlan.week_number.asc())
        .all()
    )

    return plans