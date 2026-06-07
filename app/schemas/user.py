import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from fastapi import HTTPException, status

class UserBase(BaseModel):
    nickname: str = Field(..., min_length=2, max_length=50)
    neighborhood: str = Field(..., min_length=1)

class UserCreate(UserBase):
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, min_length=2, max_length=50)
    password: Optional[str] = Field(None, min_length=4)
    provider: str = "LOCAL"
    social_id: Optional[str] = None
    is_terms_agreed: bool

    @field_validator("is_terms_agreed")
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        """약관 동의 여부 전처리 및 예외 처리 (False인 경우 400 Bad Request 반환)"""
        if not v:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Terms agreement is required"
            )
        return v

class UserResponse(UserBase):
    id: int
    username: Optional[str] = None
    display_name: Optional[str] = None
    role: str
    provider: str
    social_id: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, min_length=2, max_length=50)
    neighborhood: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class AuthUser(BaseModel):
    id: int
    username: Optional[str] = None
    nickname: str
    display_name: Optional[str] = None
    neighborhood: str
    provider: str
    social_id: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str


class AuthResponse(Token):
    user: AuthUser


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
