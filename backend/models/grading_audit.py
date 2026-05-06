# models/grading_audit.py
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from core.base import Base

def gen_id() -> str:
    return str(uuid.uuid4())

class GradingAudit(Base):
    __tablename__ = "grading_audits"

    # keep string PK if you want
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)

    # ✅ MUST match assessments.id (UUID)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    assessment = relationship("Assessment")
