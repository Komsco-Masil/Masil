from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base
import datetime

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    business_number = Column(String(20), unique=True, index=True, nullable=False)  # 사업자등록번호
    name = Column(String(100), nullable=False)                                     # 가맹점명
    address = Column(String(255), nullable=False)                                   # 주소
    is_manual_review = Column(Boolean, default=False, nullable=False)               # 수동 검토 대상 여부


    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # 관계 정의
    store_users = relationship("StoreUser", back_populates="store", cascade="all, delete-orphan")
    invites = relationship("StoreInvite", back_populates="store", cascade="all, delete-orphan")
    promotions = relationship("Promotion", back_populates="store", cascade="all, delete-orphan")


class StoreUser(Base):
    __tablename__ = "store_users"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)                                      # 역할: OWNER, EMPLOYEE
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # 관계 정의
    store = relationship("Store", back_populates="store_users")
    user = relationship("User", back_populates="store_users")

    # 한 유저가 한 가게에 중복 매핑되는 것을 방지
    __table_args__ = (
        UniqueConstraint("store_id", "user_id", name="uq_store_user"),
    )
