from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base
from app.api import api_router
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

import sys
import logging

logger = logging.getLogger(__name__)


def ensure_avatar_url_column() -> None:
    if not inspect(engine).has_table("users"):
        return

    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    migrations = {
        "username": "ALTER TABLE users ADD COLUMN username VARCHAR(50)",
        "display_name": "ALTER TABLE users ADD COLUMN display_name VARCHAR(50)",
        "avatar_url": "ALTER TABLE users ADD COLUMN avatar_url TEXT",
    }

    for column_name, statement in migrations.items():
        if column_name not in columns:
            with engine.begin() as connection:
                connection.execute(text(statement))

    with engine.begin() as connection:
        connection.execute(text("UPDATE users SET username = nickname WHERE username IS NULL"))
        connection.execute(text("UPDATE users SET display_name = nickname WHERE display_name IS NULL"))


def ensure_store_public_data_columns() -> None:
    if not inspect(engine).has_table("stores"):
        return

    columns = {column["name"] for column in inspect(engine).get_columns("stores")}
    timestamp_type = "DATETIME" if settings.DATABASE_URL.startswith("sqlite") else "TIMESTAMP"
    migrations = {
        "nts_verified": "ALTER TABLE stores ADD COLUMN nts_verified BOOLEAN NOT NULL DEFAULT 0",
        "gift_card_verified": "ALTER TABLE stores ADD COLUMN gift_card_verified BOOLEAN NOT NULL DEFAULT 0",
        "public_data_source": "ALTER TABLE stores ADD COLUMN public_data_source VARCHAR(120)",
        "verified_at": f"ALTER TABLE stores ADD COLUMN verified_at {timestamp_type}",
    }

    for column_name, statement in migrations.items():
        if column_name not in columns:
            with engine.begin() as connection:
                connection.execute(text(statement))


# 애플리케이션 시작 시 DB 테이블 자동 생성 (테스트 실행 중인 경우 제외)
if "pytest" not in sys.modules:
    try:
        Base.metadata.create_all(bind=engine)
        ensure_avatar_url_column()
        ensure_store_public_data_columns()
    except Exception as e:
        logging.warning(f"Default database connection failed. Skipping eager table creation: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "데이터베이스에 연결할 수 없습니다. DATABASE_URL 설정을 확인해주세요."},
    )


# API 라우터 등록
app.include_router(api_router, prefix=settings.API_V1_STR)

from app.core.scheduler import start_scheduler

@app.on_event("startup")
def startup_event():
    if "pytest" not in sys.modules:
        start_scheduler()


@app.get("/")
def read_root() -> dict:
    """메인 루트 엔드포인트"""
    return {
        "message": "Welcome to Masil API server",
        "docs_url": "/docs"
    }


@app.get(f"{settings.API_V1_STR}/health")
def health_check() -> dict:
    """DB 연결 상태를 확인하는 헬스체크 엔드포인트"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL 환경변수를 Vercel Postgres 또는 Neon URL로 설정해주세요.",
        ) from exc
