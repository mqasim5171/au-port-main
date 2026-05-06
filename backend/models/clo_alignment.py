# backend/models/clo_alignment.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from core.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class CLOAlignment(Base):
    __tablename__ = "clo_alignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(String(36), nullable=False, index=True)
    week_no = Column(Integer, nullable=True)

    avg_top = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)

    audit_json = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utcnow)
