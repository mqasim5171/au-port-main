from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import SessionLocal
from models.assessment import Assessment
from routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/assessments", tags=["Assessments"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class QuestionsPayload(BaseModel):
    questions_text: str

@router.put("/{assessment_id}/questions")
def save_questions(
    assessment_id: str,
    payload: QuestionsPayload,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    a = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not a:
        raise HTTPException(404, "Assessment not found")

    a.questions_text = payload.questions_text or ""
    db.add(a)
    db.commit()
    return {"ok": True}
