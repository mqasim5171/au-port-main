from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime, timezone

from core.db import SessionLocal
from .auth import get_current_user
from models.course import Course
from models.course_clo import CourseCLO
from schemas.clo import CLOUploadResponse, CLOItem
from services.upload_adapter import parse_document
from services.clo_parser import extract_clos_from_text

router = APIRouter(prefix="/courses", tags=["Courses (CLOs)"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

STORAGE_DIR = Path("storage") / "course_clos"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/{course_id}/upload-clo", response_model=CLOUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_course_clo(
    course_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Save file
    course_dir = STORAGE_DIR / course_id
    course_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = course_dir / f"{ts}_{file.filename}"

    total_bytes = 0
    with dest.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            total_bytes += len(chunk)
            out.write(chunk)

    # Parse and extract CLOs
    parsed = parse_document(str(dest)) or {}
    parsed_text = parsed.get("text")
    clos_list = extract_clos_from_text(parsed_text or "")
    clos_text = "\n".join(clos_list) if clos_list else None

    rec = CourseCLO(
        course_id=course_id,
        user_id=getattr(current, "id", None),
        filename=file.filename,
        file_type=file.content_type,
        file_size=total_bytes,
        upload_date=datetime.now(timezone.utc),
        parsed_text=parsed_text,
        clos_text=clos_text,
        file_path=str(dest)
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return CLOUploadResponse(id=str(rec.id), filename=rec.filename, upload_date=rec.upload_date)

@router.get("/{course_id}/clos", response_model=list[CLOItem])
def list_course_clos(course_id: str, db: Session = Depends(get_db), current = Depends(get_current_user)):
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="Course not found")

    rows = db.query(CourseCLO).filter(CourseCLO.course_id == course_id).order_by(CourseCLO.upload_date.desc()).all()
    out = []
    for r in rows:
        clos = [line.strip() for line in (r.clos_text or "").splitlines() if line.strip()]
        out.append(CLOItem(id=r.id, filename=r.filename, upload_date=r.upload_date, clos=clos).model_dump())
    return out
