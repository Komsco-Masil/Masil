import os
from typing import List

class Settings:
    PROJECT_NAME: str = "Masil"
    API_V1_STR: str = "/api"
    
    # JWT 보안 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "masil-super-secret-key-for-jwt-token-auth-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24시간 (초대 코드 만료 시간과 맞춤)

    # 데이터베이스 설정 (기본값은 PostgreSQL, 필요 시 SQLite 등 변경 가능)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/masil"
    )

    # 한국조폐공사 OpenAPI 설정
    KOREA_MINTING_API_URL: str = os.getenv(
        "KOREA_MINTING_API_URL",
        "https://apis.data.go.kr/B552576/localGiftCardService/getMerchantList"
    )
    # 공공데이터포털 서비스키 (Dotenv 로드)
    KOREA_MINTING_SERVICE_KEY: str = os.getenv("KOREA_MINTING_SERVICE_KEY", "")

settings = Settings()
