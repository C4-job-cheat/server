# Firebase Auth & Firestore 사용자 동기화 체크리스트

## Phase 0 - 환경 준비
- [x] Firebase Admin SDK 구성이 `job_cheat/job_cheat/settings.py`에서 환경 변수 기반으로 `FIREBASE_DB`를 초기화하는지 확인한다.
- [x] 로컬 `.env`에 `FIREBASE_PROJECT_ID`와 `FIREBASE_CREDENTIALS`(또는 JSON 변형)가 포함되어 있고 VCS에서 제외되는지 확인한다.
- [x] 테스트용 Firestore 에뮬레이터 또는 모킹 전략이 문서화되어 있으며 쉽게 접근 가능한지 검증한다.

## Phase 1 - 코어 서비스 계층
- [x] 클레임 정규화와 Firestore upsert 도우미를 포함하도록 `job_cheat/core/services/firebase_users.py`를 생성하거나 확장한다.
- [x] `FIREBASE_DB`가 `None`일 때 의미 있는 오류를 발생시켜 Firestore 클라이언트 누락을 방어한다.
- [x] `created_at`, `updated_at`, `last_login_at` 타임스탬프는 `timezone.now()`를 사용하고, `created_at`은 최초 삽입 시 한 번만 설정되도록 보장한다.

## Phase 1.1 - Firebase 클레임 기반 회원가입 저장 계획
- [x] `docs/claim.md`와 `docs/database-schema.md`를 기준으로 회원가입 시 저장할 필수 클레임 필드를 확정한다.
  - 후보: `uid`, `email`, `email_verified`, `firebase.sign_in_provider`, `name`, `picture`(미존재 시 `None`).
- [x] `docs/database-schema.md`의 `users` 컬렉션 정의를 갱신해 최종 사용자 스키마(예: `email`, `name`, `provider_id`, `email_verified`, `photo_url`, `created_at`, `updated_at`, `last_login_at`)를 반영한다.
- [x] `_coerce_profile_from_claims`에서 선택한 클레임만 추출하고 기본값(공백/`None`) 설정 로직을 추가한다.
- [x] `upsert_user_from_claims`에서 Firestore `users/{uid}` 문서에 위 스키마만 저장하도록 payload를 정리한다.
- [x] `FirebaseUserSerializer` 필드를 동일 스키마로 정렬하고 응답에 불필요한 키가 노출되지 않도록 `to_representation`을 검증한다.
  - 필드 구성: `uid`, `email`, `display_name`, `photo_url`, `email_verified`, `provider_id`, `last_login_at`, `created_at`, `updated_at`.
- [x] 회원가입 최초 호출 시 `created_at`이 설정되고 이후 호출에서는 유지되는지, `last_login_at`이 매번 갱신되는지 테스트 시나리오를 설계한다.
  - 시나리오: (1) 신규 토큰 → 문서 생성 + `created_at`/`last_login_at` 동일, (2) 동일 토큰 재호출 → `created_at` 유지 및 `last_login_at`/`updated_at` 갱신.
- [x] 커스텀 클레임 또는 미사용 필드는 Firestore에 저장하지 않도록 화이트리스트 검증을 구현한다.

## Phase 2 - API 직렬화 및 검증
- [x] `job_cheat/api/serializers.py`에 uid, 프로필, 공급자, 타임스탬프 필드를 포함하는 `FirebaseUserSerializer`를 추가한다.
- [x] 직렬화기가 이메일, photo_url 등 선택적이거나 null인 클레임 데이터를 무리 없이 처리하는지 확인한다.

## Phase 3 - API 엔드포인트 구현
- [x] `job_cheat/api/views.py`에 `IsAuthenticated`와 `FirebaseAuthentication`으로 보호되는 `SyncFirebaseUserView`를 구현한다.
- [x] `request.user.claims`와 Firestore 클라이언트를 사용해 `upsert_user_from_claims`를 호출하고, 성공 시 직렬화된 응답을 반환한다.
- [x] Firestore 초기화 문제는 503 응답으로 노출하고, 기타 오류는 안전한 400대 응답으로 변환한다.
- [x] 기존 인증 라우트와 함께 `job_cheat/api/urls.py`에 `POST /api/auth/sync/`를 등록한다.

## Phase 4 - 자동화 테스트
- [ ] 정상 케이스, uid 누락, Firestore 초기화 실패를 다루는 단위 테스트를 `job_cheat/api/tests.py`에 추가한다.
- [ ] 테스트의 결정성을 유지하기 위해 Firestore 상호작용과 타임스탬프 생성을 모킹한다.
- [ ] DRF RequestFactory나 API 클라이언트 유틸리티를 사용해 인증 강제를 검증한다.

## Phase 5 - 프런트엔드 및 문서 후속 작업
- [ ] `idToken`을 활용한 `fetch` 예제 등 프런트엔드 연동 스니펫을 프로젝트 문서나 개발자 README에 제공한다.
- [ ] PII 최소 수집과 Firestore 규칙 변경 사항을 강조하도록 보안 체크리스트를 갱신한다.
- [ ] `uv run python manage.py test` 실행, 엔드포인트 스모크 테스트 등 수동 확인 절차를 릴리스 전 기록한다.
