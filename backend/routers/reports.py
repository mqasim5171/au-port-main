from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json
from core.rbac import require_roles

from core.db import SessionLocal
from routers.auth import get_current_user

from models.course import Course
from models.completeness import CompletenessRun
from models.quality import QualityScore
from models.uploads import Upload
from models.assessment import Assessment, AssessmentCLOAlignment
from models.course_clo import CourseCLO


router = APIRouter(prefix="/courses", tags=["Reports"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _latest_quality(db: Session, course_id: str):
    return (
        db.query(QualityScore)
        .filter(QualityScore.course_id == course_id)
        .order_by(QualityScore.created_at.desc())
        .first()
    )


def _latest_completeness(db: Session, course_id: str):
    return (
        db.query(CompletenessRun)
        .filter(CompletenessRun.course_id == course_id)
        .order_by(CompletenessRun.created_at.desc())
        .first()
    )


@router.get("/{course_id}/qa-report", response_class=HTMLResponse)
def generate_qa_report(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin", "qec", "hod", "course_lead")),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    quality = _latest_quality(db, course_id)
    completeness = _latest_completeness(db, course_id)

    uploads_count = db.query(Upload).filter(Upload.course_id == course_id).count()
    assessments = db.query(Assessment).filter(Assessment.course_id == course_id).all()
    clo_records = db.query(CourseCLO).filter(CourseCLO.course_id == course_id).all()

    alignment_rows = (
        db.query(AssessmentCLOAlignment)
        .join(Assessment, Assessment.id == AssessmentCLOAlignment.assessment_id)
        .filter(Assessment.course_id == course_id)
        .all()
    )

    avg_alignment = 0
    if alignment_rows:
        avg_alignment = round(
            sum(float(a.coverage_percent or 0) for a in alignment_rows) / len(alignment_rows),
            2,
        )

    quality_suggestions = []
    if quality and quality.suggestions:
        try:
            quality_suggestions = json.loads(quality.suggestions)
        except Exception:
            quality_suggestions = [quality.suggestions]

    completeness_json = completeness.result_json if completeness else {}
    missing_items = completeness_json.get("missing", []) if completeness_json else []

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>QA Report - {course.course_code}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f3f6fb;
                color: #172033;
                padding: 32px;
            }}
            .report {{
                max-width: 950px;
                margin: auto;
                background: #ffffff;
                padding: 36px;
                border-radius: 18px;
                box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08);
            }}
            h1 {{
                margin: 0;
                color: #0f2f57;
                font-size: 30px;
            }}
            h2 {{
                color: #0f2f57;
                margin-top: 32px;
                border-bottom: 1px solid #e5e7eb;
                padding-bottom: 8px;
            }}
            .subtitle {{
                color: #64748b;
                margin-top: 6px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 14px;
                margin-top: 24px;
            }}
            .card {{
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 18px;
            }}
            .label {{
                font-size: 13px;
                color: #64748b;
            }}
            .value {{
                font-size: 24px;
                font-weight: bold;
                color: #0f2f57;
                margin-top: 8px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 12px;
            }}
            th, td {{
                border: 1px solid #e5e7eb;
                padding: 10px;
                text-align: left;
            }}
            th {{
                background: #f1f5f9;
            }}
            .badge {{
                display: inline-block;
                padding: 5px 10px;
                border-radius: 999px;
                background: #e0f2fe;
                color: #075985;
                font-size: 12px;
                font-weight: bold;
            }}
            .missing {{
                color: #b91c1c;
            }}
            .footer {{
                margin-top: 40px;
                color: #64748b;
                font-size: 13px;
            }}
            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}
                .report {{
                    box-shadow: none;
                    border-radius: 0;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="report">
            <h1>Academic QA Report</h1>
            <p class="subtitle">
                Generated on {datetime.utcnow().strftime("%d %B %Y, %I:%M %p")} UTC
            </p>

            <h2>Course Information</h2>
            <table>
                <tr><th>Course Code</th><td>{getattr(course, "course_code", "N/A")}</td></tr>
                <tr><th>Course Name</th><td>{getattr(course, "course_name", "N/A")}</td></tr>
                <tr><th>Course ID</th><td>{course.id}</td></tr>
            </table>

            <h2>QA Score Summary</h2>
            <div class="grid">
                <div class="card">
                    <div class="label">Overall</div>
                    <div class="value">{round(float(quality.overall_score), 2) if quality else 0}%</div>
                </div>
                <div class="card">
                    <div class="label">Completeness</div>
                    <div class="value">{round(float(quality.completeness_score), 2) if quality else 0}%</div>
                </div>
                <div class="card">
                    <div class="label">CLO Alignment</div>
                    <div class="value">{round(float(quality.alignment_score), 2) if quality else avg_alignment}%</div>
                </div>
                <div class="card">
                    <div class="label">Feedback</div>
                    <div class="value">{round(float(quality.feedback_score), 2) if quality else 0}%</div>
                </div>
            </div>

            <h2>Module Evidence</h2>
            <table>
                <tr><th>Total Uploads</th><td>{uploads_count}</td></tr>
                <tr><th>CLO Upload Records</th><td>{len(clo_records)}</td></tr>
                <tr><th>Assessments</th><td>{len(assessments)}</td></tr>
                <tr><th>AI Alignment Runs</th><td>{len(alignment_rows)}</td></tr>
            </table>

            <h2>Completeness Result</h2>
            <p>
                <span class="badge">
                    Score: {completeness_json.get("score_percent", 0) if completeness_json else 0}%
                </span>
            </p>
            {
                "<p>No missing items were detected in the latest completeness check.</p>"
                if not missing_items
                else "<ul>" + "".join([f"<li class='missing'>{m}</li>" for m in missing_items]) + "</ul>"
            }

            <h2>Assessments</h2>
            {
                "<p>No assessments have been uploaded yet.</p>"
                if not assessments
                else "<table><tr><th>Title</th><th>Type</th><th>Marks</th><th>Weightage</th></tr>"
                + "".join([
                    f"<tr><td>{a.title}</td><td>{a.type}</td><td>{a.max_marks}</td><td>{a.weightage}%</td></tr>"
                    for a in assessments
                ])
                + "</table>"
            }

            <h2>Improvement Suggestions</h2>
            {
                "<p>No suggestions available. Recompute quality score first.</p>"
                if not quality_suggestions
                else "<ul>" + "".join([f"<li>{s}</li>" for s in quality_suggestions]) + "</ul>"
            }

            <div class="footer">
                This report was generated automatically by the Air QA Portal.
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html)