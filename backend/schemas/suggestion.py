# backend/schemas/suggestion.py
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Literal

SuggestionStatus = Literal["new", "in_progress", "implemented", "ignored"]
SuggestionPriority = Literal["low", "medium", "high"]
SuggestionSource = Literal["quality_engine", "qec_manual"]
ActionType = Literal["comment", "status_change", "evidence_added"]

class SuggestionCreate(BaseModel):
    owner_id: str
    text: str
    priority: SuggestionPriority = "medium"
    source: SuggestionSource = "qec_manual"

class SuggestionUpdate(BaseModel):
    status: Optional[SuggestionStatus] = None
    priority: Optional[SuggestionPriority] = None
    text: Optional[str] = None

class SuggestionOut(BaseModel):
    id: str
    course_id: str
    owner_id: str
    source: str
    text: str
    status: str
    priority: str
    created_at: datetime

    class Config:
        orm_mode = True

class ActionCreate(BaseModel):
    action_type: ActionType
    notes: Optional[str] = ""
    evidence_url: Optional[str] = None

class ActionOut(BaseModel):
    id: str
    user_id: str
    action_type: str
    notes: str
    evidence_url: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

class SuggestionDetailOut(SuggestionOut):
    actions: List[ActionOut] = []
