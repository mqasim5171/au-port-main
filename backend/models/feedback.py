from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime
from core.base import Base

def gen_id() -> str:
    return str(uuid.uuid4())

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    course_id: Mapped[str] = mapped_column(String(36))
    student_name: Mapped[str] = mapped_column(String(255))
    feedback_text: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer)
    sentiment: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
