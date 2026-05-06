# backend/models/student_submission.py
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Float, Text, func, text as sql_text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base


class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    # DB: varchar(36)
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # DB: uuid
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # DB: varchar(36)
    student_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # DB: varchar(255) nullable (legacy)
    file_upload_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # DB: integer nullable
    obtained_marks: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # DB: varchar(36) nullable
    grader_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # DB: timestamptz NOT NULL default now()
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # DB: uuid NULL fk uploads(id)
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="SET NULL"),
        nullable=True,
    )

    # DB: varchar(32) NOT NULL default 'uploaded'
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=sql_text("'uploaded'"),
        default="uploaded",
    )

    # DB: double precision nullable
    ai_marks: Mapped[float | None] = mapped_column(Float, nullable=True)

    # DB: text nullable
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # DB: jsonb nullable
    evidence_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # relationships
    assessment = relationship("Assessment", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")

    # ✅ NEW: lets us read upload.filename_original easily in API
    upload = relationship("Upload", foreign_keys=[upload_id], lazy="joined")

    # ✅ computed fields for API (no DB migration needed)
    @property
    def roll_no(self) -> str | None:
        return getattr(self.student, "reg_no", None) if self.student else None

    @property
    def student_name(self) -> str | None:
        return getattr(self.student, "name", None) if self.student else None

    @property
    def filename_original(self) -> str | None:
        return getattr(self.upload, "filename_original", None) if self.upload else None
