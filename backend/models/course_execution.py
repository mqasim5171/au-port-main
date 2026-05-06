# backend/models/course_execution.py
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy import Column, String, Integer, DateTime, Text, Float, ForeignKey

from core.base import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    week_number: Mapped[int] = mapped_column(Integer, index=True)

    # plain text or JSON-encoded list; keep it simple text for now
    planned_topics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    planned_assessments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    planned_start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WeeklyExecution(Base):
    __tablename__ = "weekly_executions"

    coverage_percent = Column(Float, nullable=False, default=0)
    missing_topics = Column(Text, nullable=True)
    matched_topics = Column(Text, nullable=True)


    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    week_number: Mapped[int] = mapped_column(Integer, index=True)

    delivered_topics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivered_assessments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # on_track, behind, ahead, skipped
    coverage_status: Mapped[str] = mapped_column(String(32), default="on_track", index=True)

    # store JSON string of upload IDs or folder IDs, e.g. '["uuid1", "uuid2"]'
    evidence_links: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class DeviationLog(Base):
    __tablename__ = "deviation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    week_number: Mapped[int] = mapped_column(Integer, index=True)

    # missing_content, late_delivery, topic_change, etc.
    type: Mapped[str] = mapped_column(String(50), index=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
