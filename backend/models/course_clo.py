"""Course CLO upload record.

IMPORTANT:
Your Course model uses `id` as String(36). The original CourseCLO model used UUID
for course_id/user_id, which breaks inserts/queries throughout the project.

This model is used as a *CLO upload/parse record* (file + parsed text + extracted CLO lines).
The system uses `clos_text` (newline-separated) for alignment.
"""

import uuid
import datetime

from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.base import Base
from .associations import assessment_clos


class CourseCLO(Base):
    __tablename__ = "course_clos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Must match Course.id type
    course_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)

    filename = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    parsed_text = Column(Text, nullable=True)
    clos_text = Column(Text, nullable=True)  # newline-separated CLOs
    file_path = Column(Text, nullable=True)

    assessments = relationship(
        "Assessment",
        secondary=assessment_clos,
        back_populates="clos",
        lazy="selectin",
    )
