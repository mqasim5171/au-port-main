from sqlalchemy.orm import Session
from models.exception import ExceptionLog


def log_exception(
    db: Session,
    course_id: str | None,
    upload_id: str | None,
    module: str,
    error_type: str,
    message: str,
    severity: str = "medium",
):
    ex = ExceptionLog(
        course_id=course_id,
        upload_id=upload_id,
        module=module,
        error_type=error_type,
        message=message,
        severity=severity,
    )

    db.add(ex)
    db.commit()