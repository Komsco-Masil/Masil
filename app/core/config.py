import os
from typing import List

# .env 파일 로드 로직 (별도 외부 패키지 의존성 없이 환경변수 로드)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key_clean = key.strip()
                val_clean = val.strip()
                if key_clean not in os.environ:
                    os.environ[key_clean] = val_clean


def resolve_database_url() -> str:
    """Vercel/Neon 등 배포 환경의 DB URL을 SQLAlchemy 형식으로 정규화합니다."""
    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRES_PRISMA_URL")
        or "postgresql://postgres:postgres@localhost:5432/masil"
    )

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url.startswith("postgresql") and "localhost" not in url and "127.0.0.1" not in url:
        if "sslmode=" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"

    return url


class Settings:
    PROJECT_NAME: str = "Masil"
    API_V1_STR: str = "/api"
    
    # JWT 보안 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "masil-super-secret-key-for-jwt-token-auth-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24시간 (초대 코드 만료 시간과 맞춤)

    # 데이터베이스 설정 (Vercel Postgres/Neon 환경변수도 자동 인식)
    DATABASE_URL: str = resolve_database_url()

    # 한국조폐공사 OpenAPI 설정
    KOREA_MINTING_API_URL: str = os.getenv(
        "KOREA_MINTING_API_URL",
        "https://apis.data.go.kr/B552576/localGiftCardService/getMerchantList"
    )
    # 공공데이터포털 서비스키 (Dotenv 로드)
    KOREA_MINTING_SERVICE_KEY: str = os.getenv("KOREA_MINTING_SERVICE_KEY", "")

    # 국세청 사업자등록정보 진위확인 API 설정 (Dotenv 로드)
    NTS_API_KEY: str = os.getenv("NTS_API_KEY", "")

settings = Settings()
