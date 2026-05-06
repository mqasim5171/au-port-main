# backend/services/resetpassword.py
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from models.user import User
from core.security import hash_password, verify_password


def _find_user(db: Session, identifier: str) -> Optional[User]:
    """
    Find a user by email, username, or UUID (id).
    """
    user = None

    # Try email
    if "@" in identifier:
        user = db.query(User).filter(User.email == identifier).first()
        if user:
            return user

    # Try UUID
    try:
        uid = UUID(identifier)
        user = db.get(User, uid)
        if user:
            return user
    except Exception:
        pass

    # Try username
    return db.query(User).filter(User.username == identifier).first()


def reset_password_by_admin(db: Session, identifier: str, new_password: str) -> User:
    """
    Admin resets a user's password directly.
    """
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    user = _find_user(db, identifier)
    if not user:
        raise ValueError("User not found for the given identifier.")

    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_own_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    """
    Allow logged-in user to change their password after verifying old one.
    """
    if not verify_password(old_password, user.password_hash):
        raise ValueError("Old password is incorrect.")

    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
