# backend/routers/admin.py

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.security import hash_password
from core.db import get_db
from core.rbac import require_roles

from schemas.user import UserOut
from schemas.admin import (
    AdminCreateUserIn,
    AdminUpdateUserIn,
    AdminCourseCreate,
    AdminUpdateCourseIn,
    AssignStaffIn,
    SetClosIn,
    UserMiniOut,
)

from models.user import User
from models.course import Course
from models.course_staff import CourseStaff


router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN_DEP = require_roles("admin", "administrator", "superadmin")


# ======================================================
# USERS
# ======================================================

@router.get("/users", response_model=list[UserMiniOut])
def list_users(
    role: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    q = db.query(User)

    if role:
        q = q.filter(User.role.ilike(role))

    return q.order_by(User.full_name.asc()).limit(500).all()


@router.post("/users", response_model=UserOut, status_code=201)
def admin_create_user(
    payload: AdminCreateUserIn,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    role = (payload.role or "").strip().lower()

    if role not in {"instructor", "course_lead"}:
        raise HTTPException(
            status_code=400,
            detail="role must be instructor or course_lead",
        )

    existing = (
        db.query(User)
        .filter((User.email == payload.email) | (User.username == payload.username))
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email/username already registered",
        )

    user = User(
        username=payload.username.strip(),
        email=payload.email.strip(),
        full_name=payload.full_name.strip(),
        role=role,
        department=payload.department,
        password_hash=hash_password(payload.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.put("/users/{user_id}", status_code=200)
def admin_update_user(
    user_id: str,
    payload: AdminUpdateUserIn,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    u = db.get(User, user_id)

    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if (u.role or "").lower() in {"admin", "administrator", "superadmin"}:
        raise HTTPException(
            status_code=400,
            detail="Admin accounts cannot be edited here",
        )

    if payload.username and payload.username.strip() != u.username:
        exists = (
            db.query(User)
            .filter(User.username == payload.username.strip())
            .first()
        )

        if exists:
            raise HTTPException(status_code=400, detail="Username already in use")

        u.username = payload.username.strip()

    if payload.email and payload.email.strip().lower() != (u.email or "").lower():
        exists = (
            db.query(User)
            .filter(User.email == payload.email.strip())
            .first()
        )

        if exists:
            raise HTTPException(status_code=400, detail="Email already in use")

        u.email = payload.email.strip()

    if payload.full_name is not None:
        u.full_name = payload.full_name.strip()

    if payload.department is not None:
        u.department = payload.department

    if payload.password:
        if len(payload.password) < 8:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters",
            )
        u.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(u)

    return {
        "ok": True,
        "message": "User updated successfully",
        "user": {
            "id": u.id,
            "full_name": u.full_name,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "department": u.department,
        },
    }


@router.delete("/users/{user_id}", status_code=200)
def admin_delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    u = db.get(User, user_id)

    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if (u.role or "").lower() in {"admin", "administrator", "superadmin"}:
        raise HTTPException(
            status_code=400,
            detail="Admin accounts cannot be deleted here",
        )

    db.query(CourseStaff).filter(CourseStaff.user_id == user_id).delete(
        synchronize_session=False
    )

    db.delete(u)
    db.commit()

    return {
        "ok": True,
        "message": "User deleted successfully",
    }


# ======================================================
# COURSES
# ======================================================

@router.post("/courses", status_code=status.HTTP_201_CREATED)
def admin_create_course(
    payload: AdminCourseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    existing = (
        db.query(Course)
        .filter(
            Course.course_code == payload.course_code,
            Course.semester == payload.semester,
            Course.year == payload.year,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Course with same code, semester, and year already exists",
        )

    c = Course(
        course_code=payload.course_code.strip(),
        course_name=payload.course_name.strip(),
        semester=payload.semester.strip(),
        year=payload.year.strip(),
        instructor=payload.instructor or "",
        department=payload.department.strip(),
        clos=payload.clos or "[]",
    )

    db.add(c)
    db.commit()
    db.refresh(c)

    return c


@router.put("/courses/{course_id}", status_code=200)
def admin_update_course(
    course_id: str,
    payload: AdminUpdateCourseIn,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    c = db.get(Course, course_id)

    if not c:
        raise HTTPException(status_code=404, detail="Course not found")

    if payload.course_code is not None:
        c.course_code = payload.course_code.strip()

    if payload.course_name is not None:
        c.course_name = payload.course_name.strip()

    if payload.semester is not None:
        c.semester = payload.semester.strip()

    if payload.year is not None:
        c.year = payload.year.strip()

    if payload.department is not None:
        c.department = payload.department.strip()

    if payload.instructor is not None:
        c.instructor = payload.instructor.strip()

    if payload.clos is not None:
        c.clos = payload.clos

    db.commit()
    db.refresh(c)

    return {
        "ok": True,
        "message": "Course updated successfully",
        "course": {
            "id": c.id,
            "course_code": c.course_code,
            "course_name": c.course_name,
            "semester": c.semester,
            "year": c.year,
            "department": c.department,
            "instructor": c.instructor,
            "clos": c.clos,
        },
    }


@router.delete("/courses/{course_id}", status_code=200)
def admin_delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    c = db.get(Course, course_id)

    if not c:
        raise HTTPException(status_code=404, detail="Course not found")

    db.query(CourseStaff).filter(CourseStaff.course_id == course_id).delete(
        synchronize_session=False
    )

    db.delete(c)
    db.commit()

    return {
        "ok": True,
        "message": "Course deleted successfully",
    }


# ======================================================
# COURSE STAFF
# ======================================================

@router.get("/courses/{course_id}/staff")
def get_course_staff(
    course_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="Course not found")

    rows = (
        db.query(CourseStaff, User)
        .join(User, User.id == CourseStaff.user_id)
        .filter(CourseStaff.course_id == course_id)
        .order_by(CourseStaff.role.asc())
        .all()
    )

    return [
        {
            "id": cs.id,
            "role": cs.role,
            "user": {
                "id": u.id,
                "full_name": u.full_name,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "department": u.department,
            },
            "assigned_at": cs.assigned_at,
        }
        for cs, u in rows
    ]


@router.post("/courses/{course_id}/assign", status_code=200)
def assign_course_staff(
    course_id: str,
    payload: AssignStaffIn,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    user = db.get(User, payload.user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = (payload.role or "").upper().strip()

    if role not in {"INSTRUCTOR", "COURSE_LEAD"}:
        raise HTTPException(
            status_code=400,
            detail="role must be INSTRUCTOR or COURSE_LEAD",
        )

    if role == "COURSE_LEAD":
        db.query(CourseStaff).filter(
            CourseStaff.course_id == course_id,
            CourseStaff.role == "COURSE_LEAD",
        ).delete(synchronize_session=False)

    exists = (
        db.query(CourseStaff)
        .filter(
            CourseStaff.course_id == course_id,
            CourseStaff.user_id == user.id,
            CourseStaff.role == role,
        )
        .first()
    )

    if not exists:
        cs = CourseStaff(
            course_id=course_id,
            user_id=user.id,
            role=role,
            assigned_by=admin.id,
        )
        db.add(cs)

    if role == "INSTRUCTOR":
        course.instructor = user.full_name or user.username

    db.commit()

    return {"ok": True, "message": "Staff assigned successfully"}


@router.delete("/courses/{course_id}/staff/{staff_id}", status_code=200)
def admin_remove_course_staff(
    course_id: str,
    staff_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    row = db.get(CourseStaff, staff_id)

    if not row or row.course_id != course_id:
        raise HTTPException(
            status_code=404,
            detail="Course staff assignment not found",
        )

    db.delete(row)
    db.commit()

    return {
        "ok": True,
        "message": "Staff assignment removed successfully",
    }


# ======================================================
# CLOS
# ======================================================

@router.put("/courses/{course_id}/clos", status_code=200)
def set_course_clos(
    course_id: str,
    payload: SetClosIn,
    db: Session = Depends(get_db),
    admin: User = Depends(ADMIN_DEP),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.clos = json.dumps([c.model_dump() for c in payload.clos])

    db.commit()

    return {
        "ok": True,
        "message": "CLOs saved successfully",
        "clos_count": len(payload.clos),
    }