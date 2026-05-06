from pydantic import BaseModel

class CourseCreate(BaseModel):
    course_code: str
    course_name: str
    semester: str
    year: str
    instructor: str
    department: str
    clos: str  # JSON string for now

class CourseOut(BaseModel):
    id: str
    course_code: str
    course_name: str
    semester: str
    year: str
    instructor: str
    department: str
    clos: str

    class Config:
        from_attributes = True
