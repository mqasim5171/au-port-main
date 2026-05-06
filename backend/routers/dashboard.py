# backend/routers/dashboard.py
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from core.db import SessionLocal

# Try to import optional models; fall back to None if not present
try:
    from models.course import Course
except Exception:
    Course = None

try:
    from models.file_upload import FileUpload
except Exception:
    FileUpload = None

try:
    from models.feedback import Feedback
except Exception:
    Feedback = None

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # totals
    total_courses = db.query(Course).count() if Course else 0
    total_uploads = db.query(FileUpload).count() if FileUpload else 0
    total_feedback = db.query(Feedback).count() if Feedback else 0

    # recent uploads (last 5)
    recent_uploads = []
    if FileUpload:
        q = db.query(FileUpload)
        # adjust field names to your model (filename, created_at, status etc.)
        if hasattr(FileUpload, "created_at"):
            q = q.order_by(desc(FileUpload.created_at))
        recent = q.limit(5).all()
        for r in recent:
            recent_uploads.append({
                "filename": getattr(r, "original_filename", None) or getattr(r, "filename", "file"),
                "upload_date": getattr(r, "created_at", None) or getattr(r, "upload_date", None),
                "validation_status": getattr(r, "validation_status", "unknown"),
            })

    # recent feedback (last 5)
    recent_feedback = []
    if Feedback:
        q = db.query(Feedback)
        if hasattr(Feedback, "created_at"):
            q = q.order_by(desc(Feedback.created_at))
        recent = q.limit(5).all()
        for r in recent:
            recent_feedback.append({
                "feedback_text": getattr(r, "text", None) or getattr(r, "feedback_text", "") or "",
                "student_name": getattr(r, "student_name", None) or "Anonymous",
                "sentiment": getattr(r, "sentiment", None) or "neutral",
            })

    return {
        "total_courses": total_courses,
        "total_uploads": total_uploads,
        "total_feedback": total_feedback,
        "recent_uploads": recent_uploads,
        "recent_feedback": recent_feedback,
    }
