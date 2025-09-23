# Firebase Google 로그인 연동 + Firestore 사용자 동기화 가이드

## 목표
- 프런트엔드가 구글 로그인 완료 후 전달한 Firebase `idToken`을 백엔드에서 검증한다.
- 토큰에서 얻은 `uid` 및 프로필(claims)을 기반으로 Firestore `users` 컬렉션에 사용자 문서를 upsert한다.
- 모든 엔드포인트는 기본적으로 `FirebaseAuthentication`을 사용해 보호하며, 최초 로그인 시점에 동기화 엔드포인트를 한 번 호출해 사용자 정보를 저장한다.

## 어디에 구현할까? (권장 구조)
- `core/` → 공용 유틸리티/인증/서비스 레이어
  - 이미 `core.authentication.FirebaseAuthentication`이 존재하므로 유지한다.
  - Firestore 사용자 upsert 로직은 재사용성이 높으므로 `core/services` 하위 모듈로 두는 것을 권장한다.
    - 예: `job_cheat/core/services/firebase_users.py`
- `api/` → HTTP 엔드포인트(뷰/URL) 제공
  - 실제 동기화 엔드포인트(`POST /api/auth/sync/`)는 `api.views`에 추가하고, URL은 `api.urls`에 매핑한다.

즉, 인증 클래스와 데이터 접근 로직은 `core`, 엔드포인트는 `api`에 위치시키는 구성을 추천한다. 별도의 `auth` 앱을 신설하는 방식도 가능하지만, 현재 레포에는 `api` 앱이 존재하고 `auth/verify` 엔드포인트가 이미 `api` 내에 있으므로, 중복된 앱을 늘리지 않고 `api`에 통합하는 편이 단순하고 일관된다.

## 로컬 테스트 & 에뮬레이터 설정
- `.env`에 `FIREBASE_CREDENTIALS` 또는 `FIREBASE_CREDENTIALS_JSON`을 지정하고, 에뮬레이터를 사용할 경우 `FIRESTORE_EMULATOR_HOST=localhost:8080`처럼 호스트를 추가한다.
- Firebase CLI가 설치되어 있다면 `firebase emulators:start --only firestore --project $FIREBASE_PROJECT_ID`로 로컬 에뮬레이터를 실행한다. (다른 포트를 사용할 때는 `.env` 값과 일치하도록 조정한다.)
- 단위 테스트에서는 `unittest.mock.patch`로 `firebase_admin.initialize_app`과 `firestore.client`를 모킹해 네트워크 없이 `FIREBASE_DB`/`FIREBASE_INIT_ERROR` 흐름을 검증한다.

## Firestore 데이터 모델
- 컬렉션: `users`
- 문서 ID: Firebase `uid`
- 필드(예시):
  - `email`: string | null
  - `display_name`: string | null (claims.name)
  - `photo_url`: string | null (claims.picture)
  - `email_verified`: bool | null
  - `provider_id`: string | null (claims.firebase.sign_in_provider)
  - `last_login_at`: timestamp (서버 시간)
  - `created_at`: timestamp (최초 생성 시 한 번만 설정)
  - `updated_at`: timestamp (매 호출 시 갱신)

예시 문서:
```json
{
  "email": "user@example.com",
  "display_name": "Jane Doe",
  "photo_url": "https://.../avatar.png",
  "email_verified": true,
  "provider_id": "google.com",
  "last_login_at": "2025-09-22T01:23:45Z",
  "created_at": "2025-09-21T09:00:00Z",
  "updated_at": "2025-09-22T01:23:45Z"
}
```

## 엔드포인트 설계
- 메서드/경로: `POST /api/auth/sync/`
- 인증: `Authorization: Bearer <idToken>` (전역 `FirebaseAuthentication` 적용)
- 요청 바디: 없음 (토큰 claims로 처리)
- 응답(200): upsert 이후 사용자 프로필(일부 필드)
- 실패(503): Firestore 미초기화 등 서버 상태 이슈

## 구현 단계 (Step-by-step)
1) 서비스 모듈 추가 (`core/services/firebase_users.py`)
- 역할: claims → 사용자 dict 변환, Firestore upsert, 타임스탬프 관리
- 시그니처 예: `upsert_user_from_claims(claims: dict, db) -> dict`

2) 시리얼라이저 보강 (`api/serializers.py`)
- 응답용 스키마 추가(`FirebaseUserSerializer`), 필드: uid, email, display_name, photo_url, email_verified, provider_id, last_login_at 등

