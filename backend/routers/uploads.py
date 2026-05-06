from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import os, zipfile, tempfile
from typing import Optional, Tuple

from core.db import SessionLocal
from .auth import get_current_user
from models.course import Course
from models.uploads import Upload, UploadText, UploadFileItem
from models.completeness import CompletenessRun
from schemas.upload import UploadItem, UploadResponse
from services.upload_adapter import parse_document
from services.storage import save_bytes
from services.completeness_service import run_completeness
from services.exception_service import log_exception


router = APIRouter(prefix="/upload", tags=["Uploads"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ext_of(filename: str) -> str:
    return os.path.splitext(filename)[1].lower().lstrip(".") or "bin"


def _sanitize_text(s: str | None) -> str | None:
    if s is None:
        return None
    return s.replace("\x00", "")


def _parse_path_to_text(path: Path) -> Tuple[Optional[str], Optional[int]]:
    out = parse_document(str(path)) or {}
    text = _sanitize_text(out.get("text"))
    pages = out.get("pages")

    try:
        pages = int(pages) if pages is not None else None
    except Exception:
        pages = None

    return text, pages


def _parse_bytes_temp(filename: str, data: bytes) -> Tuple[Optional[str], Optional[int]]:
    suffix = Path(filename).suffix.lower() or ".bin"

    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tf:
        tf.write(data)
        tf.flush()
        return _parse_path_to_text(Path(tf.name))


def _status_from_completeness(result: dict) -> str:
    score = float(result.get("score_percent") or 0)

    if score >= 80:
        return "complete"
    if score > 0:
        return "incomplete"
    return "invalid"


@router.post("/{course_id}", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_course_folder(
    course_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    items: list[dict] = []
    log: list[dict] = []

    for f in files:
        raw_bytes = await f.read()

        if not raw_bytes:
            log_exception(
                db=db,
                course_id=course_id,
                upload_id=None,
                module="upload",
                error_type="empty_file",
                message=f"Empty file uploaded: {f.filename}",
                severity="medium",
            )

            log.append(
                {
                    "file": f.filename,
                    "stored": False,
                    "error": "empty file",
                }
            )
            continue

        ext = _ext_of(f.filename)

        try:
            saved = save_bytes(
                namespace=f"uploads/{course_id}",
                filename=f.filename,
                data=raw_bytes,
            )
        except Exception as e:
            log_exception(
                db=db,
                course_id=course_id,
                upload_id=None,
                module="upload",
                error_type="storage_failed",
                message=str(e),
                severity="high",
            )

            log.append(
                {
                    "file": f.filename,
                    "stored": False,
                    "error": "storage failed",
                }
            )
            continue

        now = datetime.utcnow()

        up = Upload(
            course_id=course_id,
            filename_original=f.filename,
            filename_stored=saved["key"],
            ext=ext,
            file_type_guess="course_folder",
            week_no=None,
            bytes=len(raw_bytes),
            created_at=now,
            parse_log=[],
            storage_backend=saved["backend"],
            storage_key=saved["key"],
            storage_url=saved.get("url"),
        )

        db.add(up)
        db.flush()

        texts: list[str] = []
        pages_total = 0
        parse_warnings = []

        def add_file_item(
            name: str,
            ext_: str,
            b: int,
            pages: Optional[int],
            text_chars: Optional[int],
        ):
            db.add(
                UploadFileItem(
                    upload_id=up.id,
                    filename=name,
                    ext=ext_,
                    bytes=b,
                    pages=pages,
                    text_chars=text_chars,
                )
            )

        if ext == "zip":
            try:
                with tempfile.NamedTemporaryFile(delete=True, suffix=".zip") as ztf:
                    ztf.write(raw_bytes)
                    ztf.flush()

                    with zipfile.ZipFile(ztf.name, "r") as zf:
                        for zi in zf.infolist():
                            if zi.is_dir():
                                continue

                            name = zi.filename
                            low = name.lower()

                            if not low.endswith((".pdf", ".docx", ".doc", ".txt")):
                                continue

                            try:
                                member_bytes = zf.read(zi)
                                mem_ext = _ext_of(name)

                                t, p = _parse_bytes_temp(name, member_bytes)

                                if t:
                                    texts.append(t)

                                if p:
                                    pages_total += p

                                add_file_item(
                                    name=Path(name).name,
                                    ext_=mem_ext,
                                    b=len(member_bytes),
                                    pages=p,
                                    text_chars=(len(t) if t else None),
                                )

                            except Exception as e:
                                parse_warnings.append(
                                    {
                                        "file": name,
                                        "error": str(e),
                                    }
                                )

                                log_exception(
                                    db=db,
                                    course_id=course_id,
                                    upload_id=str(up.id),
                                    module="parsing",
                                    error_type="zip_member_parse_failed",
                                    message=f"{name}: {str(e)}",
                                    severity="medium",
                                )

            except Exception as e:
                up.parse_log = [{"zip_error": str(e)}]
                parse_warnings.append({"zip_error": str(e)})

                log_exception(
                    db=db,
                    course_id=course_id,
                    upload_id=str(up.id),
                    module="parsing",
                    error_type="zip_parse_failed",
                    message=str(e),
                    severity="high",
                )

        else:
            try:
                t, p = _parse_bytes_temp(f.filename, raw_bytes)

                if t:
                    texts.append(t)

                if p:
                    pages_total = p

                add_file_item(
                    name=f.filename,
                    ext_=ext,
                    b=len(raw_bytes),
                    pages=p,
                    text_chars=(len(t) if t else None),
                )

            except Exception as e:
                parse_warnings.append(
                    {
                        "file": f.filename,
                        "error": str(e),
                    }
                )

                log_exception(
                    db=db,
                    course_id=course_id,
                    upload_id=str(up.id),
                    module="parsing",
                    error_type="file_parse_failed",
                    message=f"{f.filename}: {str(e)}",
                    severity="medium",
                )

        joined = _sanitize_text("\n\n".join(texts) if texts else None)

        ut = UploadText(
            upload_id=up.id,
            text=joined,
            text_chars=(len(joined) if joined else None),
            text_density=None,
            needs_ocr=False,
            parse_warnings=parse_warnings or ([{"note": "zip-expanded"}] if ext == "zip" else []),
        )

        db.add(ut)
        db.commit()
        db.refresh(up)

        try:
            completeness_result = run_completeness(
                db=db,
                course_id=course_id,
                upload_id=up.id,
                week_no=None,
            )
            validation_status = _status_from_completeness(completeness_result)

        except Exception as e:
            log_exception(
                db=db,
                course_id=course_id,
                upload_id=str(up.id),
                module="completeness",
                error_type="completeness_failed",
                message=str(e),
                severity="high",
            )

            completeness_result = {
                "error": str(e),
                "message": "Upload was stored, but completeness check failed.",
            }
            validation_status = "check_failed"

        items.append(
            UploadItem(
                id=str(up.id),
                filename_original=up.filename_original,
                filename_stored=up.filename_stored,
                ext=up.ext,
                file_type_guess=up.file_type_guess,
                week_no=up.week_no,
                bytes=up.bytes,
                pages=pages_total or None,
                version=1,
            ).model_dump()
            | {
                "upload_date": up.created_at,
                "validation_status": validation_status,
                "validation_details": completeness_result,
                "storage_backend": up.storage_backend,
                "storage_url": up.storage_url,
            }
        )

        log.append(
            {
                "file": f.filename,
                "stored": True,
                "bytes": len(raw_bytes),
                "backend": saved["backend"],
                "completeness_status": validation_status,
                "parse_warnings": parse_warnings,
            }
        )

    return {
        "files": items,
        "log": log,
    }


@router.get("/{course_id}/list")
def list_uploads(
    course_id: str,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    rows = (
        db.query(Upload)
        .filter(Upload.course_id == course_id)
        .order_by(Upload.created_at.desc())
        .all()
    )

    if not rows:
        return []

    out = []

    for r in rows:
        latest_run = (
            db.query(CompletenessRun)
            .filter(CompletenessRun.upload_id == r.id)
            .order_by(CompletenessRun.created_at.desc())
            .first()
        )

        if latest_run and latest_run.result_json:
            validation_details = latest_run.result_json
            validation_status = _status_from_completeness(validation_details)
        else:
            validation_details = {
                "message": "No official completeness check has been run for this upload yet."
            }
            validation_status = "not_checked"

        out.append(
            {
                "id": str(r.id),
                "filename": r.filename_original,
                "upload_date": r.created_at,
                "validation_status": validation_status,
                "validation_details": validation_details,
                "ext": r.ext,
                "bytes": r.bytes,
                "storage_backend": getattr(r, "storage_backend", "local"),
                "storage_url": getattr(r, "storage_url", None),
            }
        )

    return out