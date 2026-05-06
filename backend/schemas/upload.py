from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class UploadItem(BaseModel):
    id: str
    filename_original: str
    filename_stored: str
    ext: str
    file_type_guess: Optional[str] = None
    week_no: Optional[int] = None
    bytes: int
    pages: Optional[int] = None
    version: int = 1

class UploadResponse(BaseModel):
    files: List[UploadItem]
    log: List[Dict[str, Any]]
