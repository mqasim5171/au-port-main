from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from core.db import SessionLocal

from datetime import datetime, timezone
import tempfile, zipfile, os, shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from models.uploads import UploadText, Upload
from models.course_clo import CourseCLO
from models.course import Course

# ✅ NEW: read quiz PDFs from assessment module
from models.assessment import Assessment, AssessmentFile

from services.clo_extractor import extract_clos_and_assessments
from services.clo_parser import extract_clos_from_text
from services.text_processing import extract_text_from_path_or_bytes, parse_bytes
from services.upload_adapter import parse_document

from services.clo_alignment_service import run_clo_alignment

from routers.auth import get_current_user

from schemas.clo_alignment import (
    CLOAlignmentResponse,
    CLOAlignmentRequest,
    CLOAlignmentAutoResponse,
)

router = APIRouter(prefix="/align", tags=["CLO Alignment"])


# ======================================================
# DB
# ======================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================================================
# Helpers
# ======================================================

def utcnow():
    return datetime.now(timezone.utc)


def _clean_lines(text: str) -> List[str]:
    return [x.strip() for x in (text or "").splitlines() if x.strip()]


def _safe_json(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


def _clos_from_course_json(course: Optional[Course]) -> List[str]:
    """
    Admin panel stores course.clos as JSON string:
      [{"code":"CLO1","description":"..."}, ...]
    Convert into list[str] used by alignment:
      ["CLO1: ...", "CLO2: ..."]
    """
    if not course or not getattr(course, "clos", None):
        return []

    raw = course.clos or ""
    try:
        data = json.loads(raw)
    except Exception:
        return []

    out: List[str] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                code = (item.get("code") or "").strip()
                desc = (item.get("description") or "").strip()
                if code and desc:
                    out.append(f"{code}: {desc}")
            elif isinstance(item, str) and item.strip():
                out.append(item.strip())

    return out


def _create_upload_row(
    db: Session,
    course_id: str,
    filename_original: str,
    filename_stored: str,
    ext: str,
    file_type_guess: str,
    bytes_len: int,
    parse_log: Optional[list],
) -> Upload:
    """
    Safe Upload creator (supports your mixed Upload model variants).
    """
    now = utcnow()
    u = Upload(course_id=course_id)

    if hasattr(u, "filename_original"):
        u.filename_original = filename_original
    if hasattr(u, "filename_stored"):
        u.filename_stored = filename_stored
    if hasattr(u, "ext"):
        u.ext = ext
    if hasattr(u, "file_type_guess"):
        u.file_type_guess = file_type_guess
    if hasattr(u, "bytes"):
        u.bytes = int(bytes_len or 0)
    if hasattr(u, "parse_log"):
        u.parse_log = parse_log or []
    if hasattr(u, "created_at"):
        try:
            u.created_at = now.replace(tzinfo=None)
        except Exception:
            u.created_at = now

    # legacy fallback
    if hasattr(u, "filename") and not getattr(u, "filename", None):
        u.filename = filename_original

    db.add(u)
    db.flush()
    return u


def _get_latest_assessment_text(db: Session, course_id: str) -> Optional[str]:
    """
    ✅ IMPORTANT:
    This is the main fix.
    CLO Alignment should use Assessment PDF text (questions) if available.
    """
    a = (
        db.query(Assessment)
        .filter(Assessment.course_id == course_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not a:
        return None

    af = (
        db.query(AssessmentFile)
        .filter(AssessmentFile.assessment_id == a.id)
        .order_by(AssessmentFile.created_at.desc())
        .first()
    )
    if not af:
        return None

    text = (af.extracted_text or "").strip()
    return text or None


def _get_latest_course_upload_text(db: Session, course_id: str) -> Optional[str]:
    """
    Fallback: use latest UploadText (weekly/material uploads) if assessment text not found.
    """
    latest_upload = (
        db.query(Upload)
        .filter(Upload.course_id == course_id)
        .order_by(Upload.created_at.desc())
        .first()
    )
    if not latest_upload:
        return None

    text_obj = (
        db.query(UploadText)
        .filter(UploadText.upload_id == latest_upload.id)
        .first()
    )
    if not text_obj:
        return None

    return (text_obj.text or "").strip() or None


# ======================================================
# AUTO ALIGN (Preview)
# ======================================================

@router.get("/{course_id}/auto", response_model=CLOAlignmentAutoResponse)
def auto_align_course(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    """
    Returns CLOs + detected assessments (no alignment yet).

    ✅ FIXED DATA SOURCE:
    1) Prefer Assessment module PDF text (AssessmentFile.extracted_text)
    2) Fallback to latest UploadText (course uploads)
    """

    # 1) First preference: uploaded CLO doc record
    latest_clo = (
        db.query(CourseCLO)
        .filter(CourseCLO.course_id == course_id)
        .order_by(CourseCLO.upload_date.desc())
        .first()
    )

    clos: List[str] = []
    if latest_clo and getattr(latest_clo, "clos_text", None):
        clos = _clean_lines(latest_clo.clos_text)

    # 2) Fallback: Admin panel course.clos JSON
    if not clos:
        course = db.query(Course).filter(Course.id == course_id).first()
        clos = _clos_from_course_json(course)

    if not clos:
        raise HTTPException(
            404,
            "No CLOs found for this course (set CLOs in Admin OR upload CLO document)."
        )

    # ✅ NEW: get assessment questions text
    text = _get_latest_assessment_text(db, course_id)

    # fallback: use latest UploadText if assessment text missing
    source = "assessment_pdf"
    if not text:
        text = _get_latest_course_upload_text(db, course_id)
        source = "latest_upload_text"

    if not text:
        raise HTTPException(
            404,
            "No text found. Upload an assessment PDF (preferred) or upload weekly/material files."
        )

    # detect assessments/questions
    _, assessments = extract_clos_and_assessments(text)
    if not assessments:
        raise HTTPException(
            400,
            f"No assessments detected from {source}. "
            "Make sure your PDF includes question patterns like 'Q1:' / 'Question 1:' / 'Quiz' / 'Marks'."
        )

    # audit preview only if we had a CourseCLO record
    if latest_clo and hasattr(latest_clo, "audit_json"):
        latest_clo.audit_json = {
            "type": "auto_align_preview",
            "assessments_count": len(assessments),
            "source": source,
            "ts": utcnow().isoformat(),
        }
        db.add(latest_clo)
        db.commit()

    return CLOAlignmentAutoResponse(
        clos=clos,
        assessments=assessments,
        alignment={},
    )


# ======================================================
# MANUAL ALIGN (Explainable)
# ======================================================

@router.post("/clo/{course_id}", response_model=CLOAlignmentResponse)
def manual_align_course(
    course_id: str,
    payload: CLOAlignmentRequest,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    """
    Explainable CLO ↔ Assessment alignment.
    """

    if not payload.clos or not payload.assessments:
        raise HTTPException(400, "CLOs and assessments are required")

    assessments = [{"name": a.name} for a in payload.assessments]

    result = run_clo_alignment(
        clos=payload.clos,
        assessments=assessments,
        threshold=payload.threshold or 0.65,
    )

    latest_clo = (
        db.query(CourseCLO)
        .filter(CourseCLO.course_id == course_id)
        .order_by(CourseCLO.upload_date.desc())
        .first()
    )
    if latest_clo:
        if hasattr(latest_clo, "alignment_json"):
            latest_clo.alignment_json = _safe_json(result)
        if hasattr(latest_clo, "audit_json"):
            latest_clo.audit_json = {
                "type": "manual_alignment",
                "avg_top": result.get("avg_top"),
                "flags": result.get("flags"),
                "threshold": payload.threshold or 0.65,
                "user": getattr(current, "id", None),
                "ts": utcnow().isoformat(),
            }
        db.add(latest_clo)
        db.commit()

    return CLOAlignmentResponse(**result)


# ======================================================
# ZIP ALIGN (CLO + Materials)
# ======================================================

@router.post("/zip/{course_id}", response_model=CLOAlignmentResponse)
async def align_from_zip(
    course_id: str,
    clos_file: UploadFile = File(...),
    materials_zip: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    """
    CLO file + materials ZIP → explainable semantic alignment.
    """

    clo_bytes = await clos_file.read()
    if not clo_bytes:
        raise HTTPException(400, "Empty CLO file")

    clo_text = extract_text_from_path_or_bytes(clo_bytes, clos_file.filename)
    clos = extract_clos_from_text(clo_text) or []
    if not clos:
        clos, _ = extract_clos_and_assessments(clo_text or "")
    clos = _clean_lines("\n".join(clos))
    if not clos:
        raise HTTPException(400, "No CLOs extracted")

    clo_entry = CourseCLO(course_id=course_id, clos_text="\n".join(clos))
    if hasattr(clo_entry, "audit_json"):
        clo_entry.audit_json = {
            "type": "zip_upload",
            "uploaded_by": getattr(current, "id", None),
            "filename": clos_file.filename,
            "ts": utcnow().isoformat(),
        }
    db.add(clo_entry)
    db.commit()

    tmp_dir = tempfile.mkdtemp()
    aggregated_text = ""
    parse_manifest: List[Dict[str, Any]] = []

    try:
        zip_bytes = await materials_zip.read()
        zip_path = os.path.join(tmp_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp_dir)

        for root, _, files in os.walk(tmp_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                if fpath == zip_path:
                    continue

                parsed = {}
                try:
                    parsed = parse_document(fpath) or {}
                except Exception as e:
                    parsed = {"text": "", "error": str(e)}

                if not (parsed.get("text") or "").strip():
                    try:
                        with open(fpath, "rb") as fh:
                            parsed2 = parse_bytes(fh.read(), fname) or {}
                        if parsed2.get("text"):
                            parsed = parsed2
                    except Exception:
                        pass

                text = (parsed.get("text") or "").strip()
                if text:
                    aggregated_text += text + "\n\n"

                parse_manifest.append({
                    "path": fpath,
                    "ext": Path(fpath).suffix.lower(),
                    "chars": len(text),
                    "error": parsed.get("error"),
                })

        if not aggregated_text.strip():
            raise HTTPException(400, "No text extracted from ZIP")

        upload_entry = _create_upload_row(
            db=db,
            course_id=course_id,
            filename_original=materials_zip.filename or "materials.zip",
            filename_stored="upload.zip",
            ext="zip",
            file_type_guess="clo_materials_zip",
            bytes_len=len(zip_bytes),
            parse_log=parse_manifest,
        )
        db.commit()

        db.add(UploadText(upload_id=upload_entry.id, text=aggregated_text))
        db.commit()

        _, assessments = extract_clos_and_assessments(aggregated_text)
        if not assessments:
            raise HTTPException(400, "No assessments found in materials")

        result = run_clo_alignment(
            clos=clos,
            assessments=[{"name": a} for a in assessments],
        )

        if hasattr(clo_entry, "alignment_json"):
            clo_entry.alignment_json = _safe_json(result)
        if hasattr(clo_entry, "materials_upload_id"):
            clo_entry.materials_upload_id = str(upload_entry.id)
        db.add(clo_entry)
        db.commit()

        return CLOAlignmentResponse(**result)

    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass
