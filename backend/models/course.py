# backend/models/course.py
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base
from sqlalchemy import Column, String, Integer, Text ,DateTime


def gen_id() -> str:
    return str(uuid.uuid4())

class Course(Base):
    __tablename__ = "courses"

    course_guide_path = Column(String(255), nullable=True)
    course_guide_text = Column(Text, nullable=True)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    course_code: Mapped[str] = mapped_column(String(50))
    course_name: Mapped[str] = mapped_column(String(255))
    semester: Mapped[str] = mapped_column(String(32))
    year: Mapped[str] = mapped_column(String(16))
    instructor: Mapped[str] = mapped_column(String(255))
    department: Mapped[str] = mapped_column(String(255))

    # Optional JSON string (CLOs)
    clos: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # NEW — connect course → materials (Assignments, Quizzes, Midterm, Finalterm)
    materials: Mapped[list["CourseMaterial"]] = relationship(
        "CourseMaterial",
        back_populates="course",
        cascade="all, delete-orphan"
    )
