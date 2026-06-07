from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# SQLite 연결 시 멀티스레드 지원을 위한 설정 적용
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# DB 세션 의존성 주입을 위한 제너레이터 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
