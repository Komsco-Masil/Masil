from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine, Base
from app.api import api_router
from sqlalchemy import inspect, text

import sys
import logging

# 애플리케이션 시작 시 DB 테이블 자동 생성 (테스트 실행 중인 경우 제외)
if "pytest" not in sys.modules:
    try:
        Base.metadata.create_all(bind=engine)
        if settings.DATABASE_URL.startswith("sqlite"):
            columns = {column["name"] for column in inspect(engine).get_columns("users")}
            if "avatar_url" not in columns:
                with engine.begin() as connection:
                    connection.execute(text("ALTER TABLE users ADD COLUMN avatar_url TEXT"))
    except Exception as e:
        logging.warning(f"Default database connection failed. Skipping eager table creation: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
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
