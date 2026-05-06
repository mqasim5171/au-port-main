# schemas/clo.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CLOItem(BaseModel):
    id: str
    filename: str
    upload_date: datetime
    clos: List[str] = []

class CLOUploadResponse(BaseModel):
    id: str
    filename: str
    upload_date: datetime
    message: str = "CLO uploaded and parsed"
