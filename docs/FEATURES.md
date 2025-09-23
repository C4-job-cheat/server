# 구현된 기능 요약

다음은 현재 저장소에 실제로 구현되어 있는 백엔드 기능(엔드포인트/인증/서비스)의 요약입니다. 모든 엔드포인트는 기본적으로 Firebase idToken 기반 인증을 요구합니다.

## 인증/보안
- 전역 인증: `core.authentication.FirebaseAuthentication` — `Authorization: Bearer <idToken>` 헤더의 Firebase idToken 검증 (Django REST framework와 연동)
  - 소스: `job_cheat/core/authentication.py`
- Firestore 초기화: 환경 변수 기반으로 Firebase Admin App 및 Firestore 클라이언트 초기화
  - 소스: `job_cheat/job_cheat/settings.py`
- CORS/CSRF: 로컬/사설망 및 ngrok 도메인 허용 규칙 구성
  - 소스: `job_cheat/job_cheat/settings.py`

## 공용 API (api)
- `POST /api/auth/verify/` — 전달된 idToken을 검증하고 주요 클레임(uid, email, provider 등)을 반환
  - 소스: `job_cheat/api/views.py`, `job_cheat/api/urls.py`
- `POST /api/auth/sync/` — 검증된 idToken의 클레임으로 Firestore `users/{uid}` 문서를 생성/갱신(upsert), 최신 프로필을 반환
  - 서비스 레이어: `job_cheat/core/services/firebase_users.py`
  - 시리얼라이저: `job_cheat/api/serializers.py`

## 기능 앱(헬스 체크 엔드포인트)
다음 기능 앱들은 현재 헬스 체크용 `GET /health/` 엔드포인트만 제공합니다(사업 로직/CRUD는 아직 미구현). 모든 엔드포인트는 기본 인증이 적용됩니다.

- Personas
  - `GET /api/personas/health/` → `{ ok: true, feature: "personas", uid }`
  - 소스: `job_cheat/personas/views.py`, `job_cheat/personas/urls.py`
- Cover Letters
  - `GET /api/cover-letters/health/` → `{ ok: true, feature: "cover_letters", uid }`
  - 소스: `job_cheat/cover_letters/views.py`, `job_cheat/cover_letters/urls.py`
- Interviews
  - `GET /api/interviews/health/` → `{ ok: true, feature: "interviews", uid }`
  - 소스: `job_cheat/interviews/views.py`, `job_cheat/interviews/urls.py`
- Job Search
  - `GET /api/job-search/health/` → `{ ok: true, feature: "job_search", uid }`
  - 소스: `job_cheat/job_search/views.py`, `job_cheat/job_search/urls.py`

## 전역 라우팅
- 프로젝트 URL 구성: `job_cheat/job_cheat/urls.py`
  - `/api/` 하위에 `api`, `personas`, `cover_letters`, `interviews`, `job_search` 앱 라우팅 포함

## 참고 (테스트/문서)
- 테스트 스켈레톤: `job_cheat/api/tests.py` (추가 테스트 필요)
- 아키텍처 개요: `docs/ARCHITECTURE.md`
- Firebase 인증·Firestore 사용자 동기화 가이드: `docs/firebase-auth-firestore-user-sync.md`

---

## 빠른 호출 예시
아래 요청은 유효한 Firebase idToken이 필요합니다.

```bash
# 1) idToken 검증
curl -X POST \
  -H "Authorization: Bearer <ID_TOKEN>" \
  http://localhost:8000/api/auth/verify/

# 2) Firestore 사용자 동기화
curl -X POST \
  -H "Authorization: Bearer <ID_TOKEN>" \
  http://localhost:8000/api/auth/sync/

# 3) 기능 앱 헬스 체크 (예: personas)
curl -X GET \
  -H "Authorization: Bearer <ID_TOKEN>" \
  http://localhost:8000/api/personas/health/
```

※ 인증을 해제한 공개 엔드포인트는 현재 없습니다. 공개 API가 필요하면 해당 뷰에서 `AllowAny`를 명시하세요.

