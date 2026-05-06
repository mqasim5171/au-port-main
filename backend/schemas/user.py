from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: str = "teacher"
    department: str | None = None
    password: str

class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: str
    role: str
    department: str | None

    class Config:
        from_attributes = True
