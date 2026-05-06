-- =========================
-- 0) Upload storage metadata (Drive/local)
-- =========================
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS storage_backend varchar(16) DEFAULT 'local';
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS storage_key text;
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS storage_url text;

-- Store per-file details for ZIP-expanded uploads
CREATE TABLE IF NOT EXISTS upload_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  upload_id uuid NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
  filename text NOT NULL,
  ext varchar(16) NOT NULL,
  bytes integer NOT NULL DEFAULT 0,
  pages integer NULL,
  text_chars integer NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- 1) Completeness rules + runs
-- =========================
CREATE TABLE IF NOT EXISTS required_artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scope varchar(32) NOT NULL,     -- e.g. course_folder, weekly_folder
  name varchar(64) NOT NULL,      -- e.g. quizzes, assignments, midterm
  patterns jsonb NULL,            -- filename patterns list
  keywords jsonb NULL,            -- content keywords list
  weight numeric NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS completeness_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id varchar(36) NOT NULL,
  upload_id uuid NULL REFERENCES uploads(id) ON DELETE SET NULL,
  week_no integer NULL,
  result_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================
-- 2) FIX CLO model (your current course_clos table is wrong type-wise)
--    Fastest FYP approach: reset CLO tables (safe if you don't care about old CLO data)
-- =========================
DROP TABLE IF EXISTS assessment_clos;
DROP TABLE IF EXISTS course_clos;
DROP TABLE IF EXISTS course_clo_uploads;

CREATE TABLE course_clo_uploads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id varchar(36) NOT NULL,
  uploaded_by varchar(36) NULL,
  filename_original text NOT NULL,
  filename_stored text NOT NULL,
  storage_backend varchar(16) NOT NULL DEFAULT 'local',
  storage_key text NULL,
  storage_url text NULL,
  bytes integer NOT NULL DEFAULT 0,
  parsed_text text NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE course_clos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id varchar(36) NOT NULL,
  code varchar(50) NOT NULL,
  description text NOT NULL,
  bloom_level varchar(20) NULL,
  source_upload_id uuid NULL REFERENCES course_clo_uploads(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(course_id, code)
);

CREATE TABLE assessment_clos (
  assessment_id uuid NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  clo_id uuid NOT NULL REFERENCES course_clos(id) ON DELETE CASCADE,
  PRIMARY KEY (assessment_id, clo_id)
);
