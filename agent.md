# 📋 프로젝트 마실 - FastAPI 백엔드 개발 에이전트 로그

## 🚀 최신 업데이트 일자
- **일시**: 2026-06-06 (현재 시간 기준)
- **요약**: 국세청 사업자등록정보 진위확인 API 연동 구현 완료 및 17개 단위 테스트 100% 통과


---

## ✅ 완료된 작업 (Done)
- [x] **SQLAlchemy 2.0 모델 정의**: `app/models/` 디렉토리에 `User`, `Store`, `StoreUser`, `StoreInvite` 모델 선언 및 관계(relationship) 정의 완료.
- [x] **Pydantic V2 스키마 작성**: `app/schemas/` 디렉토리에 가입/로그인 및 인증을 위한 데이터 스키마 작성 완료. `is_terms_agreed` 필드가 `False`인 경우 즉각 400 Bad Request를 반환하는 커스텀 전처리(`@field_validator`) 적용.
- [x] **조폐공사 Mock 클라이언트 구축**: `app/services/giftcard_client.py`에 조폐공사 가맹점 대조용 모의 클라이언트 `LocalGiftCardClient` 구현 완료 (성공, 대조 실패, 타임아웃, 일반 오류 시뮬레이션 지원).
- [x] **핵심 비즈니스 로직 API 구현 완료**:
  - `POST /api/auth/signup`: 회원가입 API (LOCAL 일반 비밀번호 해싱 및 OAuth 정보 기록 처리).
  - `POST /api/auth/login`: 테스트 자격 증명 교환용 JWT 토큰 생성 API.
  - `POST /api/stores/verify`: 조폐공사 대조 API 호출 및 성공 시 OWNER 역할 격상. 타임아웃/오류 시 500 에러를 반환하지 않고 `is_manual_review=True` 플래그를 세워 임시 승인 처리하는 예외 대응 로직 포함.
  - `POST /api/stores/invites`: OWNER 전용 24시간 만료 무작위 직원 초대 코드 생성 API.
  - `POST /api/stores/invites/use`: 일반 직원이 초대 코드를 등록하여 EMPLOYEE 권한을 부여받는 API.
  - `DELETE /api/stores/employees/{employee_id}`: OWNER가 가맹점 직원의 연동을 끊는 API (직원이 다른 가게와도 연동되어 있지 않다면 자동으로 USER 역할로 강등).
- [x] **보안 모듈 개선**: passlib 라이브러리의 bcrypt v4.x 호환성 에러(72바이트 한계 예외)를 우회하기 위해 `bcrypt` 라이브러리를 직접 사용하도록 비밀번호 해싱/검증 모듈 리팩토링 완료.
- [x] **버전 경고 클리닝**: Python 3.12+ 이상 버전에서 Deprecated된 `datetime.utcnow()`를 `datetime.now(timezone.utc).replace(tzinfo=None)` 방식으로 전면 교체하여 IDE 및 Pytest 경고를 제거함.
- [x] **조폐공사 실 연동 구현**: `app/services/giftcard_client.py`를 비동기 HTTP 호출 방식(`httpx.AsyncClient`)으로 개편하여 실제 한국조폐공사 가맹점 오픈 API 연동 완료.
- [x] **환경 변수 보안 관리**: `.env.example` 작성 및 `app/core/config.py` 설정을 통해 공공데이터 API 서비스 키 보안 관리 설계 완료.
- [x] **API 비동기화 및 테스트 통과**: 가맹점 검증 라우터를 비동기(`async/await`) 함수로 리팩토링하고 13개 단위 테스트 검증(100% 통과) 완료.
- [x] **국세청 사업자등록정보 진위확인 API 연동 및 사용자 인증 시스템 구현**:
  - `app/services/nts_client.py`에 비동기 `NTSBusinessClient` 구현 (개인사업자 대조 연동).
  - `.env` 및 `app/core/config.py`에 `NTS_API_KEY` 연동.
  - `/api/stores/verify` 엔드포인트를 NTS API 검증 로직으로 개편하여 정보 일치 시 `OWNER` 격상 및 `StoreUser` 매핑 등록.
  - 외부 API 타임아웃 또는 서버 장애 발생 시 `is_manual_review=True`로 자동 임시 승인 및 관리자 수동 검토 안내 메시지 반환 구현 완료.
  - 관련 신규 케이스를 포함한 총 17개 단위 테스트를 수행하여 100% 검증 완료.

---

## 🚧 진행 중인 작업 (In Progress)
- [ ] 현재 MEM-01 ~ MEM-04 백엔드 핵심 기능 개발이 완료되었으며, 기능적 리팩토링 및 린트 오류 등 디버깅 작업이 안정적으로 완료되어 대기 중입니다.

---

## 📅 다음 진행할 작업 (To-Do)
1. [x] **JWT 토큰 정책 고도화**: 만료 및 토큰 무효화(Blacklist) 기법 및 Refresh Token 로직 연동 설계.
2. [x] **배치 스케줄러 도입**: 24시간이 경과한 미사용 `StoreInvite` 초대 코드의 만료 처리를 자동화하는 스케줄러 배치 설계.
3. [x] **가게 홍보 게시판 (PROMOTION) CRUD 개발**: 다음 마일스톤인 홍보 게시판 라우터, DB 모델 및 비즈니스 로직 개발 시작.

---

## 🚨 이슈 및 특이사항 (Issues)
- **외부 API 오류 예외 대응**: 외부 연동 API가 타임아웃되더라도 500 Internal Server 오류가 발생하지 않도록 차단하고, `is_manual_review=True` 상태의 가맹점을 생성하여 비즈니스 흐름을 유지하고 추후 수동 검토하도록 설계 정책을 정립하였습니다.
- **BCrypt 및 Datetime 경고 해결**: passlib 72바이트 버그 및 파이썬 UTC 시간 취득 표준 경고를 해결하여 최신의 클린한 코드를 확보했습니다.
