from sqlalchemy import Column, Integer, String, Text
from core.db import Base

class StudentFeedback(Base):
    __tablename__ = "student_feedback"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), index=True)
    name = Column(Text)
    form_type = Column(Text)
    mcq_number = Column(Integer)
    answer = Column(Text)
    instructor_name = Column(Text, index=True)
    course_name = Column(Text, index=True)
    comments = Column(Text)
    sentiment = Column(String(20), index=True)
    emotion = Column(String(50))
    topic = Column(Integer)
    batch = Column(Integer, index=True)
    department = Column(String(20), index=True)
