from pydantic import BaseModel
from typing import Optional

class StudentFeedbackBase(BaseModel):
    student_id: Optional[str]
    name: Optional[str]
    form_type: Optional[str]
    mcq_number: Optional[int]
    answer: Optional[str]
    instructor_name: Optional[str]
    course_name: Optional[str]
    comments: Optional[str]
    sentiment: Optional[str]
    emotion: Optional[str]
    topic: Optional[int]
    batch: Optional[int]

class StudentFeedbackOut(StudentFeedbackBase):
    id: int

    class Config:
        orm_mode = True
