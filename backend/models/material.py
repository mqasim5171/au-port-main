# models/material.py
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from core.base import Base

def gen_id() -> str:
    return str(uuid.uuid4())


class CourseMaterial(Base): 
    __tablename__ = "course_materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)

    # IMPORTANT: link to courses.id so SQLAlchemy can join Course ↔ CourseMaterial
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id"),
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    folder_type: Mapped[str] = mapped_column(
        String(50)
    )  # "assignments" | "quizzes" | "midterm" | "finalterm"
    created_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Back-reference to Course (matches Course.materials)
    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="materials",
    )

    # One-to-many: material → files
    files: Mapped[list["CourseMaterialFile"]] = relationship(
        "CourseMaterialFile",
        back_populates="material",
        cascade="all, delete-orphan",
    )


class CourseMaterialFile(Base):
    __tablename__ = "course_material_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_id)
    material_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("course_materials.id"),
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))  # relative path on disk
    content_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    material: Mapped[CourseMaterial] = relationship(
        "CourseMaterial",
        back_populates="files",
    )
