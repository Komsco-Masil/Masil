import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.deps import get_db
from app.core.database import Base

# 임시 SQLite 테스트 DB 파일 경로
TEST_DB_URL = "sqlite:///./test_temp.db"

# 테스트 전용 데이터베이스 엔진 및 세션 생성
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """테스트마다 독립된 DB 스키마를 제공하는 Fixture"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()  # Windows 환경에서 파일이 고정되는 것을 방지하기 위해 엔진 연결 해제
        if os.path.exists("./test_temp.db"):
            try:
                os.remove("./test_temp.db")
            except Exception:
                pass


@pytest.fixture(scope="function")
def client(db):
    """DB 의존성이 테스트 DB 세션으로 교체된 TestClient를 제공하는 Fixture"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
