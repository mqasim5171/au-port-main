# backend/models/suggestion.py
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, Index

from core.base import Base

def gen_id() -> str:
    return str(uuid.uuid4())

SUGGESTION_STATUS = ("new", "in_progress", "implemented", "ignored")
SUGGESTION_PRIORITY = ("low", "medium", "high")
SUGGESTION_SOURCE = ("quality_engine", "qec_manual")

class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    course_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    source: Mapped[str] = mapped_column(
        Enum(*SUGGESTION_SOURCE, name="suggestion_source"),
        nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        Enum(*SUGGESTION_STATUS, name="suggestion_status"),
        default="new",
        nullable=False
    )
    priority: Mapped[str] = mapped_column(
        Enum(*SUGGESTION_PRIORITY, name="suggestion_priority"),
        default="medium",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    actions = relationship(
        "SuggestionAction",
        back_populates="suggestion",
        cascade="all, delete-orphan"
    )


ACTION_TYPE = ("comment", "status_change", "evidence_added")

class SuggestionAction(Base):
    __tablename__ = "suggestion_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    suggestion_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("suggestions.id", ondelete="CASCADE"),
        index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True)

    action_type: Mapped[str] = mapped_column(
        Enum(*ACTION_TYPE, name="suggestion_action_type"),
        nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    evidence_url: Mapped[str | None] = mapped_column(String(1000))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    suggestion = relationship("Suggestion", back_populates="actions")
