import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional
from models.course_clo import CourseCLO
from sqlalchemy.orm import Session

from models.course import Course
from models.uploads import Upload, UploadText
from models.assessment import Assessment, AssessmentFile, AssessmentExpectedAnswers, AssessmentCLOAlignment
from services.upload_adapter import parse_document
from services.openrouter_client import call_openrouter_json
from datetime import datetime, timezone, date as dt_date


ALLOWED_Q_EXTS = {".pdf", ".docx"}
MAX_TEXT = 120_000


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


def _read_prompt(rel_path: str) -> str:
    p = Path(__file__).resolve().parent / "ai_prompts" / rel_path
    return p.read_text(encoding="utf-8")


def create_assessment(db: Session, course_id: str, payload: Dict[str, Any], created_by: str) -> Assessment:
    # ✅ ensure not-null DB fields are always set
    weightage = payload.get("weightage", None)
    if weightage is None:
        weightage = 0

    raw_date = payload.get("date")
    if raw_date is None:
        # fallback to today if frontend didn't send
        raw_date = dt_date.today()

    a = Assessment(
        course_id=course_id,
        type=payload["type"],
        title=payload["title"],
        max_marks=int(payload.get("max_marks") or 0),
        weightage=int(weightage),
        date=raw_date,
        created_by=created_by,
        created_at=utcnow(),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def save_questions_file_and_extract_text(
    db: Session,
    assessment_id,
    course_id: str,
    file_bytes: bytes,
    filename: str,
    storage_root: str = "uploads/assessments",
) -> AssessmentFile:
    ext = (Path(filename).suffix or "").lower()
    if ext not in ALLOWED_Q_EXTS:
        raise ValueError("Only PDF/DOCX allowed for questions file")

    now = utcnow()
    base_dir = Path(storage_root) / str(course_id) / str(assessment_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"questions_{int(now.timestamp()*1000)}{ext}"
    stored_path = base_dir / stored_name
    stored_path.write_bytes(file_bytes)

    parsed = parse_document(str(stored_path)) or {}
    extracted = clean_text(parsed.get("text") or "")[:MAX_TEXT]

    # Save Upload (matches your Upload model fields)
    up = Upload(
        course_id=course_id,
        filename_original=filename,
        filename_stored=stored_name,
        ext=ext.lstrip("."),
        file_type_guess="assessment_questions",
        week_no=None,
        bytes=len(file_bytes),
        parse_log=[],
        created_at=datetime.utcnow(),
    )
    db.add(up)
    db.flush()

    ut = UploadText(
        upload_id=up.id,
        text=extracted,
        text_chars=len(extracted),
        needs_ocr=False,
        parse_warnings=[],
    )
    db.add(ut)

    af = AssessmentFile(
        assessment_id=assessment_id,
        upload_id=up.id,
        filename_original=filename,
        filename_stored=stored_name,
        ext=ext.lstrip("."),
        created_at=now,
        extracted_text=extracted,
    )
    db.add(af)

    db.commit()
    db.refresh(af)
    return af


def ai_extract_questions(db: Session, assessment: Assessment) -> Dict[str, Any]:
    # pick latest questions file text
    af = (
        db.query(AssessmentFile)
        .filter(AssessmentFile.assessment_id == assessment.id)
        .order_by(AssessmentFile.created_at.desc())
        .first()
    )
    if not af or not (af.extracted_text or "").strip():
        raise ValueError("No extracted questions text found. Upload questions file first.")

    system = _read_prompt("question_extract_v1.txt")
    schema_hint = '{"questions":[{"question_no":1,"question_text":"...","marks":5}],"total_questions":10}'
    user = f"ASSESSMENT_TEXT:\n{af.extracted_text[:MAX_TEXT]}"

    parsed, meta = call_openrouter_json(system=system, user=user, schema_hint=schema_hint, temperature=0.2)
    # store on file record for convenience
    # (optional: you can store parsed questions in another table later)
    return {"questions_json": parsed, "meta": meta}


def ai_generate_expected_answers(db: Session, assessment: Assessment) -> AssessmentExpectedAnswers:
    # Step 1: extract questions via AI
    qpack = ai_extract_questions(db, assessment)
    questions_json = qpack["questions_json"]

    system = _read_prompt("expected_answers_v1.txt")
    schema_hint = '{"total_questions":10,"answers":[{"question_no":1,"expected_answer":"...","key_points":["a"],"marks_split":[{"point":"a","marks":2}]}]}'
    user = f"ASSESSMENT_TITLE: {assessment.title}\nMAX_MARKS: {assessment.max_marks}\nQUESTIONS_JSON:\n{json.dumps(questions_json, ensure_ascii=False)}"

    parsed, meta = call_openrouter_json(system=system, user=user, schema_hint=schema_hint, temperature=0.25)

    # upsert expected
    exp = (
        db.query(AssessmentExpectedAnswers)
        .filter(AssessmentExpectedAnswers.assessment_id == assessment.id)
        .first()
    )
    if not exp:
        exp = AssessmentExpectedAnswers(assessment_id=assessment.id)

    exp.prompt_version = "v1"
    exp.model = meta.get("model")
    exp.input_hash = meta.get("input_hash")
    exp.raw_response = meta.get("raw_response")
    exp.parsed_json = parsed
    exp.created_at = utcnow()

    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def ai_clo_alignment(db: Session, assessment: Assessment) -> AssessmentCLOAlignment:
    """Align assessment questions against course CLOs.

    ✅ Preferred source: latest `course_clos` upload record (CourseCLO.clos_text)
    ✅ Fallback source: `Course.clos` JSON string (legacy)
    """

    clos_list: List[str] = []

    # 1) Preferred: latest CourseCLO record (newline-separated)
    try:
        rec = (
            db.query(CourseCLO)
            .filter(CourseCLO.course_id == str(assessment.course_id))
            .order_by(CourseCLO.upload_date.desc())
            .first()
        )
        if rec and (rec.clos_text or "").strip():
            clos_list = [ln.strip() for ln in (rec.clos_text or "").splitlines() if ln.strip()]
    except Exception:
        clos_list = []

    # 2) Fallback: legacy Course.clos JSON
    if not clos_list:
        course = db.get(Course, assessment.course_id)
        raw_clos = (getattr(course, "clos", None) or "") if course else ""
        try:
            if raw_clos:
                parsed = json.loads(raw_clos)
                if isinstance(parsed, dict):
                    parsed = list(parsed.values())
                if isinstance(parsed, list):
                    clos_list = [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            clos_list = []

    if not clos_list:
        align = (
            db.query(AssessmentCLOAlignment)
            .filter(AssessmentCLOAlignment.assessment_id == assessment.id)
            .first()
        )
        if not align:
            align = AssessmentCLOAlignment(assessment_id=assessment.id)
        align.coverage_percent = 0.0
        align.per_clo = {}
        align.per_question = []
        align.model = None
        align.prompt_version = "v1"
        align.created_at = utcnow()
        db.add(align)
        db.commit()
        db.refresh(align)
        return align

    qpack = ai_extract_questions(db, assessment)
    questions_json = qpack["questions_json"]

    system = _read_prompt("clo_align_v1.txt")
    schema_hint = '{"per_question":[{"question_no":1,"clo":"CLO-1","confidence":0.8}],"per_clo":{"CLO-1":50},"coverage_percent":100}'
    user = f"CLO_LIST:\n{json.dumps(clos_list, ensure_ascii=False)}\n\nQUESTIONS_JSON:\n{json.dumps(questions_json, ensure_ascii=False)}"

    parsed, meta = call_openrouter_json(system=system, user=user, schema_hint=schema_hint, temperature=0.2)

    align = (
        db.query(AssessmentCLOAlignment)
        .filter(AssessmentCLOAlignment.assessment_id == assessment.id)
        .first()
    )
    if not align:
        align = AssessmentCLOAlignment(assessment_id=assessment.id)

    align.coverage_percent = float(parsed.get("coverage_percent") or 0.0)
    align.per_clo = parsed.get("per_clo") or {}
    align.per_question = parsed.get("per_question") or []
    align.model = meta.get("model")
    align.prompt_version = "v1"
    align.created_at = utcnow()

    db.add(align)
    db.commit()
    db.refresh(align)
    return align
