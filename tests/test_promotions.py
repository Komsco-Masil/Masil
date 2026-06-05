from app.models.user import User
from app.models.store import Store, StoreUser
from app.models.promotion import Promotion

def test_promotion_crud(client, db):
    # 1. 회원가입 및 로그인 (사장님 계정)
    client.post(
        "/api/auth/signup",
        json={"nickname": "owner_user", "neighborhood": "동네1", "password": "password", "is_terms_agreed": True}
    )
    owner_token = client.post(
        "/api/auth/login",
        data={"username": "owner_user", "password": "password"}
    ).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. 가맹점 인증 (사장 권한 격상 및 가맹점 등록)
    verify_resp = client.post(
        "/api/stores/verify",
        json={"business_number": "111-22-33333", "name": "마실카페", "address": "망원동"},
        headers=owner_headers
    )
    store_id = verify_resp.json()["id"]

    # 3. 홍보글 작성 성공
    promo_resp = client.post(
        "/api/promotions/",
        json={"store_id": store_id, "title": "오픈 이벤트", "content": "커피 1+1 행사 진행합니다!"},
        headers=owner_headers
    )
    assert promo_resp.status_code == 201
    promo_data = promo_resp.json()
    assert promo_data["title"] == "오픈 이벤트"
    assert promo_data["content"] == "커피 1+1 행사 진행합니다!"
    promo_id = promo_data["id"]

    # 4. 일반 유저(권한 없음) 가입 및 로그인 후 생성 시도 -> 403 Forbidden
    client.post(
        "/api/auth/signup",
        json={"nickname": "normal_user", "neighborhood": "동네2", "password": "password", "is_terms_agreed": True}
    )
    normal_token = client.post(
        "/api/auth/login",
        data={"username": "normal_user", "password": "password"}
    ).json()["access_token"]
    normal_headers = {"Authorization": f"Bearer {normal_token}"}

    fail_resp = client.post(
        "/api/promotions/",
        json={"store_id": store_id, "title": "해킹글", "content": "홍보글 해킹시도"},
        headers=normal_headers
    )
    assert fail_resp.status_code == 403

    # 5. 전체/필터 목록 조회
    list_resp = client.get("/api/promotions/")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    list_filter_resp = client.get(f"/api/promotions/?store_id={store_id}")
    assert list_filter_resp.status_code == 200
    assert len(list_filter_resp.json()) == 1

    list_empty_resp = client.get("/api/promotions/?store_id=9999")
    assert list_empty_resp.status_code == 200
    assert len(list_empty_resp.json()) == 0

    # 6. 상세 조회
    detail_resp = client.get(f"/api/promotions/{promo_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["title"] == "오픈 이벤트"

    # 7. 수정 성공
    update_resp = client.put(
        f"/api/promotions/{promo_id}",
        json={"title": "오픈 이벤트 변경", "content": "커피 1+2 행사 진행합니다!"},
        headers=owner_headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "오픈 이벤트 변경"
    assert update_resp.json()["content"] == "커피 1+2 행사 진행합니다!"

    # 8. 일반 유저 수정 시도 -> 403 Forbidden
    fail_update_resp = client.put(
        f"/api/promotions/{promo_id}",
        json={"title": "해킹 수정"},
        headers=normal_headers
    )
    assert fail_update_resp.status_code == 403

    # 9. 삭제 성공
    delete_resp = client.delete(f"/api/promotions/{promo_id}", headers=owner_headers)
    assert delete_resp.status_code == 200
    
    # 10. 조회 시 404
    get_fail_resp = client.get(f"/api/promotions/{promo_id}")
    assert get_fail_resp.status_code == 404
