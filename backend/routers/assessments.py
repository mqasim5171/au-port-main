# backend/routers/assessments.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload

from typing import List
import uuid

from core.db import SessionLocal
from routers.auth import get_current_user

from models.course import Course
from models.course_staff import CourseStaff
from models.assessment import Assessment, AssessmentFile
from models.student_submission import StudentSubmission
from models.uploads import Upload, UploadText

from schemas.assessment import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentDetailOut,
    SubmissionOut,
)

from services.assessment_service import (
    create_assessment,
    save_questions_file_and_extract_text,
    ai_generate_expected_answers,
    ai_clo_alignment,
)

from services.grading_service import (
    upload_submissions_zip,
    upload_single_submission_file,
    grade_all,
)


router = APIRouter(tags=["Assessments"])


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ======================================================
# ACCESS HELPERS
# ======================================================

ROLE_ALIASES = {
    "administrator": "admin",
    "superadmin": "admin",
    "course lead": "course_lead",
    "faculty member": "faculty",
    "instructor": "faculty",
    "qec officer": "qec",
    "quality officer": "qec",
}


def _uid(current) -> str:
    if isinstance(current, dict):
        return str(current.get("id") or "")

    return str(getattr(current, "id", "") or "")


def _role(current) -> str:
    if isinstance(current, dict):
        raw = current.get("role") or ""
    else:
        raw = getattr(current, "role", "") or ""

    r = str(raw).strip().lower()

    return ROLE_ALIASES.get(r, r)


def _is_teacher_role(current) -> bool:
    return _role(current) in {"course_lead", "faculty"}


def _validate_uuid_string(value: str, field_name: str):
    try:
        return uuid.UUID(value)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}",
        )


def _ensure_course_exists(db: Session, course_id: str) -> Course:
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return course


