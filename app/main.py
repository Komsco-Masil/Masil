from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine, Base
from app.api import api_router

import sys
import logging

# 애플리케이션 시작 시 DB 테이블 자동 생성 (테스트 실행 중인 경우 제외)
if "pytest" not in sys.modules:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logging.warning(f"Default database connection failed. Skipping eager table creation: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# API 라우터 등록
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root() -> dict:
    """메인 루트 엔드포인트"""
    return {
        "message": "Welcome to Masil API server",
        "docs_url": "/docs"
    }
