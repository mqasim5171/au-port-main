from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import mimetypes
from collections import Counter
from services.weekly_zip_upload_service import handle_weekly_zip_upload
from services.completeness_service import run_completeness

from core.db import SessionLocal
from .auth import get_current_user
from models.course import Course
from models.course_execution import WeeklyPlan, WeeklyExecution, DeviationLog
from models.uploads import Upload, UploadFileItem
from schemas.course_execution import (
    WeeklyPlanOut,
    WeeklyPlanUpdate,
    WeeklyExecutionCreate,
    WeeklyExecutionOut,
    WeeklyStatusSummary,
    WeeklyStatusItem,
    DeviationOut,
    DeviationResolve,
)
from services.course_execution import generate_weekly_plan_from_guide, update_deviations_for_course


router = APIRouter(prefix="/courses", tags=["Course Execution"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- COURSE PLAN SETUP ----------

@router.post("/{course_id}/weekly-plan/generate-from-guide", response_model=List[WeeklyPlanOut])
def generate_weekly_plan(
    course_id: str,
    guide_text: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    plans = generate_weekly_plan_from_guide(db, course, guide_text)
    update_deviations_for_course(db, course_id)
    return plans


@router.get("/{course_id}/weekly-plan", response_model=List[WeeklyPlanOut])
def list_weekly_plan(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    return (
        db.query(WeeklyPlan)
        .filter(WeeklyPlan.course_id == course_id)
        .order_by(WeeklyPlan.week_number)
        .all()
    )


@router.put("/weekly-plan/{week_id}", response_model=WeeklyPlanOut)
def update_weekly_plan(
    week_id: str,
    payload: WeeklyPlanUpdate,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    plan = db.get(WeeklyPlan, week_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    db.add(plan)
    db.commit()
    db.refresh(plan)

    update_deviations_for_course(db, plan.course_id)
    return plan


# ---------- EXECUTION TRACKING ----------

@router.post("/{course_id}/weekly-execution/{week_number}", response_model=WeeklyExecutionOut)
def upsert_weekly_execution(
    course_id: str,
    week_number: int,
    payload: WeeklyExecutionCreate,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    exec_obj = (
        db.query(WeeklyExecution)
        .filter(
            WeeklyExecution.course_id == course_id,
            WeeklyExecution.week_number == week_number,
        )
        .first()
    )

    if exec_obj is None:
        exec_obj = WeeklyExecution(course_id=course_id, week_number=week_number)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exec_obj, field, value)

    db.add(exec_obj)
    db.commit()
    db.refresh(exec_obj)

    update_deviations_for_course(db, course_id)
    return exec_obj


@router.get("/{course_id}/weekly-execution", response_model=List[WeeklyExecutionOut])
def list_weekly_execution(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    return (
        db.query(WeeklyExecution)
        .filter(WeeklyExecution.course_id == course_id)
        .order_by(WeeklyExecution.week_number)
        .all()
    )


@router.get("/{course_id}/weekly-status-summary", response_model=WeeklyStatusSummary)
def weekly_status_summary(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    plans = {
        p.week_number: p
        for p in db.query(WeeklyPlan)
        .filter(WeeklyPlan.course_id == course_id)
        .all()
    }
    execs = {
        e.week_number: e
        for e in db.query(WeeklyExecution)
        .filter(WeeklyExecution.course_id == course_id)
        .all()
    }

    max_week = max(plans.keys() | execs.keys() | {16})

    items: list[WeeklyStatusItem] = []
    for w in range(1, max_week + 1):
        plan = plans.get(w)
        exe = execs.get(w)

        if exe:
            status_val = exe.coverage_status
        elif plan:
            status_val = "behind" if plan.planned_end_date else "on_track"
        else:
            status_val = "skipped"

        items.append(
            WeeklyStatusItem(
                week_number=w,
                planned_topics=plan.planned_topics if plan else None,
                delivered_topics=exe.delivered_topics if exe else None,
                planned_assessments=plan.planned_assessments if plan else None,
                delivered_assessments=exe.delivered_assessments if exe else None,
                coverage_status=status_val,
            )
        )

    return WeeklyStatusSummary(course_id=course_id, items=items)


# ---------- DEVIATION HANDLING ----------

@router.get("/{course_id}/deviations", response_model=List[DeviationOut])
def list_deviations(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    return (
        db.query(DeviationLog)
        .filter(DeviationLog.course_id == course_id)
        .order_by(DeviationLog.week_number, DeviationLog.created_at)
        .all()
    )


@router.put("/deviations/{deviation_id}/resolve", response_model=DeviationOut)
def resolve_deviation(
    deviation_id: str,
    payload: DeviationResolve,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    dev = db.get(DeviationLog, deviation_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Deviation not found")

    dev.resolved = payload.resolved
    if payload.resolved:
        dev.resolved_at = dev.resolved_at or dev.created_at
        dev.resolved_by = current["id"] if isinstance(current, dict) else str(current.id)
    else:
        dev.resolved_at = None
        dev.resolved_by = None

    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev


# ✅ WEEKLY ZIP UPLOAD (Instructor)
@router.post("/{course_id}/weeks/{week_no}/weekly-zip")
async def upload_weekly_zip(
    course_id: str,
    week_no: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    role = (current.get("role") if isinstance(current, dict) else getattr(current, "role", "")) or ""
    role_l = role.lower()

    if not any(k in role_l for k in ["instructor", "faculty", "admin"]):
        raise HTTPException(status_code=403, detail="Only instructor/faculty/admin can upload weekly zip.")

    if week_no < 1 or week_no > 16:
        raise HTTPException(status_code=400, detail="week_no must be 1..16")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    user_id = current["id"] if isinstance(current, dict) else str(current.id)

    out = handle_weekly_zip_upload(
        db=db,
        course_id=course_id,
        week_no=week_no,
        user_id=user_id,
        zip_file_bytes=data,
        zip_filename=file.filename or f"week_{week_no}.zip",
    )

    # ✅ AUTO-RUN completeness for weekly uploads
    try:
        comp = run_completeness(
            db=db,
            course_id=out.get("course_id") or course_id,
            upload_id=out.get("upload_id"),
            week_no=week_no,
        )
    except Exception as e:
        comp = {"error": str(e)}

    out["completeness"] = comp
    return out


# -------------------- NEW: Explorer APIs --------------------

@router.get("/{course_id}/weeks/{week_no}/uploads")
def list_weekly_uploads(
    course_id: str,
    week_no: int,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    # weekly uploads are Upload rows with week_no + file_type_guess=weekly_zip
    q = (
        db.query(Upload)
        .filter(Upload.course_id == course_id, Upload.week_no == week_no)
        .order_by(Upload.created_at.desc())
    )
    rows = q.all()
    return [
        {
            "id": str(u.id),
            "filename_original": u.filename_original,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "bytes": int(u.bytes or 0),
            "file_type_guess": u.file_type_guess,
        }
        for u in rows
    ]


@router.get("/{course_id}/weeks/{week_no}/latest")
def weekly_latest_bundle(
    course_id: str,
    week_no: int,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    # latest upload
    up = (
        db.query(Upload)
        .filter(Upload.course_id == course_id, Upload.week_no == week_no)
        .order_by(Upload.created_at.desc())
        .first()
    )

    exe = (
        db.query(WeeklyExecution)
        .filter(WeeklyExecution.course_id == course_id, WeeklyExecution.week_number == week_no)
        .first()
    )

    if not up and not exe:
        return {"upload": None, "execution": None, "completeness": None}

    comp = None
    if up:
        try:
            comp = run_completeness(db=db, course_id=course_id, upload_id=str(up.id), week_no=week_no)
        except Exception as e:
            comp = {"error": str(e)}

    return {
        "upload": {
            "id": str(up.id),
            "filename_original": up.filename_original,
            "created_at": up.created_at.isoformat() if up.created_at else None,
            "bytes": int(up.bytes or 0),
        } if up else None,
        "execution": {
            "coverage_percent": float(exe.coverage_percent or 0),
            "coverage_status": exe.coverage_status,
            "missing_topics": exe.missing_topics,
            "matched_topics": exe.matched_topics,
            "last_updated_at": exe.last_updated_at.isoformat() if exe.last_updated_at else None,
        } if exe else None,
        "completeness": comp,
    }


@router.get("/uploads/{upload_id}/files")
def list_upload_files(
    upload_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    up = db.get(Upload, upload_id)
    if not up:
        raise HTTPException(status_code=404, detail="Upload not found")

    files = (
        db.query(UploadFileItem)
        .filter(UploadFileItem.upload_id == up.id)
        .order_by(UploadFileItem.filename.asc())
        .all()
    )

    return [
        {
            "filename": f.filename,
            "ext": f.ext,
            "bytes": int(f.bytes or 0),
            "text_chars": int(f.text_chars or 0),
            "download_url": f"/courses/uploads/{upload_id}/files/{f.filename}",
        }
        for f in files
    ]


@router.get("/uploads/{upload_id}/files/{filename}")
def download_upload_file(
    upload_id: str,
    filename: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    """
    Streams a file out of the extracted folder.
    We do NOT store extracted paths in DB, so we locate via Upload.parse_log safely.
    """
    up = db.get(Upload, upload_id)
    if not up:
        raise HTTPException(status_code=404, detail="Upload not found")

    manifest = up.parse_log or []
    filename = Path(filename).name  # sanitize

    candidate = None
    for m in manifest:
        p = m.get("path")
        if not p:
            continue
        if Path(p).name == filename:
            candidate = p
            break

    if not candidate:
        raise HTTPException(status_code=404, detail="File not found in this upload")

    fpath = Path(candidate)
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="File is missing on server storage")

    ctype, _ = mimetypes.guess_type(str(fpath))
    return FileResponse(
        path=str(fpath),
        media_type=ctype or "application/octet-stream",
        filename=filename,
    )



@router.get("/{course_id}/weekly-progress")
def weekly_progress(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    weeks = []
    weeks_behind = []
    missing_counter = Counter()

    for w in range(1, 17):
        # latest upload for this week
        up = (
            db.query(Upload)
            .filter(Upload.course_id == course_id, Upload.week_no == w)
            .order_by(Upload.created_at.desc())
            .first()
        )

        exe = (
            db.query(WeeklyExecution)
            .filter(WeeklyExecution.course_id == course_id, WeeklyExecution.week_number == w)
            .first()
        )

        coverage_percent = float(exe.coverage_percent or 0) if exe else 0.0
        coverage_status = exe.coverage_status if exe else ("skipped" if not up else "behind")

        completeness_percent = None
        if up:
            try:
                comp = run_completeness(db=db, course_id=course_id, upload_id=str(up.id), week_no=w)
                completeness_percent = float(comp.get("score_percent")) if isinstance(comp, dict) and comp.get("score_percent") is not None else None
            except Exception:
                completeness_percent = None

        if coverage_status == "behind":
            weeks_behind.append(w)

        # aggregate missing topics
        if exe and exe.missing_topics:
            for line in (exe.missing_topics or "").split("\n"):
                t = line.strip().lower()
                if t:
                    missing_counter[t] += 1

        weeks.append({
            "week_no": w,
            "has_upload": bool(up),
            "upload_id": str(up.id) if up else None,
            "coverage_percent": round(coverage_percent, 2),
            "coverage_status": coverage_status,
            "completeness_percent": round(completeness_percent, 2) if completeness_percent is not None else None,
        })

    top_missing = [{"topic": k, "count": v} for k, v in missing_counter.most_common(20)]

    return {
        "course_id": course_id,
        "weeks": weeks,
        "weeks_behind": weeks_behind,
        "top_missing_topics": top_missing,
    }
