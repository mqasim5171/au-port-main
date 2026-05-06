# backend/app.py

from dotenv import load_dotenv
load_dotenv()

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.schema_guard import ensure_all_tables_once

from routers import completeness
from routers import assessments
from routers import (
    auth,
    analytics,
    admin_documents,
    admin,
    users,
    exception,
    override,
    reminders,
    courses,
    uploads,
    feedback,
    quality,
    health,
    dashboard,
    clo_alignment,
    course_clo,
    student_feedback,
    course_execution,
    student_router,
    grading_audit_router,
    suggestions,
    course_lead,
    reports,
    # execution_zip,  # old duplicate router, not used currently
)

print("OPENROUTER_API_KEY loaded:", bool(os.getenv("OPENROUTER_API_KEY")))

app = FastAPI(title="Air QA Backend")


# --- CORS CONFIG ------------------------------------------------------------
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- ROUTERS ----------------------------------------------------------------
app.include_router(analytics.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(uploads.router)
app.include_router(feedback.router)
app.include_router(quality.router)
app.include_router(reports.router)
app.include_router(course_clo.router)
app.include_router(clo_alignment.router)
app.include_router(reminders.router)
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(exception.router)
app.include_router(student_feedback.router)
app.include_router(student_router.router)
app.include_router(grading_audit_router.router)
app.include_router(admin_documents.router)
app.include_router(completeness.router)

# Frontend uses non-/api assessment endpoints
app.include_router(assessments.router)
app.include_router(override.router)
# Official course execution router
# This already handles weekly ZIP upload through weekly_zip_upload_service.py
app.include_router(course_execution.router)

# Old duplicate weekly ZIP router disabled to avoid route conflict
# app.include_router(execution_zip.router)

# Suggestions router currently has its own prefix inside the router file
app.include_router(suggestions.router)

app.include_router(admin.router)
app.include_router(course_lead.router)


# --- STARTUP ----------------------------------------------------------------

@app.on_event("startup")
def _startup_schema():
    ensure_all_tables_once()