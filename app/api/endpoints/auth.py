from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()


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

    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