3) 뷰 추가 (`api/views.py`)
- `SyncFirebaseUserView(APIView)`
  - `permission_classes = [IsAuthenticated]`
  - `claims = request.user.claims`
  - `user_dict = upsert_user_from_claims(claims, settings.FIREBASE_DB)`
  - `return Response(serializer.data)`

4) URL 매핑 (`api/urls.py`)
- `path('auth/sync/', SyncFirebaseUserView.as_view(), name='api-auth-sync')`

5) 테스트 (`api/tests.py`)
- RequestFactory + `IsAuthenticated` 경로로 호출
- Firestore는 직접 호출하지 않고 mock 처리 (또는 Firebase Emulator 연결)
- 성공/실패 케이스(미초기화, 예외 발생) 커버

6) 예외/에러 처리
- `settings.FIREBASE_DB`가 `None`이면 503 반환
- 예외 발생 시 400 또는 500대 상태코드와 메시지 반환

## 코드 스니펫 (참고용)
- 서비스 함수 (요지):
```py
# job_cheat/core/services/firebase_users.py
from django.utils import timezone

def _coerce_profile_from_claims(claims: dict) -> dict:
    firebase_info = (claims or {}).get("firebase") or {}
    return {
        "uid": claims.get("uid"),
        "email": claims.get("email"),
        "display_name": claims.get("name"),
        "photo_url": claims.get("picture"),
        "email_verified": claims.get("email_verified"),
        "provider_id": firebase_info.get("sign_in_provider"),
    }


def upsert_user_from_claims(claims: dict, db):
    if db is None:
        raise RuntimeError("Firestore is not initialized")

    ts = timezone.now()
    profile = _coerce_profile_from_claims(claims)
    uid = profile.get("uid")
    if not uid:
        raise ValueError("Missing uid in claims")

    doc_ref = db.collection("users").document(uid)
    snap = doc_ref.get()

    payload = {
        "email": profile["email"],
        "display_name": profile["display_name"],
        "photo_url": profile["photo_url"],
        "email_verified": profile["email_verified"],
        "provider_id": profile["provider_id"],
        "last_login_at": ts,
        "updated_at": ts,
    }

    if not snap.exists:
        payload["created_at"] = ts
        doc_ref.set(payload)
    else:
        doc_ref.update(payload)

    payload["uid"] = uid
    return payload
```

- 뷰 (요지):
```py
# job_cheat/api/views.py
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.services.firebase_users import upsert_user_from_claims
from .serializers import FirebaseUserSerializer

class SyncFirebaseUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            claims = getattr(request.user, "claims", {})
            data = upsert_user_from_claims(claims, settings.FIREBASE_DB)
            return Response(FirebaseUserSerializer(data).data)
        except RuntimeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

- URL (요지):
```py
# job_cheat/api/urls.py
from django.urls import path
from .views import VerifyFirebaseIdTokenView, SyncFirebaseUserView

urlpatterns = [
    path("auth/verify/", VerifyFirebaseIdTokenView.as_view(), name="api-auth-verify"),
    path("auth/sync/", SyncFirebaseUserView.as_view(), name="api-auth-sync"),
]
```

- 시리얼라이저 (요지):
```py
# job_cheat/api/serializers.py
from rest_framework import serializers

class FirebaseUserSerializer(serializers.Serializer):
    uid = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    display_name = serializers.CharField(allow_null=True)
    photo_url = serializers.URLField(allow_null=True)
    email_verified = serializers.BooleanField(allow_null=True)
    provider_id = serializers.CharField(allow_null=True)
    last_login_at = serializers.DateTimeField(required=False)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
```

## 프런트엔드 연동 예시
- Google 로그인 성공 → `idToken` 획득 → 동기화 엔드포인트 호출
```ts
const idToken = await firebase.auth().currentUser?.getIdToken();
await fetch("/api/auth/sync/", {
  method: "POST",
  headers: { Authorization: `Bearer ${idToken}` },
});
```

## 설정/보안 체크리스트
- 환경변수: `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS`(경로) 또는 `FIREBASE_CREDENTIALS_JSON` 중 하나 설정
- PII 최소수집: 필요한 필드만 저장, 불필요한 민감정보 저장 금지
- 에뮬레이터/테스트: Firestore Emulator 또는 mock으로 테스트 분리
- 인덱스/규칙: 사용자 문서 접근 권한 최소화(본인만 읽기 등), 필요한 인덱스 정의

## 결론
- 인증은 `core`에, 엔드포인트는 `api`에 두고, Firestore 동기화 로직은 `core/services`로 분리하는 구성이 간결하고 재사용성이 높다.
- 추후 역할/권한, 세팅 페이지 등 확장이 필요하면 별도 `accounts`/`auth` 앱으로 리팩터링을 고려한다.
