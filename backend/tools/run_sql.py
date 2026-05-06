# tools/run_sql.py

from sqlalchemy import text
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import engine

SQL = """
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  username VARCHAR(150) NOT NULL UNIQUE,
  email VARCHAR(320) NOT NULL UNIQUE,
  full_name VARCHAR(255),
  role VARCHAR(50),
  department VARCHAR(100),
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

with engine.begin() as conn:
    conn.execute(text(SQL))
print("users table ensured.")
