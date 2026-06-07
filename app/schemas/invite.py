import datetime
from pydantic import BaseModel, Field, ConfigDict

class InviteCreate(BaseModel):
    store_id: int = Field(...)  # 초대를 보낼 가맹점 ID

class InviteResponse(BaseModel):
    id: int
    invite_code: str
    store_id: int
    expires_at: datetime.datetime
    is_used: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class InviteUseRequest(BaseModel):
    invite_code: str = Field(..., min_length=1)  # 사장에게 받은 초대 코드
