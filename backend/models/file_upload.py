from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime
from core.base import Base

def gen_id() -> str:
    return str(uuid.uuid4())

class FileUpload(Base):
    __tablename__ = "file_uploads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    course_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(String(36))
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)
    validation_status: Mapped[str] = mapped_column(String(255))
    validation_details: Mapped[str] = mapped_column(Text)  # JSON string
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
