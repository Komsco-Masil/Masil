from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
import bcrypt
import uuid
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호 대조 (bcrypt 직접 사용)"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), 
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """비밀번호 해싱 (bcrypt 직접 사용)"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """JWT 액세스 토큰 생성"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "jti": str(uuid.uuid4())
    }
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """JWT 리프레시 토큰 생성"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)  # 7일 만료
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "jti": str(uuid.uuid4())
    }
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt
