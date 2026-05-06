# backend/models/completeness.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
from core.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class RequiredArtifact(Base):
    __tablename__ = "required_artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(String(32), nullable=False)
    name = Column(String(64), nullable=False)
    patterns = Column(JSONB, nullable=True)
    keywords = Column(JSONB, nullable=True)
    weight = Column(Numeric, nullable=False, default=1)

class CompletenessRun(Base):
    __tablename__ = "completeness_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(String(36), nullable=False, index=True)
    upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True)
    week_no = Column(Integer, nullable=True)
    result_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
