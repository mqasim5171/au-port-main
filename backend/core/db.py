# backend/core/db.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.base import Base  # ✅ single source of truth

# --- Load .env from the backend directory ---
try:
    from dotenv import load_dotenv
    BACKEND_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(BACKEND_DIR / ".env")
except Exception:
    pass

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set. Ensure backend/.env exists.")

connect_args = {}
if DB_URL.startswith("postgresql+"):
    connect_args["sslmode"] = "require"

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
