# backend/routers/suggestions.py

from routers.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import get_db

from models.course import Course              # ✅ REQUIRED IMPORT
from services.suggestion_engine import generate_suggestions
from models.suggestion import Suggestion, SuggestionAction
from schemas.suggestion import (
    SuggestionCreate,
    SuggestionUpdate,
    SuggestionOut,
    SuggestionDetailOut,
    ActionCreate,
    ActionOut,
)

router = APIRouter(tags=["Suggestions"])


# ======================================================
# LIST EXISTING SUGGESTIONS
# ======================================================

@router.get("/courses/{course_id}/suggestions", response_model=list[SuggestionOut])
def list_suggestions(
    course_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return (
        db.query(Suggestion)
        .filter(Suggestion.course_id == course_id)
        .order_by(Suggestion.created_at.desc())
        .all()
    )


# ======================================================
# MANUAL CREATE
# ======================================================

@router.post("/courses/{course_id}/suggestions", response_model=SuggestionOut)
def create_suggestion(
    course_id: str,
    payload: SuggestionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    s = Suggestion(
        course_id=course_id,
        owner_id=payload.owner_id,
        source=payload.source,
        text=payload.text,
        priority=payload.priority,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ======================================================
# GET SINGLE SUGGESTION
# ======================================================

@router.get("/suggestions/{suggestion_id}", response_model=SuggestionDetailOut)
def get_suggestion(suggestion_id: str, db: Session = Depends(get_db)):
    s = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return s


# ======================================================
# UPDATE SUGGESTION
# ======================================================

@router.put("/suggestions/{suggestion_id}", response_model=SuggestionOut)
def update_suggestion(
    suggestion_id: str,
    payload: SuggestionUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    s = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if payload.status:
        s.status = payload.status
    if payload.priority:
        s.priority = payload.priority
    if payload.text:
        s.text = payload.text

    db.add(
        SuggestionAction(
            suggestion_id=s.id,
            user_id=user.id,
            action_type="status_change",
            notes="Suggestion updated",
        )
    )

    db.commit()
    db.refresh(s)
    return s


# ======================================================
# ADD ACTION / COMMENT
# ======================================================

@router.post("/suggestions/{suggestion_id}/actions", response_model=ActionOut)
def add_action(
    suggestion_id: str,
    payload: ActionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    a = SuggestionAction(
        suggestion_id=suggestion_id,
        user_id=user.id,
        action_type=payload.action_type,
        notes=payload.notes,
        evidence_url=payload.evidence_url,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


# ======================================================
# AUTO-GENERATE AI SUGGESTIONS (FIXED)
# ======================================================

@router.post("/courses/{course_id}/suggestions/auto")
def generate_course_suggestions(
    course_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # 1️⃣ Resolve course (needed for StudentFeedback.course_name)
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2️⃣ Generate suggestions using real data
    texts = generate_suggestions(
        db=db,
        course_id=course_id,
        course_name=course.course_name,
    )

    # 3️⃣ Persist generated suggestions
    created = []
    for t in texts:
        s = Suggestion(
            course_id=course_id,
            owner_id=user.id,
            source="quality_engine",
            text=t,
            priority="high",
        )
        db.add(s)
        created.append(s)

    db.commit()
    return created
