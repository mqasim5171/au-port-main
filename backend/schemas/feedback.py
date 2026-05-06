from pydantic import BaseModel

class FeedbackIn(BaseModel):
    course_id: str
    student_name: str
    feedback_text: str
    rating: int

class FeedbackOut(BaseModel):
    id: str
    course_id: str
    student_name: str
    feedback_text: str
    rating: int
    sentiment: str

    class Config:
        from_attributes = True
