import os
import re
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.db import SessionLocal
from core.rbac import require_roles
from models.admin_document import AdminDocument
from models.user import User


router = APIRouter(prefix="/admin-documents", tags=["Administrative Documents"])

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "admin_documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


ALLOWED_CATEGORIES = {
    "policy",
    "contract",
    "budget",
    "rules",
    "template",
    "accreditation",
    "meeting_minutes",
    "other",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "document")
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name or "document"


def _next_version(db: Session, title: str, category: str) -> int:
    latest = (
        db.query(AdminDocument)
        .filter(
            AdminDocument.title == title,
            AdminDocument.category == category,
        )
        .order_by(AdminDocument.version.desc())
        .first()
    )

    if not latest:
        return 1

    return int(latest.version or 0) + 1


@router.post("/")
def upload_admin_document(
    title: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("admin", "qec")),
):
    category = category.strip().lower()

    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}",
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    safe_name = _safe_filename(file.filename)
    version = _next_version(db, title=title.strip(), category=category)

    stored_filename = f"{category}_v{version}_{safe_name}"
    file_path = UPLOAD_DIR / stored_filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save uploaded document: {str(e)}",
        )

    doc = AdminDocument(
        title=title.strip(),
        category=category,
        description=description,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        content_type=file.content_type,
        version=version,
        uploaded_by=current.id,
        uploaded_by_name=current.full_name or current.username,
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "id": doc.id,
        "title": doc.title,
        "category": doc.category,
        "description": doc.description,
        "original_filename": doc.original_filename,
        "version": doc.version,
        "uploaded_by_name": doc.uploaded_by_name,
        "created_at": doc.created_at,
    }


@router.get("/")
def list_admin_documents(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("admin", "qec", "hod")),
):
    query = db.query(AdminDocument)

    if category and category != "all":
        query = query.filter(AdminDocument.category == category.strip().lower())

    docs = query.order_by(AdminDocument.created_at.desc()).all()

    return [
        {
            "id": d.id,
            "title": d.title,
            "category": d.category,
            "description": d.description,
            "original_filename": d.original_filename,
            "version": d.version,
            "uploaded_by_name": d.uploaded_by_name,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.get("/{document_id}/download")
def download_admin_document(
    document_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("admin", "qec", "hod")),
):
    doc = db.get(AdminDocument, document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(doc.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing.")

    return FileResponse(
        path=str(file_path),
        filename=doc.original_filename,
        media_type=doc.content_type or "application/octet-stream",
    )


@router.delete("/{document_id}")
def delete_admin_document(
    document_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("admin")),
):
    doc = db.get(AdminDocument, document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(doc.file_path)

    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass

    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully."}