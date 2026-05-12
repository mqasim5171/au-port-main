# backend/services/grading_service.py

import json
import zipfile
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from models.uploads import Upload, UploadText
from models.assessment import Assessment, GradingRun, AssessmentExpectedAnswers
from models.student import Student
from models.student_submission import StudentSubmission

from services.upload_adapter import parse_document
from services.openrouter_client import call_openrouter_json


ALLOWED_SUB_EXTS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILES = 200

# Keep this lower for free AI models. Bigger text = slower grading.
MAX_TEXT = 20_000


def utcnow():
    return datetime.now(timezone.utc)


def clean_text(val: Optional[str]) -> str:
    if not val:
        return ""

    if not isinstance(val, str):
        val = str(val)

    val = val.replace("\x00", "")

    out = []

    for ch in val:
        o = ord(ch)

        if ch in ("\n", "\r", "\t"):
            out.append(ch)
        elif o >= 32:
            out.append(ch)

    return "".join(out).strip()


def _safe_extract_zip(zip_path: str, dest_dir: str) -> List[str]:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    out: List[str] = []

    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()

        if len(names) > MAX_FILES:
            names = names[:MAX_FILES]

        for member in names:
            if member.endswith("/"):
                continue

            target = (dest / member).resolve()

            # Zip-slip protection
            if not str(target).startswith(str(dest.resolve())):
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            with z.open(member) as src, open(target, "wb") as f:
                f.write(src.read())

            out.append(str(target))

    return out


def _infer_reg_no(filename: str) -> str:
    base = Path(filename).stem

    # Common patterns: BSCS-FA22-123, 21-CS-500, etc.
    m = re.search(
        r"([A-Za-z]{2,10}[-_ ]?[A-Za-z]{1,10}[-_ ]?\d{2,4}[-_ ]?\d{2,6})",
        base,
    )

    if m:
        return re.sub(r"[\s_]+", "-", m.group(1)).upper()

    m = re.search(r"([0-9]{2}[-_ ]?[A-Za-z]{2,}[-_ ]?[0-9]{2,})", base)

    if m:
        return re.sub(r"[\s_]+", "-", m.group(1)).upper()

    m2 = re.search(r"([0-9]{4,})", base)

    return (m2.group(1) if m2 else base[:40]).upper()


ROLL_TEXT_RE = re.compile(
    r"(student\s*roll\s*no|roll\s*no|registration\s*no|reg\s*no)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-_/]{3,})",
    re.IGNORECASE,
)

