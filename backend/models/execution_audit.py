import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from core.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class ExecutionAudit(Base):
    __tablename__ = "execution_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(String(36), nullable=False, index=True)
    week_no = Column(Integer, nullable=False)
    upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"))
    coverage_percent = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    audit_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
