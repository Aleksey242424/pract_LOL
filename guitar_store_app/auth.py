# auth.py
from datetime import datetime, timezone, timedelta
from typing import Optional
import jwt
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext
from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User

SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
MAX_FAILED_ATTEMPTS = 3
LOCKOUT_MINUTES = 15

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        print(f"!!! JWT DECODE ERROR: {type(e).__name__}: {e}")
        return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    # sub в JWT хранится строкой — приводим к int
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return db.query(User).filter(User.id_user == user_id).first()


def require_admin(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    if not current_user or current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return current_user


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def authenticate_user(db: Session, login: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.login == login).first()
    if not user:
        return None

    locked = _ensure_aware(user.locked_until)
    if locked and locked > _now_utc():
        raise HTTPException(
            status_code=423,
            detail=f"Аккаунт заблокирован до {locked.strftime('%H:%M:%S')}",
        )

    if not verify_password(password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = _now_utc() + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_attempts = 0
        db.commit()
        return None

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()
    return user