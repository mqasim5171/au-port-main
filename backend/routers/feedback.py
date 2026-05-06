from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.db import SessionLocal
from models.feedback import Feedback
from schemas.feedback import FeedbackIn, FeedbackOut
from .auth import get_current_user

router = APIRouter(prefix="/feedback", tags=["Feedback"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=FeedbackOut, status_code=201)
def submit_feedback(payload: FeedbackIn, db: Session = Depends(get_db), current=Depends(get_current_user)):
    # TODO: add sentiment from your original logic
    row = Feedback(
        course_id=payload.course_id,
        student_name=payload.student_name,
        feedback_text=payload.feedback_text,
        rating=payload.rating,
        sentiment="neutral",
    )
    db.add(row); db.commit(); db.refresh(row)
    return row

@router.get("/course/{course_id}", response_model=list[FeedbackOut])
def get_course_feedback(course_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    return db.query(Feedback).filter(Feedback.course_id == course_id).order_by(Feedback.created_at.desc()).all()
