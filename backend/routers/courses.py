# backend/routers/courses.py

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status,
    Form,
)
from sqlalchemy.orm import Session
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from typing import List, Optional
import os
import shutil

from core.db import SessionLocal
from .auth import get_current_user

from models.course import Course
from models.course_staff import CourseStaff
from models.file_upload import FileUpload
from models.material import CourseMaterial, CourseMaterialFile
from models.course_execution import WeeklyPlan

from schemas.course import CourseCreate, CourseOut

router = APIRouter(prefix="/courses", tags=["Courses"])


# -------------------- DB DEP --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- ROLE / ACCESS HELPERS --------------------
ROLE_ALIASES = {
    "administrator": "admin",
    "superadmin": "admin",
    "qec officer": "qec",
    "quality officer": "qec",
    "course lead": "course_lead",
    "faculty member": "faculty",
    "instructor": "faculty",
}


def _user_id(current) -> str:
    if isinstance(current, dict):
        return str(current.get("id") or "")
    return str(getattr(current, "id", "") or "")


def _user_role(current) -> str:
    if isinstance(current, dict):
        raw = current.get("role") or ""
    else:
        raw = getattr(current, "role", "") or ""

    role = str(raw).strip().lower()
    return ROLE_ALIASES.get(role, role)


def _is_admin_like(current) -> bool:
    return _user_role(current) in {"admin", "qec", "hod"}


def _is_teacher_like(current) -> bool:
    return _user_role(current) in {"course_lead", "faculty"}


def _ensure_course_exists(db: Session, course_id: str) -> Course:
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return course


def _assigned_course_ids(db: Session, current) -> list[str]:
    uid = _user_id(current)

    if not uid:
        return []

    rows = db.query(CourseStaff).filter(CourseStaff.user_id == uid).all()

    return [row.course_id for row in rows]


def _is_assigned_to_course(db: Session, course_id: str, current) -> bool:
    uid = _user_id(current)

    if not uid:
        return False

    row = (
        db.query(CourseStaff)
        .filter(
            CourseStaff.course_id == course_id,
            CourseStaff.user_id == uid,
        )
        .first()
    )

    return row is not None


def _ensure_can_view_course(db: Session, course_id: str, current):
    _ensure_course_exists(db, course_id)

    if _is_admin_like(current):
        return

    if _is_teacher_like(current) and _is_assigned_to_course(db, course_id, current):
        return

    raise HTTPException(
        status_code=403,
        detail="You do not have access to this course.",
    )


def _ensure_teacher_assigned_course_access(db: Session, course_id: str, current):
    """
    Used for teacher academic upload areas.
    Admin/QEC/HOD are intentionally blocked here because they should not upload
    teacher/course material.
    """
    _ensure_course_exists(db, course_id)

    if _is_teacher_like(current) and _is_assigned_to_course(db, course_id, current):
        return

    raise HTTPException(
        status_code=403,
        detail="Only assigned course staff can access this course material area.",
    )


def _ensure_admin_can_create_course(current):
    if _user_role(current) == "admin":
        return

    raise HTTPException(
        status_code=403,
        detail="Only admin can create courses.",
    )


# -------------------- LEGACY COURSE FOLDER UPLOAD --------------------
async def _save_course_upload(course_id: str, file: UploadFile, db: Session, current):
    _ensure_teacher_assigned_course_access(db, course_id, current)

    base_dir = Path("storage") / "course_uploads" / course_id
    base_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = base_dir / f"{ts}_{file.filename}"

    total_bytes = 0

    with dest.open("wb") as f_out:
        while chunk := await file.read(1024 * 1024):
            total_bytes += len(chunk)
            f_out.write(chunk)

    rec = FileUpload(
        id=str(uuid4()),
        course_id=course_id,
        user_id=_user_id(current),
        filename=file.filename,
        file_type=file.content_type,
        file_size=total_bytes,
        upload_date=datetime.now(timezone.utc),
        validation_status="pending",
        validation_details="Not validated yet",
    )

    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "id": rec.id,
        "filename": rec.filename,
        "upload_date": rec.upload_date,
        "validation_status": rec.validation_status,
    }


