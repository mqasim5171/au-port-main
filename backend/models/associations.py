# backend/models/associations.py
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from core.base import Base

assessment_clos = Table(
    "assessment_clos",
    Base.metadata,
    Column(
        "assessment_id",
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "clo_id",
        UUID(as_uuid=True),
        ForeignKey("course_clos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
