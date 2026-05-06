from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import SessionLocal
from routers.auth import get_current_user
from models.override import ManualOverride
from core.rbac import require_roles

router = APIRouter(prefix="/overrides", tags=["Overrides"])


class OverrideRequest(BaseModel):
    course_id: str
    module: str  # completeness / quality
    original_score: float
    overridden_score: float
    reason: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def create_override(
    payload: OverrideRequest,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec")),
):
    if payload.module not in ["completeness", "quality"]:
        raise HTTPException(status_code=400, detail="Invalid module")

    row = ManualOverride(
        course_id=payload.course_id,
        module=payload.module,
        original_score=payload.original_score,
        overridden_score=payload.overridden_score,
        reason=payload.reason,
        created_by=str(current.get("id")),
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "message": "Override applied successfully",
    }


@router.get("/{course_id}")
def get_overrides(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec")),
):
    rows = (
        db.query(ManualOverride)
        .filter(ManualOverride.course_id == course_id)
        .order_by(ManualOverride.created_at.desc())
        .all()
    )

    return [
        {
            "module": r.module,
            "original_score": r.original_score,
            "overridden_score": r.overridden_score,
            "reason": r.reason,
            "created_at": r.created_at,
        }
        for r in rows
    ]