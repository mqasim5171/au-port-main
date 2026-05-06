# backend/models/course_clo_upload.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from core.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class CourseCLOUpload(Base):
    __tablename__ = "course_clo_uploads"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(String(36), nullable=False, index=True)
    uploaded_by = Column(String(36), nullable=True, index=True)

    filename_original = Column(Text, nullable=False)
    filename_stored = Column(Text, nullable=False)

    storage_backend = Column(String(16), nullable=False, default="local")
    storage_key = Column(Text, nullable=True)
    storage_url = Column(Text, nullable=True)

    bytes = Column(Integer, nullable=False, default=0)
    parsed_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
