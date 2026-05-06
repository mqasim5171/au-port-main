# backend/models/student.py
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from core.base import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    reg_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    program: Mapped[str] = mapped_column(String(50))
    section: Mapped[str] = mapped_column(String(50))

    # ✅ link to submissions
    submissions = relationship(
        "StudentSubmission",
        back_populates="student",
        cascade="all, delete-orphan",
    )
