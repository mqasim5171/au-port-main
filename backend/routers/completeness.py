# backend/routers/completeness.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import get_db
from routers.auth import get_current_user
from services.completeness_service import run_completeness
from models.completeness import CompletenessRun

router = APIRouter(prefix="/courses", tags=["Completeness Checker"])

@router.post("/{course_id}/completeness/run")
def run(course_id: str, upload_id: str, week_no: int | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        import uuid
        uid = uuid.UUID(upload_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid upload_id")
    try:
        return run_completeness(db, course_id=course_id, upload_id=uid, week_no=week_no)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{course_id}/completeness/latest")
def latest(course_id: str, week_no: int | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(CompletenessRun).filter(CompletenessRun.course_id == course_id)
    if week_no is not None:
        q = q.filter(CompletenessRun.week_no == week_no)
    row = q.order_by(CompletenessRun.created_at.desc()).first()
    return row.result_json if row else {"course_id": course_id, "week_no": week_no, "note": "no runs yet"}
