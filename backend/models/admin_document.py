import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Integer, DateTime

from core.base import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class AdminDocument(Base):
    __tablename__ = "admin_documents"

    id = Column(String(36), primary_key=True, default=gen_id)

    title = Column(String(255), nullable=False)
    category = Column(String(100), index=True, nullable=False)

    description = Column(Text, nullable=True)

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content_type = Column(String(150), nullable=True)

    version = Column(Integer, default=1)

    uploaded_by = Column(String(36), nullable=True)
    uploaded_by_name = Column(String(255), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )