from fastapi import APIRouter
from sqlalchemy import text
from core.db import engine

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/db")
def db_health():
    with engine.connect() as conn:
        version = conn.execute(text("select version()")).scalar_one()
    return {"ok": True, "version": version}
