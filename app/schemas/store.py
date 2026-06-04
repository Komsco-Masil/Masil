import datetime
from pydantic import BaseModel, Field, ConfigDict

class StoreBase(BaseModel):
    business_number: str = Field(..., min_length=1)  # 사업자등록번호
    name: str = Field(..., min_length=1)             # 가맹점명
    address: str = Field(..., min_length=1)          # 주소

class StoreCreate(StoreBase):
    is_manual_review: bool = False

class StoreResponse(StoreBase):
    id: int
    is_manual_review: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class StoreVerifyRequest(StoreBase):
    pass
