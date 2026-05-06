from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import SessionLocal
from models.user import User
from schemas.user import UserOut
from .auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current=Depends(get_current_user)):
    # add admin check if needed: if not current.is_admin: raise HTTPException(403, "Forbidden")
    return db.query(User).limit(100).all()
