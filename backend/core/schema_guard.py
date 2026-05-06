from sqlalchemy.exc import OperationalError

from core.db import engine
from core.base import Base

# Import all models so SQLAlchemy metadata knows every table
from models import user  # noqa: F401
from models import course  # noqa: F401
from models import uploads  # noqa: F401
from models import completeness  # noqa: F401
from models import course_execution  # noqa: F401
from models import assessment  # noqa: F401
from models import student  # noqa: F401
from models import student_submission  # noqa: F401
from models import student_feedback  # noqa: F401
from models import quality  # noqa: F401
from models import exception  # noqa: F401
from models import override  # noqa: F401
from models import suggestion  # noqa: F401
from models import course_staff  # noqa: F401
from models import grading_audit  # noqa: F401
from models import feedback  # noqa: F401
from models import course_clo  # noqa: F401
from models import material  # noqa: F401
from models import admin_document  # noqa: F401

_initialized = False


def ensure_all_tables_once():
    global _initialized

    if _initialized:
        return

    try:
        Base.metadata.create_all(bind=engine)
        _initialized = True
    except OperationalError as e:
        print("Database not reachable, skipping schema creation.")
        print(e)