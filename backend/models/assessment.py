# backend/models/assessment.py

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.base import Base
from .associations import assessment_clos


def utcnow():
    return datetime.now(timezone.utc)


class Assessment(Base):
    __tablename__ = "assessments"

    # ✅ DB: uuid
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ✅ DB: character varying(36) referencing courses.id (varchar)
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # ✅ DB: character varying(36) (keep as varchar; don't FK unless users.id is uuid)
    created_by = Column(String(36), nullable=True, index=True)

    type = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)

    # ✅ DB column name: total_marks
    max_marks = Column("total_marks", Integer, nullable=False)

    weightage = Column(Integer, nullable=False)

    # ✅ DB column name: date_conducted (DATE)
    date = Column("date_conducted", Date, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # -------------------- Relationships --------------------

    files = relationship(
        "AssessmentFile",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    expected = relationship(
        "AssessmentExpectedAnswers",
        uselist=False,
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    clo_alignment = relationship(
        "AssessmentCLOAlignment",
        uselist=False,
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    submissions = relationship(
        "StudentSubmission",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    # ✅ many-to-many Assessment <-> CourseCLO via assessment_clos
    # DB: assessment_clos(assessment_id uuid, clo_id uuid)
    clos = relationship(
        "CourseCLO",
        secondary=assessment_clos,
        back_populates="assessments",
        lazy="selectin",
    )


class AssessmentFile(Base):
    __tablename__ = "assessment_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    assessment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # ✅ uploads.id is uuid (based on your FK you added for student_submissions.upload_id)
    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="SET NULL"),
        nullable=True,
    )

    filename_original = Column(String, nullable=False)
    filename_stored = Column(String, nullable=False)
    ext = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    extracted_text = Column(Text, nullable=True)

    assessment = relationship("Assessment", back_populates="files")


class AssessmentExpectedAnswers(Base):
    __tablename__ = "assessment_expected_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    assessment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    prompt_version = Column(String, default="v1")
    model = Column(String, nullable=True)
    input_hash = Column(String, index=True, nullable=True)

    raw_response = Column(Text, nullable=True)
    parsed_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    assessment = relationship("Assessment", back_populates="expected")


class AssessmentCLOAlignment(Base):
    __tablename__ = "assessment_clo_alignment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    assessment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # ✅ DB stores int 0..100
    coverage_percent = Column(Integer, default=0)

    per_clo = Column(JSONB, nullable=True)
    per_question = Column(JSONB, nullable=True)

    model = Column(String, nullable=True)
    prompt_version = Column(String, default="v1")

    created_at = Column(DateTime(timezone=True), default=utcnow)

    assessment = relationship("Assessment", back_populates="clo_alignment")


class GradingRun(Base):
    __tablename__ = "grading_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    assessment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    model = Column(String, nullable=True)
    prompt_version = Column(String, default="v1")
    thresholds = Column(JSONB, nullable=True)

    # ✅ keep varchar unless your DB column is uuid
    created_by = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    completed = Column(Boolean, default=False)
