import json
import re
import zipfile
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.course import Course
from models.uploads import Upload, UploadText, UploadFileItem
from models.course_execution import WeeklyPlan, WeeklyExecution, DeviationLog
from models.completeness import CompletenessRun
from models.grading_audit import GradingAudit

from services.upload_adapter import parse_document
from services.execution_compare import compare_week

# OPTIONAL (safe imports)
try:
    from services.clo_alignment_service import run_clo_alignment
except Exception:
    run_clo_alignment = None


ALLOWED_EXTS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
MAX_FILES = 200
MAX_TEXT_CHARS = 80_000

PLACEHOLDER_HINTS = {
    "update later",
    "topics (auto)",
    "week topics",
}


# ----------------------- helpers -----------------------

def clean_text(val: Optional[str]) -> str:
    if val is None:
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


def _strip_placeholders(text: str) -> str:
    t = clean_text(text).lower()
    for h in PLACEHOLDER_HINTS:
        t = t.replace(h, " ")
    return re.sub(r"\s+", " ", t).strip()


def _safe_extract_zip(zip_path: str, dest_dir: str) -> list[str]:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    extracted: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()[:MAX_FILES]
        for member in names:
            if member.endswith("/"):
                continue

            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as out:
                out.write(src.read())

            extracted.append(str(target))
    return extracted


def _extract_week_section(text: str, week_no: int) -> str:
    t = clean_text(text)
    if not t:
        return ""

    if week_no < 16:
        pat = rf"(?ms)^\s*{week_no}\s+(.*?)(?=^\s*{week_no+1}\s+)"
    else:
        pat = rf"(?ms)^\s*{week_no}\s+(.*)$"

    m = re.search(pat, t)
    return m.group(1).strip() if m else ""


def _compact_text_for_matching(text: str) -> str:
    text = clean_text(text)
    if len(text) <= MAX_TEXT_CHARS:
        return text
    h = MAX_TEXT_CHARS // 2
    return (text[:h] + "\n\n---SNIP---\n\n" + text[-h:]).strip()


def _resolve_course(db: Session, course_id_or_code: str) -> Course | None:
    return (
        db.query(Course)
        .filter(
            or_(
                Course.id == course_id_or_code,
                Course.course_code == course_id_or_code,
            )
        )
        .first()
    )


def _course_clos_json_to_list(raw: str) -> list[str]:
    """
    Admin stores courses.clos as JSON string:
      [{"code":"CLO1","description":"..."}, ...]
    Convert to list[str] used by run_clo_alignment:
      ["CLO1: ...", ...]
    """
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    out: list[str] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                code = (item.get("code") or "").strip()
                desc = (item.get("description") or "").strip()
                if code and desc:
                    out.append(f"{code}: {desc}")
            elif isinstance(item, str) and item.strip():
                out.append(item.strip())
    return out


# ----------------------- MAIN SERVICE -----------------------

