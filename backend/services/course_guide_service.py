import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from models.course import Course
from models.course_execution import WeeklyPlan
 # adjust name if your file is weekly_plans.py

UPLOAD_ROOT = Path("uploads") / "course_guides"

def _safe_filename(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1]
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)

def save_upload(course_id: str, file: UploadFile) -> str:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fname = f"{course_id}_{ts}_{_safe_filename(file.filename or 'course_guide')}"
    fpath = UPLOAD_ROOT / fname

    with open(fpath, "wb") as f:
        f.write(file.file.read())

    return str(fpath)

def extract_text_best_effort(file_path: str) -> str:
    """
    Robust extractor:
    - PDF: try pypdf text extraction
      if empty -> OCR using pdf2image + pytesseract (slow but reliable)
    - DOCX: python-docx
    """
    from pathlib import Path
    path = Path(file_path)
    ext = path.suffix.lower()

    # -------- DOCX --------
    if ext == ".docx":
        try:
            import docx
            d = docx.Document(str(path))
            return "\n".join([p.text for p in d.paragraphs]).strip()
        except Exception:
            return ""

    # -------- PDF --------
    if ext == ".pdf":
        text = ""
        # 1) normal extraction
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            parts = []
            for p in reader.pages:
                parts.append(p.extract_text() or "")
            text = "\n".join(parts).strip()
        except Exception:
            text = ""

        # 2) OCR fallback if very little text
        if len(text) < 50:
            try:
                from pdf2image import convert_from_path
                import pytesseract

                images = convert_from_path(str(path), dpi=200)
                ocr_parts = []
                for img in images[:20]:  # safety cap for large PDFs
                    ocr_parts.append(pytesseract.image_to_string(img) or "")
                text = "\n".join(ocr_parts).strip()
            except Exception:
                # if OCR not available, return what we have
                return text

        return text

    return ""


def ensure_weekly_plans(db: Session, course_id: str, planned_text: str):
    """
    Creates/updates 16 WeeklyPlan rows.
    For demo reliability: if we can’t parse week-wise topics, we store the whole extracted text
    and keep placeholders per week.
    """
    # Delete existing plans for clean regeneration
    db.query(WeeklyPlan).filter(WeeklyPlan.course_id == course_id).delete()

    now = datetime.now(timezone.utc)

    for w in range(1, 17):
        wp = WeeklyPlan(
            course_id=course_id,
            week_number=w,
            planned_topics=f"Week {w} topics (auto) — update later\n\n{planned_text[:2500]}",
            planned_assessments="",
            planned_start_date=None,
            planned_end_date=None,
            created_at=now,
            updated_at=now,
        )
        db.add(wp)

    db.commit()

def set_course_guide_metadata(db: Session, course: Course, file_path: str, extracted_text: str):
    """
    Store guide path + extracted text in Course row for quick access.
    Uses existing flexible fields to avoid new tables for now.
    """
    course.course_guide_path = file_path if hasattr(course, "course_guide_path") else None
    course.course_guide_text = extracted_text[:20000] if hasattr(course, "course_guide_text") else None
    db.commit()
