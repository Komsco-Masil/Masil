from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String(50), unique=True, index=True, nullable=False)  # 닉네임 (중복불가)
    neighborhood = Column(String(100), nullable=False)                     # 동네 정보 (필수)
    role = Column(String(20), default="USER", nullable=False)               # 권한: USER, OWNER, EMPLOYEE
    provider = Column(String(20), default="LOCAL", nullable=False)           # 가입경로: LOCAL, KAKAO, NAVER, GOOGLE
    social_id = Column(String(100), nullable=True, index=True)              # 소셜 고유 ID
    hashed_password = Column(String(255), nullable=True)                    # 비밀번호 해시 (일반 가입용)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # 관계 정의
    store_users = relationship("StoreUser", back_populates="user", cascade="all, delete-orphan")
