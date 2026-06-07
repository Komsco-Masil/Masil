from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, reusable_oauth2
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.models.token import RefreshToken, TokenBlacklist
from app.schemas.user import UserCreate, UserResponse, Token, TokenRefreshRequest, UserUpdate
from app.core.config import settings
import datetime
from jose import jwt

router = APIRouter()


class SocialLoginRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=20)
    social_id: str = Field(..., min_length=2, max_length=100)
    nickname: str = Field(..., min_length=2, max_length=50)
    neighborhood: str = "동네 미설정"


def issue_tokens(user_id: int, db: Session) -> dict:
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)

    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp = payload.get("exp")
        expires_at = datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        expires_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(days=7)

    db_refresh = RefreshToken(
        token=refresh_token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(db_refresh)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/check-nickname")
def check_nickname(nickname: str, db: Session = Depends(get_db)) -> dict:
    """
    닉네임/아이디 중복 확인 API
    """
    normalized = nickname.strip()
    if len(normalized) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nickname must be at least 2 characters"
        )

    exists = db.query(User).filter(User.nickname == normalized).first() is not None
    return {
        "available": not exists,
        "nickname": normalized
    }


@router.post("/social-login")
def social_login(payload: SocialLoginRequest, db: Session = Depends(get_db)) -> dict:
    """
    소셜 로그인 API

    실제 OAuth 검증은 provider SDK 연동 후 추가하고, 현재는 프론트 소셜 버튼과
    앱 세션 흐름을 검증하기 위한 provider/social_id 기반 로그인입니다.
    """
    provider = payload.provider.upper()
    user = db.query(User).filter(
        User.provider == provider,
        User.social_id == payload.social_id
    ).first()

    if not user:
        nickname = payload.nickname.strip()
        duplicate = db.query(User).filter(User.nickname == nickname).first()
        if duplicate:
            nickname = f"{nickname}_{provider.lower()}"

        user = User(
            nickname=nickname,
            neighborhood=payload.neighborhood,
            provider=provider,
            social_id=payload.social_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token_data = issue_tokens(user.id, db)
    return {
        **token_data,
        "user": {
            "id": user.id,
            "nickname": user.nickname,
            "neighborhood": user.neighborhood,
            "provider": user.provider,
            "social_id": user.social_id,
            "avatar_url": user.avatar_url,
        }
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """
    현재 로그인한 사용자의 프로필 정보 조회 API
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """
    닉네임, 동네, 프로필 이미지를 수정하는 API
    """
    if payload.nickname is not None:
        next_nickname = payload.nickname.strip()
        duplicate = db.query(User).filter(
            User.nickname == next_nickname,
            User.id != current_user.id,
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nickname already exists"
            )
        current_user.nickname = next_nickname

    if payload.neighborhood is not None:
        current_user.neighborhood = payload.neighborhood.strip()

    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip() or None

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    """
    회원가입 API (일반 및 OAuth)
    
    - 닉네임 중복 시 400 Bad Request
    - LOCAL 가입 시 비밀번호 필수
    """
    # 닉네임 중복 조회 예외 처리
    existing_user = db.query(User).filter(User.nickname == user_in.nickname).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nickname already exists"
        )

    # LOCAL 가입 시 비밀번호 검증 및 해싱
    hashed_password = None
    if user_in.provider == "LOCAL":
        if not user_in.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required for LOCAL provider"
            )
        hashed_password = get_password_hash(user_in.password)

    db_user = User(
        nickname=user_in.nickname,
        neighborhood=user_in.neighborhood,
        provider=user_in.provider,
        social_id=user_in.social_id,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> dict:
    """
    로그인 API (의존성 검증용 JWT 토큰 반환)
    """
    user = db.query(User).filter(User.nickname == form_data.username).first()
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect nickname or password"
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect nickname or password"
        )

    return issue_tokens(user.id, db)


@router.post("/refresh", response_model=Token)
def refresh_token(
    payload: TokenRefreshRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Refresh Token을 검증하여 새로운 Access Token과 Refresh Token을 발급받는 API
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    # 1. DB에서 리프레시 토큰 조회 및 유효성(revoked 여부) 검증
    db_refresh = db.query(RefreshToken).filter(
        RefreshToken.token == payload.refresh_token,
        RefreshToken.is_revoked == False
    ).first()
    if not db_refresh:
        raise credentials_exception

    # 만료 여부 확인
    if db_refresh.expires_at < datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None):
        db_refresh.is_revoked = True
        db.commit()
        raise credentials_exception

    # 2. JWT Decode
    try:
        jwt_payload = jwt.decode(
            payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_str: str = jwt_payload.get("sub")
        token_type: str = jwt_payload.get("type")
        if user_id_str is None or token_type != "refresh":
            raise credentials_exception
        user_id = int(user_id_str)
    except Exception:
        raise credentials_exception

    # 3. 새로운 토큰 발급 및 기존 토큰 revoke
    db_refresh.is_revoked = True
    
    new_access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)

    try:
        new_payload = jwt.decode(
            new_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        new_exp = new_payload.get("exp")
        new_expires_at = datetime.datetime.fromtimestamp(new_exp, tz=datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        new_expires_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(days=7)

    new_db_refresh = RefreshToken(
        token=new_refresh_token,
        user_id=user_id,
        expires_at=new_expires_at
    )
    db.add(new_db_refresh)
    db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(reusable_oauth2)
) -> dict:
    """
    로그아웃 API (Access Token 블랙리스트 추가 및 Refresh Token 만료 처리)
    """
    # 1. Access Token을 블랙리스트에 추가
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp = payload.get("exp")
        expires_at = datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        expires_at = datetime.datetime.now(timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=24)

    # 이미 블랙리스트에 있는지 확인
    existing_blacklist = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
    if not existing_blacklist:
        blacklist_item = TokenBlacklist(
            token=token,
            expires_at=expires_at
        )
        db.add(blacklist_item)

    # 2. 사용자의 모든 활성화된 리프레시 토큰 폐기 (revoke)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked == False
    ).update({RefreshToken.is_revoked: True})

    db.commit()

    return {"detail": "Successfully logged out"}
