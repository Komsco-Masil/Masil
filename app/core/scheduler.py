import asyncio
import logging
import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.invite import StoreInvite

logger = logging.getLogger("scheduler")

async def expire_unused_invites_job():
    """24시간이 경과한 미사용 초대 코드를 만료(삭제) 처리하는 백그라운드 태스크"""
    while True:
        try:
            db: Session = SessionLocal()
            now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            
            # expires_at이 현재 시간보다 이전이고, 사용되지 않은(is_used == False) 초대 코드를 삭제
            deleted_count = db.query(StoreInvite).filter(
                StoreInvite.is_used == False,
                StoreInvite.expires_at < now
            ).delete()
            
            if deleted_count > 0:
                db.commit()
                logger.info(f"[Scheduler] Expired and deleted {deleted_count} unused invite codes.")
            else:
                db.commit()
            
            db.close()
        except Exception as e:
            logger.error(f"[Scheduler] Error running invite expiration job: {e}")
            
        # 1시간(3600초)마다 반복 실행
        await asyncio.sleep(3600)

def start_scheduler():
    """FastAPI 구동 시 스케줄러 백그라운드 태스크 시작"""
    logger.info("[Scheduler] Starting background invite expiration scheduler...")
    asyncio.create_task(expire_unused_invites_job())
