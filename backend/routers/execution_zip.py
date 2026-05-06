# backend/routers/execution_zip.py

import uuid
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from core.db import SessionLocal
from routers.auth import get_current_user

from models.course import Course
from models.course_execution import WeeklyPlan, WeeklyExecution, DeviationLog

from services.upload_adapter import parse_document
from services.execution_compare import compare_week


router = APIRouter(prefix="/courses", tags=["Execution ZIP"])

ALLOWED_EXTS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
MAX_FILES = 200


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def clean_text(val: Optional[str]) -> Optional[str]:
    """
    PostgreSQL TEXT/VARCHAR cannot store NUL bytes (\x00).
    Also removes other control chars while keeping \n, \r, \t.
    """
    if val is None:
        return None
    if not isinstance(val, str):
        val = str(val)

    # remove NUL bytes (root cause of your crash)
    val = val.replace("\x00", "")

    # remove other low ASCII control chars except newline/tab/cr
    out = []
    for ch in val:
        o = ord(ch)
        if ch in ("\n", "\r", "\t"):
            out.append(ch)
        elif o >= 32:
            out.append(ch)
        # else skip
    return "".join(out).strip()


def _safe_extract_zip(zip_path: str, dest_dir: str) -> List[str]:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    extracted_files: List[str] = []
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()

        if len(names) > MAX_FILES:
            names = names[:MAX_FILES]

        for member in names:
            # skip directories
            if member.endswith("/"):
                continue

            # ✅ skip macOS junk files
            if member.startswith("__MACOSX/"):
                continue
            if Path(member).name.startswith("._"):
                continue

            # prevent zip slip
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as out:
                out.write(src.read())

            extracted_files.append(str(target))

    return extracted_files


def _normalize_coverage(coverage_raw: float) -> Tuple[float, float]:
    """
    compare_week in your project may return:
      - 0..1  (ratio)
      - 0..100 (percent)
    We output both:
      coverage_score: 0..1
      coverage_percent: 0..100
    """
    try:
        c = float(coverage_raw)
    except Exception:
        c = 0.0

    if c <= 1.5:
        score = max(0.0, min(1.0, c))
        percent = score * 100.0
    else:
        percent = max(0.0, min(100.0, c))
        score = percent / 100.0

    return score, percent


@router.post("/{course_id}/weeks/{week_no}/weekly-zip")
async def upload_weekly_zip(
    course_id: str,
    week_no: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    # ---- auth ----
    role = (current.get("role") if isinstance(current, dict) else getattr(current, "role", "")) or ""
    role_l = role.lower()
    if not any(k in role_l for k in ["instructor", "faculty", "admin"]):
        raise HTTPException(status_code=403, detail="Only instructor/faculty/admin can upload weekly zip.")

    if week_no < 1 or week_no > 16:
        raise HTTPException(status_code=400, detail="week_no must be 1..16")

    # course exists?
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # ---- read zip ----
    zip_bytes = await file.read()
    if not zip_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    now = datetime.now(timezone.utc)
    upload_id = str(uuid.uuid4())

    storage_root = Path("uploads/weekly") / course_id / f"week_{week_no}" / upload_id
    storage_root.mkdir(parents=True, exist_ok=True)

    zip_name = file.filename or f"week_{week_no}.zip"
    zip_path = storage_root / zip_name
    zip_path.write_bytes(zip_bytes)

    extracted_dir = storage_root / "extracted"
    files = _safe_extract_zip(str(zip_path), str(extracted_dir))

    # ---- parse files ----
    texts: List[str] = []
    manifest = []

    for fp in files:
        ext = Path(fp).suffix.lower()
        if ext not in ALLOWED_EXTS:
            continue

        try:
            parsed = parse_document(fp) or {}
        except Exception as e:
            parsed = {"text": "", "error": f"parse failed: {e}"}

        t = clean_text(parsed.get("text") or "") or ""
        if t:
            texts.append(t)

        manifest.append(
            {"path": fp, "ext": ext, "chars": len(t), "error": parsed.get("error")}
        )

    delivered_topics_text = clean_text("\n\n".join(texts)) or ""
    delivered_topics_text = delivered_topics_text[:20000]  # cap

    # ---- planned topics for this week ----
    plan = (
        db.query(WeeklyPlan)
        .filter(WeeklyPlan.course_id == course_id, WeeklyPlan.week_number == week_no)
        .first()
    )
    plan_text = clean_text((plan.planned_topics if plan else "") or "") or ""

    # ---- compare ----
    coverage_raw, missing_terms, plan_terms = compare_week(plan_text, delivered_topics_text)

    coverage_score, coverage_percent = _normalize_coverage(coverage_raw)

    missing_terms = missing_terms or []
    plan_terms = plan_terms or []
    matched_terms = [t for t in plan_terms if t not in set(missing_terms)]

    missing_topics_str = clean_text("\n".join(missing_terms)) or ""
    matched_topics_str = clean_text("\n".join(matched_terms)) or ""

    missing_topics_str = missing_topics_str[:20000]
    matched_topics_str = matched_topics_str[:20000]

    coverage_status = "on_track" if coverage_percent >= 80.0 else "behind"

    # ---- upsert WeeklyExecution (matches your model) ----
    ex = (
        db.query(WeeklyExecution)
        .filter(WeeklyExecution.course_id == course_id, WeeklyExecution.week_number == week_no)
        .first()
    )
    if not ex:
        ex = WeeklyExecution(
            id=str(uuid.uuid4()),
            course_id=course_id,
            week_number=week_no,
        )
        db.add(ex)

    ex.coverage_percent = coverage_percent
    ex.coverage_status = coverage_status
    ex.delivered_topics = clean_text(delivered_topics_text)
    ex.missing_topics = clean_text(missing_topics_str)
    ex.matched_topics = clean_text(matched_topics_str)
    ex.last_updated_at = now

    # deviation log if low coverage
    if coverage_percent < 80.0:
        db.add(
            DeviationLog(
                course_id=course_id,
                week_number=week_no,
                type="coverage_low",
                details=clean_text(
                    json.dumps(
                        {
                            "coverage_percent": coverage_percent,
                            "missing_terms": missing_terms[:200],
                            "note": "Weekly upload coverage below threshold.",
                        },
                        ensure_ascii=False,
                    )
                ),
            )
        )

    db.commit()
    db.refresh(ex)

    # ✅ return BOTH shapes so frontend never breaks
    return {
        "course_id": course_id,
        "week_no": week_no,
        "coverage_score": coverage_score,          # 0..1
        "coverage_percent": coverage_percent,      # 0..100
        "coverage_status": coverage_status,
        "missing_terms": missing_terms[:200],
        "matched_terms": matched_terms[:200],
        "deviation_flag": bool(coverage_percent < 80.0),
        "files_seen": len(files),
        "files_used": len([m for m in manifest if m["ext"] in ALLOWED_EXTS]),
    }
