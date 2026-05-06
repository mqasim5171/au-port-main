from fastapi import Depends, HTTPException, status
from routers.auth import get_current_user
from models.user import User


ROLE_ALIASES = {
    "administrator": "admin",
    "superadmin": "admin",
    "qec officer": "qec",
    "quality officer": "qec",
    "course lead": "course_lead",
    "faculty member": "faculty",
}


def normalize_role(role: str | None) -> str:
    r = (role or "").strip().lower()
    return ROLE_ALIASES.get(r, r)


def require_roles(*roles: str):
    allowed = {normalize_role(r) for r in roles}

    def _dep(current: User = Depends(get_current_user)) -> User:
        role = normalize_role(current.role)

        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current

    return _dep


def is_admin(role: str | None) -> bool:
    return normalize_role(role) == "admin"


def is_qec_or_admin(role: str | None) -> bool:
    return normalize_role(role) in {"admin", "qec"}


def is_faculty_level(role: str | None) -> bool:
    return normalize_role(role) in {"admin", "qec", "hod", "course_lead", "faculty"}