def _ensure_assigned_course_staff(db: Session, course_id: str, current):
    """
    Assessment creation, question upload, ZIP submission upload, and grading
    are teacher/course staff actions.

    Allowed:
    - assigned Course Lead
    - assigned Faculty/Instructor

    Not allowed:
    - admin
    - qec
    - hod
    - unassigned teacher
    """
    _ensure_course_exists(db, course_id)

    if not _is_teacher_role(current):
        raise HTTPException(
            status_code=403,
            detail="Only assigned course staff can access assessments.",
        )

    row = (
        db.query(CourseStaff)
        .filter(
            CourseStaff.course_id == course_id,
            CourseStaff.user_id == _uid(current),
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this course.",
        )


def _get_assessment_or_404(db: Session, assessment_id: str) -> Assessment:
    aid = _validate_uuid_string(assessment_id, "assessment_id")

    assessment = db.get(Assessment, aid)

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return assessment


def _ensure_assessment_access(db: Session, assessment: Assessment, current):
    _ensure_assigned_course_staff(db, str(assessment.course_id), current)


# ======================================================
# ASSESSMENT CRUD
# ======================================================

@router.post("/courses/{course_id}/assessments", response_model=AssessmentOut)
def create_assessment_api(
    course_id: str,
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    _validate_uuid_string(course_id, "course_id")
    _ensure_assigned_course_staff(db, course_id, current)

    assessment = create_assessment(
        db,
        course_id=course_id,
        payload=payload.model_dump(),
        created_by=_uid(current),
    )

    return assessment


@router.get("/courses/{course_id}/assessments", response_model=List[AssessmentOut])
def list_assessments(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    _validate_uuid_string(course_id, "course_id")
    _ensure_assigned_course_staff(db, course_id, current)

    return (
        db.query(Assessment)
        .filter(Assessment.course_id == course_id)
        .order_by(Assessment.created_at.desc())
        .all()
    )


@router.get("/assessments/{assessment_id}", response_model=AssessmentDetailOut)
def get_assessment_detail(
    assessment_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _ensure_assessment_access(db, assessment, current)

    return {
        "assessment": assessment,
        "files": list(assessment.files or []),
        "expected": assessment.expected,
        "clo_alignment": assessment.clo_alignment,
    }


# ======================================================
# QUESTIONS + EXPECTED ANSWERS
# ======================================================

@router.post("/assessments/{assessment_id}/questions/upload")
async def upload_questions_file(
    assessment_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _ensure_assessment_access(db, assessment, current)

    filename = file.filename or "questions.pdf"

    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX question files are allowed.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        assessment_file = save_questions_file_and_extract_text(
            db=db,
            assessment_id=assessment.id,
            course_id=assessment.course_id,
            file_bytes=file_bytes,
            filename=filename,
        )

        return {
            "ok": True,
            "message": "Question file uploaded and text extracted.",
            "assessment_file_id": str(assessment_file.id),
            "extracted_len": len(assessment_file.extracted_text or ""),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/assessments/{assessment_id}/questions/{file_id}")
def delete_question_file(
    assessment_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _ensure_assessment_access(db, assessment, current)

    fid = _validate_uuid_string(file_id, "file_id")

    assessment_file = (
        db.query(AssessmentFile)
        .filter(
            AssessmentFile.id == fid,
            AssessmentFile.assessment_id == assessment.id,
        )
        .first()
    )

    if not assessment_file:
        raise HTTPException(status_code=404, detail="Question file not found")

    upload_id = assessment_file.upload_id

    db.delete(assessment_file)

    if upload_id:
        upload_text = db.query(UploadText).filter(UploadText.upload_id == upload_id).first()
        if upload_text:
            db.delete(upload_text)

        upload = db.get(Upload, upload_id)
        if upload:
            db.delete(upload)

    db.commit()

    return {
        "ok": True,
        "message": "Question file deleted successfully.",
    }


@router.post("/assessments/{assessment_id}/generate-expected-answers")
def generate_expected_answers(
    assessment_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _ensure_assessment_access(db, assessment, current)

    try:
        expected = ai_generate_expected_answers(db, assessment)
        clo = ai_clo_alignment(db, assessment)

        return {
            "ok": True,
            "message": "Expected answers and CLO alignment generated.",
            "expected_answers_created": True,
            "model": expected.model,
            "prompt_version": expected.prompt_version,
            "clo_coverage_percent": clo.coverage_percent,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======================================================
# STUDENT SUBMISSIONS ZIP + SINGLE FILE + GRADING
# ======================================================

@router.post("/assessments/{assessment_id}/submissions/upload-zip")
async def upload_submissions(
    assessment_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _ensure_assessment_access(db, assessment, current)

    filename = file.filename or "submissions.zip"

    if not filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are allowed for bulk submissions.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty ZIP")

    try:
        result = upload_submissions_zip(
            db,
            assessment,
            file_bytes,
            filename,
        )

        return {
            "ok": True,
            "message": "ZIP extracted and submissions processed.",
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assessments/{assessment_id}/submissions/upload-file")
async def upload_single_submission(
    assessment_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _ensure_assessment_access(db, assessment, current)

    filename = file.filename or "submission.docx"

    if not filename.lower().endswith((".pdf", ".docx", ".txt", ".md")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, TXT, and MD files are allowed for student submissions.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = upload_single_submission_file(
            db=db,
            assessment=assessment,
            file_bytes=file_bytes,
            filename=filename,
        )

        return {
            "ok": True,
            "message": "Single submission uploaded successfully.",
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assessments/{assessment_id}/grade-all")
def grade_all_api(
    assessment_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _ensure_assessment_access(db, assessment, current)

    try:
        result = grade_all(
            db,
            assessment,
            created_by=_uid(current),
        )

        return {
            "ok": True,
            "message": "All submissions graded.",
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assessments/{assessment_id}/submissions", response_model=List[SubmissionOut])
def list_submissions(
    assessment_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _ensure_assessment_access(db, assessment, current)

    return (
        db.query(StudentSubmission)
        .options(
            joinedload(StudentSubmission.student),
            joinedload(StudentSubmission.upload),
        )
        .filter(StudentSubmission.assessment_id == assessment.id)
        .order_by(StudentSubmission.submitted_at.desc())
        .all()
    )