NAME_TEXT_RE = re.compile(
    r"(student\s*name)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)


def _extract_roll_and_name_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None

    roll = None
    name = None

    m = ROLL_TEXT_RE.search(text)

    if m:
        roll = (m.group(2) or "").strip()

    m2 = NAME_TEXT_RE.search(text)

    if m2:
        name = (m2.group(2) or "").strip()
        name = name.splitlines()[0].strip()

    if roll:
        roll = roll.replace("_", "-").replace(" ", "-").upper()

    return roll or None, name or None


def _save_submission_record(
    db: Session,
    assessment: Assessment,
    file_path: Path,
    file_bytes_len: int,
    filename: str,
    upload_type: str,
) -> Dict[str, Any]:
    ext = file_path.suffix.lower()

    if ext not in ALLOWED_SUB_EXTS:
        raise ValueError("Only PDF, DOCX, TXT, and MD files are allowed for student submissions.")

    parsed = parse_document(str(file_path)) or {}
    text = clean_text(parsed.get("text") or "")[:MAX_TEXT]

    if not text.strip():
        raise ValueError("Submission text is empty. The file could not be parsed.")

    roll_from_text, name_from_text = _extract_roll_and_name_from_text(text)
    reg_no = roll_from_text or _infer_reg_no(filename)

    student = db.query(Student).filter(Student.reg_no == reg_no).first()

    if not student:
        student = Student(
            reg_no=reg_no,
            name=(name_from_text or reg_no),
            program="N/A",
            section="N/A",
        )
        db.add(student)
        db.flush()
    else:
        if name_from_text and (student.name in (None, "", student.reg_no)):
            student.name = name_from_text
            db.add(student)

    up = Upload(
        course_id=str(assessment.course_id),
        filename_original=filename,
        filename_stored=filename,
        ext=ext.lstrip("."),
        file_type_guess="student_submission",
        week_no=None,
        bytes=file_bytes_len,
        parse_log=[],
        created_at=datetime.utcnow(),
    )
    db.add(up)
    db.flush()

    ut = UploadText(
        upload_id=up.id,
        text=text,
        text_chars=len(text),
        needs_ocr=False,
        parse_warnings=[],
    )
    db.add(ut)

    existing = (
        db.query(StudentSubmission)
        .filter(
            StudentSubmission.assessment_id == assessment.id,
            StudentSubmission.student_id == student.id,
        )
        .first()
    )

    ev = {
        "reg_no": reg_no,
        "student_name": name_from_text,
        "filename_original": filename,
        "upload_type": upload_type,
    }

    if existing:
        existing.upload_id = up.id
        existing.status = "uploaded"
        existing.ai_marks = None
        existing.ai_feedback = None
        existing.obtained_marks = None
        existing.grader_id = None
        existing.evidence_json = {**(existing.evidence_json or {}), **ev}
        existing.submitted_at = utcnow()
        db.add(existing)

        return {
            "created": 0,
            "updated": 1,
            "reg_no": reg_no,
            "filename": filename,
            "submission_id": str(existing.id),
            "text_chars": len(text),
        }

    submission = StudentSubmission(
        assessment_id=assessment.id,
        student_id=student.id,
        upload_id=up.id,
        status="uploaded",
        ai_marks=None,
        ai_feedback=None,
        obtained_marks=None,
        grader_id=None,
        evidence_json=ev,
        submitted_at=utcnow(),
    )
    db.add(submission)
    db.flush()

    return {
        "created": 1,
        "updated": 0,
        "reg_no": reg_no,
        "filename": filename,
        "submission_id": str(submission.id),
        "text_chars": len(text),
    }


def upload_submissions_zip(
    db: Session,
    assessment: Assessment,
    zip_bytes: bytes,
    zip_filename: str,
    storage_root: str = "uploads/submissions",
) -> Dict[str, Any]:
    now = utcnow()

    base_dir = (
        Path(storage_root)
        / str(assessment.course_id)
        / str(assessment.id)
        / str(int(now.timestamp() * 1000))
    )

    base_dir.mkdir(parents=True, exist_ok=True)

    zip_path = base_dir / (zip_filename or "submissions.zip")
    zip_path.write_bytes(zip_bytes)

    extracted_dir = base_dir / "extracted"
    files = _safe_extract_zip(str(zip_path), str(extracted_dir))

    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for fp in files:
        try:
            fp_path = Path(fp)
            ext = fp_path.suffix.lower()

            if ext not in ALLOWED_SUB_EXTS:
                skipped += 1
                continue

            result = _save_submission_record(
                db=db,
                assessment=assessment,
                file_path=fp_path,
                file_bytes_len=fp_path.stat().st_size if fp_path.exists() else 0,
                filename=fp_path.name,
                upload_type="zip",
            )

            created += int(result.get("created") or 0)
            updated += int(result.get("updated") or 0)

        except Exception as e:
            errors.append(f"{Path(fp).name}: {str(e)}")
            skipped += 1

    db.commit()

    return {
        "files_seen": len(files),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


def upload_single_submission_file(
    db: Session,
    assessment: Assessment,
    file_bytes: bytes,
    filename: str,
    storage_root: str = "uploads/submissions_single",
) -> Dict[str, Any]:
    now = utcnow()
    ext = (Path(filename).suffix or "").lower()

    if ext not in ALLOWED_SUB_EXTS:
        raise ValueError("Only PDF, DOCX, TXT, and MD files are allowed for student submissions.")

    base_dir = (
        Path(storage_root)
        / str(assessment.course_id)
        / str(assessment.id)
        / str(int(now.timestamp() * 1000))
    )

    base_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    stored_path = base_dir / safe_name
    stored_path.write_bytes(file_bytes)

    result = _save_submission_record(
        db=db,
        assessment=assessment,
        file_path=stored_path,
        file_bytes_len=len(file_bytes),
        filename=safe_name,
        upload_type="single_file",
    )

    db.commit()

    return result


def _load_grading_prompt() -> str:
    p = Path(__file__).resolve().parent / "ai_prompts" / "grading_v1.txt"

    if p.exists():
        return p.read_text(encoding="utf-8")

    return (
        "You are an examiner. Grade the student's submission against expected answers.\n"
        "Return JSON only following the given schema.\n"
        "Be strict but fair. Use MAX_MARKS.\n"
    )


def grade_all(
    db: Session,
    assessment: Assessment,
    created_by: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    exp = (
        db.query(AssessmentExpectedAnswers)
        .filter(AssessmentExpectedAnswers.assessment_id == assessment.id)
        .first()
    )

    if not exp or not exp.parsed_json:
        raise ValueError("Expected answers not generated. Run generate-expected-answers first.")

    # Only grade ungraded/error/uploaded submissions.
    # Already graded submissions are skipped to save time and API calls.
    subs = (
        db.query(StudentSubmission)
        .filter(
            StudentSubmission.assessment_id == assessment.id,
            StudentSubmission.status != "graded",
        )
        .order_by(StudentSubmission.submitted_at.asc())
        .all()
    )

    if not subs:
        return {
            "graded": 0,
            "failed": 0,
            "grading_run_id": None,
            "message": "No ungraded submissions found. All submissions are already graded.",
        }

    gr = GradingRun(
        assessment_id=assessment.id,
        model=model,
        prompt_version="v1",
        thresholds={"note": "strict but fair"},
        created_by=created_by,
        created_at=utcnow(),
        completed=False,
    )

    db.add(gr)
    db.commit()
    db.refresh(gr)

    system = _load_grading_prompt()

    schema_hint = json.dumps(
        {
            "total_marks": 0,
            "feedback": "string",
            "per_question": [
                {
                    "question_no": 1,
                    "marks_awarded": 0,
                    "justification": "string",
                    "missing_points": ["string"],
                }
            ],
        }
    )

    graded = 0
    failed = 0
    total_subs = len(subs)

    print(
        f"[GRADE_ALL] Started | assessment_id={assessment.id} | total_ungraded={total_subs}",
        flush=True,
    )

    for index, s in enumerate(subs, start=1):
        print(
            f"[GRADE_ALL] Starting submission {index}/{total_subs} | submission_id={s.id}",
            flush=True,
        )

        try:
            ut = None

            if s.upload_id:
                ut = db.query(UploadText).filter(UploadText.upload_id == s.upload_id).first()

            sub_text = clean_text((ut.text if ut else "") or "")[:MAX_TEXT]

            if not sub_text.strip():
                raise ValueError("Submission text is empty (parsing failed).")

            user = (
                f"ASSESSMENT_TITLE: {assessment.title}\n"
                f"MAX_MARKS: {assessment.max_marks}\n"
                f"EXPECTED_ANSWERS_JSON:\n{json.dumps(exp.parsed_json, ensure_ascii=False)}\n\n"
                f"STUDENT_SUBMISSION_TEXT:\n{sub_text}\n"
            )

            print(
                f"[GRADE_ALL] Calling AI for submission {index}/{total_subs} | text_chars={len(sub_text)}",
                flush=True,
            )

            parsed, meta = call_openrouter_json(
                system=system,
                user=user,
                schema_hint=schema_hint,
                model=model,
                temperature=0.2,
            )

            total = float(parsed.get("total_marks") or 0.0)
            feedback = str(parsed.get("feedback") or "")

            s.ai_marks = total
            s.obtained_marks = int(round(total))
            s.ai_feedback = feedback
            s.status = "graded"
            s.grader_id = created_by

            s.evidence_json = {
                **(s.evidence_json or {}),
                "grading_run_id": str(gr.id),
                "model": meta.get("model"),
                "prompt_version": "v1",
                "input_hash": meta.get("input_hash"),
                "latency_ms": meta.get("latency_ms"),
                "raw_response": meta.get("raw_response"),
                "parsed": parsed,
            }

            db.add(s)
            db.commit()

            graded += 1

            print(
                f"[GRADE_ALL] Finished submission {index}/{total_subs} | status=graded | marks={total}",
                flush=True,
            )

        except Exception as e:
            err_msg = str(e)

            s.ai_marks = 0
            s.obtained_marks = 0
            s.ai_feedback = f"Grading failed: {err_msg}"
            s.status = "error"
            s.evidence_json = {
                **(s.evidence_json or {}),
                "grading_run_id": str(gr.id),
                "error": err_msg,
            }

            db.add(s)
            db.commit()

            failed += 1

            print(
                f"[GRADE_ALL] Failed submission {index}/{total_subs} | error={err_msg}",
                flush=True,
            )

    gr.completed = True
    db.add(gr)
    db.commit()

    print(
        f"[GRADE_ALL] Completed | graded={graded} | failed={failed} | run_id={gr.id}",
        flush=True,
    )

    return {
        "graded": graded,
        "failed": failed,
        "grading_run_id": str(gr.id),
    }