# backend/schemas/clo_alignment.py

from pydantic import BaseModel
from typing import Dict, Any, List


class AssessmentItem(BaseModel):
    name: str


class BestAssessment(BaseModel):
    question: str
    score: float
    passed: bool


class CLOAlignmentItem(BaseModel):
    best_assessment: BestAssessment
    score: float
    passed: bool


class CLOAlignmentResponse(BaseModel):
    alignment: Dict[str, CLOAlignmentItem]
    avg_top: float
    flags: List[str]
    pairs: List[Dict[str, Any]] | None = None
    audit: Dict[str, Any] | None = None


class CLOAlignmentRequest(BaseModel):
    clos: List[str]
    assessments: List[AssessmentItem]
    threshold: float | None = 0.65


class CLOAlignmentAutoResponse(BaseModel):
    clos: List[str]
    assessments: List[str]
    alignment: Dict[str, Any]
