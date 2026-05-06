import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Text, DateTime
from core.base import Base


def gen_id():
    return str(uuid.uuid4())


class ManualOverride(Base):
    __tablename__ = "manual_overrides"

    id = Column(String, primary_key=True, default=gen_id)

    course_id = Column(String, index=True)
    module = Column(String)  # completeness / quality

    original_score = Column(Float)
    overridden_score = Column(Float)

    reason = Column(Text)

    created_by = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))