def handle_weekly_zip_upload(
    db: Session,
    course_id: str,
    week_no: int,
    user_id: str,
    zip_file_bytes: bytes,
    zip_filename: str,
    storage_root: str = "uploads/weekly",
) -> Dict[str, Any]:

    now = datetime.now(timezone.utc)

    # ---------- resolve course ----------
    course = _resolve_course(db, course_id)
    if not course:
        raise ValueError(f"Course not found: {course_id}")

    real_course_id = str(course.id)

    # ---------- store zip ----------
    upload_ts = str(int(now.timestamp() * 1000))
    base_dir = Path(storage_root) / real_course_id / f"week_{week_no}" / upload_ts
    base_dir.mkdir(parents=True, exist_ok=True)

    zip_path = base_dir / (zip_filename or f"week_{week_no}.zip")
    zip_path.write_bytes(zip_file_bytes)

    extracted_dir = base_dir / "extracted"
    files = _safe_extract_zip(str(zip_path), str(extracted_dir))

    # ---------- parse files ----------
    texts: List[str] = []
    manifest: List[Dict[str, Any]] = []

    for fp in files:
        ext = Path(fp).suffix.lower()
        if ext not in ALLOWED_EXTS:
            continue

        try:
            parsed = parse_document(fp) or {}
            raw = parsed.get("text") or ""
            txt = clean_text(raw)
            err = parsed.get("error")
        except Exception as e:
            txt = ""
            err = str(e)

        if txt:
            texts.append(txt)

        manifest.append({
            "path": fp,
            "ext": ext,
            "chars": len(txt),
            "error": err,
        })

    delivered_text = _compact_text_for_matching("\n\n".join(texts))

    if not delivered_text.strip():
        raise ValueError("No text extracted from weekly ZIP")

    # ---------- fetch plan ----------
    plan = (
        db.query(WeeklyPlan)
        .filter(
            WeeklyPlan.course_id == real_course_id,
            WeeklyPlan.week_number == week_no,
        )
        .first()
    )

    plan_source = "weekly_plans.planned_topics"
    plan_text_raw = clean_text(plan.planned_topics if plan else "")

    week_section = _extract_week_section(plan_text_raw, week_no)
    if week_section:
        plan_text = week_section
        plan_source += " (week section)"
    else:
        plan_text = _strip_placeholders(plan_text_raw)

    if not plan_text.strip():
        guide = clean_text(getattr(course, "course_guide_text", "") or "")
        week_section = _extract_week_section(guide, week_no)
        if week_section:
            plan_text = week_section
            plan_source = "courses.course_guide_text (week section)"
        else:
            plan_text = _strip_placeholders(guide)
            plan_source = "courses.course_guide_text"

    if not plan_text.strip():
        raise ValueError("No weekly plan text available")

    # ---------- COVERAGE ----------
    coverage_score, missing_terms, plan_terms = compare_week(plan_text, delivered_text)

    coverage_percent = float(coverage_score) * 100.0
    coverage_status = "on_track" if coverage_percent >= 80.0 else "behind"
    matched_terms = [t for t in plan_terms if t not in set(missing_terms)]

    audit_snapshot = {
        "timestamp": now.isoformat(),
        "week_no": week_no,
        "coverage_score": coverage_score,
        "coverage_percent": coverage_percent,
        "plan_source": plan_source,
    }

    # ---------- CLO ALIGNMENT (OPTIONAL) ----------
    clo_alignment_result = None
    if run_clo_alignment and getattr(course, "clos", None):
        try:
            clos_list = _course_clos_json_to_list(course.clos or "")
            if clos_list:
                # run_clo_alignment expects assessments = list[{"name": "..."}]
                assessments_for_alignment = [{"name": t} for t in plan_terms[:50]]
                clo_alignment_result = run_clo_alignment(
                    clos=clos_list,
                    assessments=assessments_for_alignment,
                    threshold=0.65,
                )
        except Exception:
            clo_alignment_result = None

    # ---------- save Upload ----------
    up = Upload(
        course_id=real_course_id,
        filename_original=zip_filename,
        filename_stored=zip_path.name,
        ext="zip",
        file_type_guess="weekly_zip",
        week_no=week_no,
        bytes=len(zip_file_bytes),
        parse_log=manifest,
        created_at=now.replace(tzinfo=None),
    )
    db.add(up)
    db.flush()

    # ---------- per-file metadata ----------
    for m in manifest:
        try:
            p = m.get("path")
            if not p:
                continue
            fpath = Path(p)
            db.add(
                UploadFileItem(
                    upload_id=up.id,
                    filename=fpath.name,
                    ext=fpath.suffix.lstrip("."),
                    bytes=fpath.stat().st_size if fpath.exists() else 0,
                    pages=None,
                    text_chars=int(m.get("chars") or 0),
                )
            )
        except Exception:
            pass

    db.add(
        UploadText(
            upload_id=up.id,
            text=delivered_text,
            text_chars=len(delivered_text),
            needs_ocr=False,
            parse_warnings=manifest,
        )
    )

    # ---------- completeness run (history) ----------
    try:
        from services.completeness_service import run_completeness
        comp = run_completeness(db=db, course_id=real_course_id, upload_id=up.id, week_no=week_no)
        db.add(
            CompletenessRun(
                course_id=real_course_id,
                upload_id=up.id,
                week_no=week_no,
                result_json=comp,
            )
        )
    except Exception:
        comp = None

    # ---------- upsert WeeklyExecution ----------
    ex = (
        db.query(WeeklyExecution)
        .filter(
            WeeklyExecution.course_id == real_course_id,
            WeeklyExecution.week_number == week_no,
        )
        .first()
    )
    if not ex:
        ex = WeeklyExecution(course_id=real_course_id, week_number=week_no)
        db.add(ex)

    ex.coverage_percent = coverage_percent
    ex.coverage_status = coverage_status
    ex.delivered_topics = delivered_text
    ex.missing_topics = clean_text("\n".join(missing_terms))[:20000]
    ex.matched_topics = clean_text("\n".join(matched_terms))[:20000]
    ex.last_updated_at = now

    if hasattr(ex, "audit_json"):
        ex.audit_json = audit_snapshot

    if hasattr(ex, "audit_history"):
        hist = ex.audit_history or []
        hist.append(audit_snapshot)
        ex.audit_history = hist

    # ✅ store dict directly (not model_dump)
    if clo_alignment_result and hasattr(ex, "clo_audit_json"):
        ex.clo_audit_json = clo_alignment_result

    if coverage_status == "behind":
        db.add(
            DeviationLog(
                course_id=real_course_id,
                week_number=week_no,
                type="coverage_low",
                details=json.dumps(audit_snapshot),
            )
        )

    # ---------- grading fairness hook ----------
    try:
        if hasattr(course, "assessments"):
            for a in course.assessments or []:
                db.add(
                    GradingAudit(
                        assessment_id=a.id,
                        metric="weekly_context",
                        value=f"Week {week_no} coverage={coverage_percent:.2f}",
                        notes="Recorded during weekly ZIP upload",
                    )
                )
    except Exception:
        pass

    db.commit()
    db.refresh(ex)

    return {
        "course_id": real_course_id,
        "course_code": course.course_code,
        "week_no": week_no,
        "coverage_score": coverage_score,
        "coverage_percent": coverage_percent,
        "coverage_status": coverage_status,
        "missing_terms": missing_terms[:200],
        "matched_terms": matched_terms[:200],
        "audit": audit_snapshot,
        "clo_alignment": clo_alignment_result if clo_alignment_result else None,
        "completeness": comp,
        "upload_id": str(up.id),
        "files_seen": len(files),
        "files_used": len([m for m in manifest if m["ext"] in ALLOWED_EXTS]),
        "plan_source": plan_source,
        "plan_text_len": len(plan_text),
        "delivered_text_len": len(delivered_text),
        "manifest_errors": [m for m in manifest if m.get("error")][:5],
    }
