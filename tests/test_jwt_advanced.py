import pytest
from jose import jwt
from app.core.config import settings

def test_jwt_refresh_and_logout(client):
    # 1. 회원가입
    client.post(
        "/api/auth/signup",
        json={"nickname": "jwt_user", "neighborhood": "동네1", "password": "password", "is_terms_agreed": True}
    )

    # 2. 로그인 -> access_token과 refresh_token 수령 확인
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "jwt_user", "password": "password"}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    # 3. Access Token으로 보호된 API 호출 성공 테스트
    headers = {"Authorization": f"Bearer {access_token}"}
    store_verify_resp = client.post(
        "/api/stores/verify",
        json={"business_number": "123-45-00000", "name": "가게", "address": "주소"},
        headers=headers
    )
    assert store_verify_resp.status_code == 201

    # 4. Refresh Token으로 신규 Access/Refresh Token 발급 테스트
    refresh_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    assert "access_token" in refresh_data
    assert "refresh_token" in refresh_data
    
    new_access_token = refresh_data["access_token"]
    new_refresh_token = refresh_data["refresh_token"]

    # 5. 기존 Refresh Token 재사용 시도 -> (revoked 되었으므로) 401 Unauthorized
    fail_refresh_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert fail_refresh_resp.status_code == 401

    # 6. 로그아웃 API 호출 -> Access Token 블랙리스트 등록 및 모든 Refresh Token revoke
    logout_headers = {"Authorization": f"Bearer {new_access_token}"}
    logout_resp = client.post("/api/auth/logout", headers=logout_headers)
    assert logout_resp.status_code == 200

    # 7. 로그아웃된 Access Token으로 API 호출 시도 -> 401 Unauthorized (Blacklisted)
    fail_api_resp = client.post(
        "/api/stores/verify",
        json={"business_number": "123-45-11111", "name": "가게2", "address": "주소2"},
        headers=logout_headers
    )
    assert fail_api_resp.status_code == 401

    # 8. 로그아웃된 이후 새 Refresh Token으로 갱신 시도 -> 401 Unauthorized (Revoked)
    fail_refresh_after_logout = client.post(
        "/api/auth/refresh",
        json={"refresh_token": new_refresh_token}
    )
    assert fail_refresh_after_logout.status_code == 401
