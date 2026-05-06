# backend/schemas/course_execution.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ---------- WEEKLY PLAN ----------

class WeeklyPlanBase(BaseModel):
    week_number: int
    planned_topics: Optional[str] = None
    planned_assessments: Optional[str] = None
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None


class WeeklyPlanCreate(WeeklyPlanBase):
    pass


class WeeklyPlanUpdate(BaseModel):
    planned_topics: Optional[str] = None
    planned_assessments: Optional[str] = None
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None


class WeeklyPlanOut(WeeklyPlanBase):
    id: str
    course_id: str

    class Config:
        from_attributes = True


# ---------- WEEKLY EXECUTION ----------

class WeeklyExecutionBase(BaseModel):
    week_number: int
    delivered_topics: Optional[str] = None
    delivered_assessments: Optional[str] = None
    coverage_status: Optional[str] = "on_track"
    evidence_links: Optional[str] = None

    # ✅ NEW
    coverage_percent: Optional[float] = 0
    missing_topics: Optional[str] = None
    matched_topics: Optional[str] = None



class WeeklyExecutionCreate(WeeklyExecutionBase):
    pass


class WeeklyExecutionOut(WeeklyExecutionBase):
    id: str
    course_id: str
    last_updated_at: datetime

    class Config:
        from_attributes = True


# ---------- DEVIATION LOG ----------

class DeviationOut(BaseModel):
    id: str
    course_id: str
    week_number: int
    type: str
    details: Optional[str]
    created_at: datetime
    resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]

    class Config:
        from_attributes = True


class DeviationResolve(BaseModel):
    resolved: bool = True


# ---------- STATUS SUMMARY ----------

class WeeklyStatusItem(BaseModel):
    week_number: int
    planned_topics: Optional[str]
    delivered_topics: Optional[str]
    planned_assessments: Optional[str]
    delivered_assessments: Optional[str]
    coverage_status: str


class WeeklyStatusSummary(BaseModel):
    course_id: str
    items: List[WeeklyStatusItem]
