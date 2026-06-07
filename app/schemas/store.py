import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

class StoreBase(BaseModel):
    business_number: str = Field(..., min_length=1)  # 사업자등록번호
    name: str = Field(..., min_length=1)             # 가맹점명
    address: str = Field(..., min_length=1)          # 주소

class StoreCreate(StoreBase):
    is_manual_review: bool = False

class StoreResponse(StoreBase):
    id: int
    is_manual_review: bool
    nts_verified: bool = False
    gift_card_verified: bool = False
    public_data_source: Optional[str] = None
    verified_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class StoreVerifyRequest(BaseModel):
    business_number: str = Field(..., min_length=10, max_length=10)
    name: str = Field(..., min_length=1)
    representative_name: str = Field(..., min_length=1, description="대표자성명")
    address: Optional[str] = ""

    @field_validator("business_number", mode="before")
    @classmethod
    def normalize_business_number(cls, value: object) -> str:
        normalized = "".join(char for char in str(value) if char.isdigit())
        if len(normalized) != 10:
            raise ValueError("사업자등록번호는 숫자 10자리여야 합니다")
        return normalized


class PublicDataSource(BaseModel):
    name: str
    provider: str
    purpose: str
    status: str


class PublicDataStore(BaseModel):
    id: str
    name: str
    address: str
    category: str
    gift_card_verified: bool
    source: str


class PublicDataSummaryResponse(BaseModel):
    title: str
    description: str
    sources: list[PublicDataSource]
    stores: list[PublicDataStore]