# -------------------- BASIC COURSE CRUD --------------------
@router.get("", response_model=list[CourseOut])
@router.get("/", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db), current=Depends(get_current_user)):
    """
    Admin/QEC/HOD can see all courses.
    Course Lead/Faculty can only see courses assigned to them in CourseStaff.
    """
    if _is_admin_like(current):
        return (
            db.query(Course)
            .order_by(Course.created_at.desc())
            .limit(200)
            .all()
        )

    assigned_ids = _assigned_course_ids(db, current)

    if not assigned_ids:
        return []

    return (
        db.query(Course)
        .filter(Course.id.in_(assigned_ids))
        .order_by(Course.created_at.desc())
        .all()
    )


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    """
    This route is admin-only.
    Main admin panel should normally use /admin/courses.
    """
    _ensure_admin_can_create_course(current)

    c = Course(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)

    return c


@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    _ensure_can_view_course(db, course_id, current)

    c = db.get(Course, course_id)
    return c


# -------------------- WEEKLY PLAN FOR WEEKLY UPLOAD --------------------
@router.get("/{course_id}/weekly-plans")
def get_course_weekly_plans_for_upload(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    """
    Used by Weekly Upload page.

    It returns the Week 1-16 plan generated from the Course Guide.
    Assigned course staff can see the plan so they can upload weekly material
    against the correct planned topics.
    """
    _ensure_teacher_assigned_course_access(db, course_id, current)

    plans = (
        db.query(WeeklyPlan)
        .filter(WeeklyPlan.course_id == course_id)
        .order_by(WeeklyPlan.week_number.asc())
        .all()
    )

    return [
        {
            "id": p.id,
            "week_number": p.week_number,
            "planned_topics": p.planned_topics,
            "created_at": p.created_at,
        }
        for p in plans
    ]


# -------------------- LEGACY UPLOAD LIST --------------------
@router.get("/{course_id}/uploads")
def list_course_uploads(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    _ensure_teacher_assigned_course_access(db, course_id, current)

    uploads = (
        db.query(FileUpload)
        .filter(FileUpload.course_id == course_id)
        .order_by(FileUpload.upload_date.desc())
        .all()
    )

    return [
        {
            "id": u.id,
            "filename": u.filename,
            "upload_date": u.upload_date,
            "validation_status": u.validation_status,
        }
        for u in uploads
    ]


@router.post("/{course_id}/upload")
async def upload_course_file(
    course_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    return await _save_course_upload(course_id, file, db, current)


# ======================================================================
# 4-FOLDER MATERIAL SYSTEM
# ======================================================================

MATERIAL_STORAGE_ROOT = Path("storage") / "materials"
MATERIAL_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def _infer_folder_type(title: str) -> str:
    t = (title or "").lower().strip()

    if t.startswith("lecture"):
        return "lecture_notes"

    if t.startswith("slide"):
        return "slides"

    if t.startswith("assignment"):
        return "assignments"

    if t.startswith("quiz"):
        return "quizzes"

    if t.startswith("mid"):
        return "midterm"

    if t.startswith("final"):
        return "finalterm"

    return "other"


@router.get("/{course_id}/materials")
def list_course_materials(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    _ensure_teacher_assigned_course_access(db, course_id, current)

    mats: list[CourseMaterial] = (
        db.query(CourseMaterial)
        .filter(CourseMaterial.course_id == course_id)
        .order_by(CourseMaterial.created_at.desc())
        .all()
    )

    mat_ids = [m.id for m in mats]

    files: list[CourseMaterialFile] = []

    if mat_ids:
        files = (
            db.query(CourseMaterialFile)
            .filter(CourseMaterialFile.material_id.in_(mat_ids))
            .all()
        )

    file_map: dict[str, list[CourseMaterialFile]] = {m_id: [] for m_id in mat_ids}

    for f in files:
        file_map.setdefault(f.material_id, []).append(f)

    def file_to_dict(f: CourseMaterialFile) -> dict:
        url_path = f.stored_path.replace(os.sep, "/")

        if not url_path.startswith("storage/"):
            url_path = f"storage/{url_path}"

        return {
            "id": f.id,
            "filename": f.filename,
            "display_name": f.filename,
            "url": f"/{url_path}",
            "size_bytes": f.size_bytes,
            "content_type": f.content_type,
            "uploaded_at": f.uploaded_at,
        }

    out = []

    for m in mats:
        out.append(
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "folder": m.folder_type,
                "folder_type": m.folder_type,
                "created_at": m.created_at,
                "files": [file_to_dict(f) for f in file_map.get(m.id, [])],
            }
        )

    return out


@router.post(
    "/{course_id}/materials",
    status_code=status.HTTP_201_CREATED,
)
async def create_course_material(
    course_id: str,
    title: str = Form(...),
    description: str = Form(""),
    folder_hint: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    _ensure_teacher_assigned_course_access(db, course_id, current)

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    folder_type = folder_hint or _infer_folder_type(title)

    allowed_folders = {
        "lecture_notes",
        "slides",
        "assignments",
        "quizzes",
        "midterm",
        "finalterm",
        "other",
    }

    if folder_type not in allowed_folders:
        folder_type = "other"

    mat = CourseMaterial(
        id=str(uuid4()),
        course_id=course_id,
        title=title.strip(),
        description=description.strip() if description else "",
        folder_type=folder_type,
        created_by=_user_id(current),
    )

    db.add(mat)
    db.flush()

    mat_dir = MATERIAL_STORAGE_ROOT / course_id / mat.id
    mat_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        original_name = f.filename or "uploaded_file"
        safe_name = Path(original_name).name
        stored_name = f"{uuid4().hex}_{safe_name}"
        dest = mat_dir / stored_name

        total_bytes = 0

        with dest.open("wb") as out:
            while chunk := await f.read(1024 * 1024):
                total_bytes += len(chunk)
                out.write(chunk)

        rel_path = os.path.relpath(dest, ".")

        mf = CourseMaterialFile(
            material_id=mat.id,
            filename=safe_name,
            stored_path=rel_path,
            content_type=f.content_type or "application/octet-stream",
            size_bytes=total_bytes,
        )

        db.add(mf)

    db.commit()
    db.refresh(mat)

    return {
        "ok": True,
        "id": mat.id,
        "message": "Material created",
    }


@router.delete("/{course_id}/materials/{material_id}", status_code=200)
def delete_course_material(
    course_id: str,
    material_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    _ensure_teacher_assigned_course_access(db, course_id, current)

    mat = db.get(CourseMaterial, material_id)

    if not mat or mat.course_id != course_id:
        raise HTTPException(status_code=404, detail="Material not found")

    files = (
        db.query(CourseMaterialFile)
        .filter(CourseMaterialFile.material_id == material_id)
        .all()
    )

    for f in files:
        if f.stored_path:
            try:
                path = Path(f.stored_path)
                if path.exists() and path.is_file():
                    path.unlink()
            except Exception:
                pass

        db.delete(f)

    mat_dir = MATERIAL_STORAGE_ROOT / course_id / material_id

    try:
        if mat_dir.exists() and mat_dir.is_dir():
            shutil.rmtree(mat_dir)
    except Exception:
        pass

    db.delete(mat)
    db.commit()

    return {
        "ok": True,
        "message": "Material deleted successfully",
    }


@router.delete(
    "/{course_id}/materials/{material_id}/files/{file_id}",
    status_code=200,
)
def delete_course_material_file(
    course_id: str,
    material_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    _ensure_teacher_assigned_course_access(db, course_id, current)

    mat = db.get(CourseMaterial, material_id)

    if not mat or mat.course_id != course_id:
        raise HTTPException(status_code=404, detail="Material not found")

    file_row = db.get(CourseMaterialFile, file_id)

    if not file_row or file_row.material_id != material_id:
        raise HTTPException(status_code=404, detail="File not found")

    if file_row.stored_path:
        try:
            path = Path(file_row.stored_path)
            if path.exists() and path.is_file():
                path.unlink()
        except Exception:
            pass

    db.delete(file_row)
    db.commit()

    return {
        "ok": True,
        "message": "File deleted successfully",
    }