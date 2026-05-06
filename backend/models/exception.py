import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from core.base import Base


def gen_id():
    return str(uuid.uuid4())


class ExceptionLog(Base):
    __tablename__ = "exception_logs"

    id = Column(String, primary_key=True, default=gen_id)

    course_id = Column(String, index=True, nullable=True)
    upload_id = Column(String, nullable=True)

    module = Column(String, nullable=False)  # upload, completeness, quality, parsing
    error_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    severity = Column(String, default="medium")  # low / medium / high / critical
    status = Column(String, default="open")  # open / resolved / ignored

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))