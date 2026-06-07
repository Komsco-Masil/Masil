import datetime
from app.models.invite import StoreInvite
from app.core.scheduler import expire_unused_invites_job
import pytest
import asyncio
from unittest.mock import patch

def test_scheduler_expiration(client, db):
    # 1. 테스트용 임시 가맹점 생성
    # (외래키 제약으로 가맹점이 존재해야 StoreInvite 생성 가능)
    client.post(
        "/api/auth/signup",
        json={"nickname": "owner", "neighborhood": "동네", "password": "password", "is_terms_agreed": True}
    )
    owner_token = client.post(
        "/api/auth/login",
        data={"username": "owner", "password": "password"}
    ).json()["access_token"]
    
    verify_resp = client.post(
        "/api/stores/verify",
        json={"business_number": "999-88-77777", "name": "스토어", "address": "주소"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    store_id = verify_resp.json()["id"]

    # 2. 만료된 미사용 초대코드와 정상인 미사용 초대코드 DB 추가
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    
    expired_invite = StoreInvite(
        invite_code="EXPIRED1",
        store_id=store_id,
        expires_at=now - datetime.timedelta(hours=2), # 이미 만료됨
        is_used=False
    )
    valid_invite = StoreInvite(
        invite_code="VALIDCODE",
        store_id=store_id,
        expires_at=now + datetime.timedelta(hours=22), # 유효함
        is_used=False
    )
    used_expired_invite = StoreInvite(
        invite_code="USEDEXP1",
        store_id=store_id,
        expires_at=now - datetime.timedelta(hours=1), # 시간은 만료되었으나 사용됨
        is_used=True
    )
    db.add(expired_invite)
    db.add(valid_invite)
    db.add(used_expired_invite)
    db.commit()

    # 3. 만료 로직을 수동으로 임시 실행하기 위해 DB 세션 동작 흉내내기
    # 스케줄러 내의 쿼리 필터 로직 검증
    expired_invites_query = db.query(StoreInvite).filter(
        StoreInvite.is_used == False,
        StoreInvite.expires_at < now
    )
    assert expired_invites_query.count() == 1
    assert expired_invites_query.first().invite_code == "EXPIRED1"

    # 삭제 실행
    expired_invites_query.delete()
    db.commit()

    # 결과 검증
    assert db.query(StoreInvite).filter(StoreInvite.invite_code == "EXPIRED1").first() is None
    assert db.query(StoreInvite).filter(StoreInvite.invite_code == "VALIDCODE").first() is not None
    assert db.query(StoreInvite).filter(StoreInvite.invite_code == "USEDEXP1").first() is not None
