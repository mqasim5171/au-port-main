import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get DB URL from .env
raw_url = os.getenv("DATABASE_URL")

if not raw_url:
    raise ValueError("❌ DB_URL not found in environment variables.")

# Convert SQLAlchemy-style URL -> psycopg format
DB_URL = raw_url.replace("postgresql+psycopg://", "postgresql://")

def add_created_at_column():
    try:
        with psycopg.connect(DB_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Check if column already exists
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='quality_scores' AND column_name='created_at';
                """)
                result = cur.fetchone()

                if result:
                    print("✅ Column 'created_at' already exists.")
                else:
                    cur.execute("""
                        ALTER TABLE quality_scores 
                        ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
                    """)
                    conn.commit()
                    print("🎉 Column 'created_at' added successfully.")

    except Exception as e:
        print("❌ Error:", e)

if __name__ == "__main__":
    add_created_at_column()
