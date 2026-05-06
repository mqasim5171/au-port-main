from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.db import SessionLocal
from models.exception import ExceptionLog
from routers.auth import get_current_user
from core.rbac import require_roles

router = APIRouter(prefix="/exceptions", tags=["Exceptions"])


class ExceptionStatusUpdate(BaseModel):
    status: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def list_exceptions(
    status: str | None = None,
    module: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec")),
):
    q = db.query(ExceptionLog)

    if status:
        q = q.filter(ExceptionLog.status == status)

    if module:
        q = q.filter(ExceptionLog.module == module)

    if severity:
        q = q.filter(ExceptionLog.severity == severity)

    rows = q.order_by(ExceptionLog.created_at.desc()).limit(100).all()

    return [
        {
            "id": r.id,
            "course_id": r.course_id,
            "upload_id": r.upload_id,
            "module": r.module,
            "error_type": r.error_type,
            "message": r.message,
            "severity": r.severity,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.patch("/{exception_id}/status")
def update_exception_status(
    exception_id: str,
    payload: ExceptionStatusUpdate,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec")),
):
    allowed = {"open", "resolved", "ignored"}

    if payload.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Use open, resolved, or ignored.",
        )

    row = db.get(ExceptionLog, exception_id)

    if not row:
        raise HTTPException(status_code=404, detail="Exception not found")

    row.status = payload.status
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "status": row.status,
        "message": "Exception status updated successfully.",
    }


@router.get("/summary")
def exception_summary(
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec")),
):
    rows = db.query(ExceptionLog).all()

    summary = {
        "total": len(rows),
        "open": 0,
        "resolved": 0,
        "ignored": 0,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for r in rows:
        if r.status in summary:
            summary[r.status] += 1

        if r.severity in summary:
            summary[r.severity] += 1

    return summary