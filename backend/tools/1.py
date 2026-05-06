import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import engine
from sqlalchemy import text

print("🚀 Connecting to DB...")
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE student_feedback ADD COLUMN IF NOT EXISTS batch BIGINT;"))
    print("✅ batch column added (BIGINT)")
print("🎉 Script finished")
