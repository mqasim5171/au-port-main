from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGO = "HS256"

def hash_password(p: str) -> str:
    return pwd_context.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    return pwd_context.verify(p, hashed)

def _create_token(sub: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=minutes)
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGO)

def create_access_token(user_id: str) -> str:
    return _create_token(user_id, settings.ACCESS_TOKEN_EXPIRE_MINUTES)

def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
    except JWTError:
        return None
