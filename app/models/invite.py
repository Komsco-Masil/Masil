from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base
import datetime

class StoreInvite(Base):
    __tablename__ = "store_invites"

    id = Column(Integer, primary_key=True, index=True)
    invite_code = Column(String(50), unique=True, index=True, nullable=False)  # 초대 코드 (무작위 문자열)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)        # 가맹점 ID
    expires_at = Column(DateTime, nullable=False)                              # 만료시간 (24시간)
    is_used = Column(Boolean, default=False, nullable=False)                   # 사용여부
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # 관계 정의
    store = relationship("Store", back_populates="invites")
