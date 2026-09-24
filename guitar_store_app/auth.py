from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User

# ============ НАСТРОЙКИ ============
# В реальном проекте SECRET_KEY должен быть в .env и быть длинным
SECRET_KEY = "super-secret-key-change-me-in-production-1234567890"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 сутки

# Контекст для хеширования паролей (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Схема OAuth2: токен берётся из заголовка Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ============ ХЕШИРОВАНИЕ ПАРОЛЕЙ ============
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ============ JWT ============
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============ ЗАВИСИМОСТИ ============
def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Возвращает текущего пользователя по JWT.
    Сначала пробует заголовок Authorization: Bearer ...
    Если его нет — берёт токен из cookie access_token (для HTML-страниц).
    """
    # 1. Если Bearer-токен не пришёл — пробуем cookie
    if not token:
        token = request.cookies.get("access_token")

    # 2. Если и там пусто — 401
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Декодируем и ищем пользователя
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Некорректный токен")

    user = db.query(User).filter(User.id_user == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Для HTML-страниц: берём токен из cookie, если он есть. Иначе None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        return db.query(User).filter(User.id_user == int(user_id)).first()
    except HTTPException:
        return None


def require_role(*roles: str):
    """Фабрика зависимостей: требует одну из указанных ролей."""
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещён. Требуется роль: {', '.join(roles)}",
            )
        return current_user
    return checker


# Готовые зависимости
require_admin = require_role("admin")
require_manager = require_role("admin", "manager")
require_any = require_role("admin", "manager", "client")