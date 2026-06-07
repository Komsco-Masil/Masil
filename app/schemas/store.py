import datetime
from pydantic import BaseModel, Field, ConfigDict

class StoreBase(BaseModel):
    business_number: str = Field(..., min_length=1)  # 사업자등록번호
    name: str = Field(..., min_length=1)             # 가맹점명
    address: str = Field(..., min_length=1)          # 주소

class StoreCreate(StoreBase):
    is_manual_review: bool = False

from typing import Optional

class StoreResponse(StoreBase):
    id: int
    is_manual_review: bool
    created_at: datetime.datetime
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class StoreVerifyRequest(StoreBase):
    start_date: Optional[str] = Field("", description="개업일자 (8자리_YYYYMMDD)")
    representative_name: Optional[str] = Field("", description="대표자성명")



