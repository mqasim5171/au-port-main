# backend/routers/student_router.py

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
import csv
import io

from core.db import get_db
from models.student import Student  # your new Student model


router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/import")
async def import_students(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Import students from CSV.

    Expected columns: reg_no, name, program, section
    """
    content = await file.read()
    text = content.decode("utf-8")

    reader = csv.DictReader(io.StringIO(text))

    created = 0
    skipped_existing = 0

    for row in reader:
        reg_no = (row.get("reg_no") or "").strip()
        if not reg_no:
            continue

        existing = db.query(Student).filter_by(reg_no=reg_no).first()
        if existing:
            skipped_existing += 1
            continue

        s = Student(
            reg_no=reg_no,
            name=(row.get("name") or "").strip(),
            program=(row.get("program") or "").strip(),
            section=(row.get("section") or "").strip(),
        )
        db.add(s)
        created += 1

    db.commit()

    return {
        "status": "ok",
        "created": created,
        "skipped_existing": skipped_existing,
    }
