# tools/migrate_users_to_uuid.py
import os, sys
from sqlalchemy import text
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.db import engine

SQL = """
BEGIN;

-- create table if it doesn't exist (varchar id)
CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(36) PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  full_name VARCHAR(255),
  role VARCHAR(50),
  department VARCHAR(100),
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- if table exists but id is integer/identity, normalize it to varchar(36)

-- 1) drop default/identity if present
DO $$
DECLARE
  coldef text;
BEGIN
  SELECT pg_get_expr(adbin, adrelid) INTO coldef
  FROM pg_attrdef
  WHERE adrelid = 'users'::regclass
    AND adnum = (SELECT attnum FROM pg_attribute WHERE attrelid = 'users'::regclass AND attname = 'id');

  -- Try drop identity; if it wasn't identity, ignore error
  BEGIN
    EXECUTE 'ALTER TABLE users ALTER COLUMN id DROP IDENTITY';
  EXCEPTION WHEN others THEN
    NULL;
  END;

  -- Drop DEFAULT if any
  BEGIN
    EXECUTE 'ALTER TABLE users ALTER COLUMN id DROP DEFAULT';
  EXCEPTION WHEN others THEN
    NULL;
  END;
END$$;

-- 2) drop PK temporarily (re-add later)
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_pkey;

-- 3) change type to varchar(36) (from integer if needed)
ALTER TABLE users ALTER COLUMN id TYPE VARCHAR(36);

-- 4) ensure NOT NULL + PK
ALTER TABLE users ALTER COLUMN id SET NOT NULL;
ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);

COMMIT;
"""

CHECK = """
SELECT data_type, is_nullable, character_maximum_length
FROM information_schema.columns
WHERE table_name='users' AND column_name='id';
"""

with engine.begin() as conn:
    conn.execute(text(SQL))
    row = conn.execute(text(CHECK)).mappings().first()
    print("users.id =>", dict(row) if row else "NOT FOUND")
