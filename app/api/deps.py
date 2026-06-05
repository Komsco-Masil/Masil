from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.schemas.user import TokenData
from app.services.giftcard_client import LocalGiftCardClient

# 토큰 획득 엔드포인트 URL 지정
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_db() -> Generator[Session, None, None]:
    """DB 세션 생성 및 정리 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_giftcard_client() -> LocalGiftCardClient:
    """조폐공사 API 연동용 Mock 클라이언트 주입"""
    return LocalGiftCardClient()

def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(reusable_oauth2)
) -> User:
    """JWT 토큰을 복호화하여 현재 로그인한 사용자 정보를 조회합니다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
        token_data = TokenData(user_id=user_id)
    except (JWTError, ValueError):
        raise credentials_exception
        
    from app.models.token import TokenBlacklist
    is_blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
    if is_blacklisted:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise credentials_exception
    return user

def get_current_owner(
    current_user: User = Depends(get_current_user)
) -> User:
    """현재 로그인한 사용자가 OWNER(가맹점 사장님)인지 검증합니다."""
    if current_user.role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have OWNER privileges",
        )
    return current_user
