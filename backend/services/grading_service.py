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
MAX_TEXT = 80_000


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
            # zip-slip protection
            if not str(target).startswith(str(dest.resolve())):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as f:
                f.write(src.read())
            out.append(str(target))
    return out


def _infer_reg_no(filename: str) -> str:
    base = Path(filename).stem

    # common patterns: BSCS-FA22-123, 21-CS-500, etc
    m = re.search(r"([A-Za-z]{2,10}[-_ ]?[A-Za-z]{1,10}[-_ ]?\d{2,4}[-_ ]?\d{2,6})", base)
    if m:
        return re.sub(r"[\s_]+", "-", m.group(1)).upper()

    m = re.search(r"([0-9]{2}[-_ ]?[A-Za-z]{2,}[-_ ]?[0-9]{2,})", base)
    if m:
        return re.sub(r"[\s_]+", "-", m.group(1)).upper()

    m2 = re.search(r"([0-9]{4,})", base)
    return (m2.group(1) if m2 else base[:40]).upper()


# ✅ Extract from content
ROLL_TEXT_RE = re.compile(
    r"(student\s*roll\s*no|roll\s*no|registration\s*no|reg\s*no)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-_/]{3,})",
    re.IGNORECASE
)
NAME_TEXT_RE = re.compile(
    r"(student\s*name)\s*[:\-]?\s*(.+)",
    re.IGNORECASE
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

            parsed = parse_document(fp) or {}
            text = clean_text(parsed.get("text") or "")[:MAX_TEXT]
            if not text.strip():
                skipped += 1
                continue

            # ✅ Prefer roll from file CONTENT, fallback to filename inference
            roll_from_text, name_from_text = _extract_roll_and_name_from_text(text)
            reg_no = roll_from_text or _infer_reg_no(fp_path.name)

            # Find/create Student by reg_no
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

            # Save Upload + UploadText
            up = Upload(
                course_id=str(assessment.course_id),
                filename_original=fp_path.name,   # ✅ used by UI
                filename_stored=fp_path.name,
                ext=ext.lstrip("."),
                file_type_guess="student_submission",
                week_no=None,
                bytes=fp_path.stat().st_size if fp_path.exists() else 0,
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
                "filename_original": fp_path.name,
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
                updated += 1
            else:
                sub = StudentSubmission(
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
                db.add(sub)
                created += 1

        except Exception as e:
            errors.append(f"{Path(fp).name}: {str(e)}")

    db.commit()
    return {
        "files_seen": len(files),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


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

    subs = (
        db.query(StudentSubmission)
        .filter(StudentSubmission.assessment_id == assessment.id)
        .order_by(StudentSubmission.submitted_at.asc())
        .all()
    )
    if not subs:
        raise ValueError("No submissions found for this assessment. Upload submissions ZIP first.")

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

    for s in subs:
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
                "raw_response": meta.get("raw_response"),
                "parsed": parsed,
            }

            db.add(s)
            graded += 1

        except Exception as e:
            s.status = "error"
            s.evidence_json = {**(s.evidence_json or {}), "error": str(e)}
            db.add(s)
            failed += 1

    gr.completed = True
    db.add(gr)
    db.commit()

    return {"graded": graded, "failed": failed, "grading_run_id": str(gr.id)}
