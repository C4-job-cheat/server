# Firebase ID 토큰 클레임 정리

Firebase Authentication이 발급하는 ID 토큰(`idToken`)은 JWT(JSON Web Token) 규격을 따르며, 사용자 인증 상태와 프로필 정보를 담은 **클레임(claim)** 키-값 쌍으로 구성됩니다. Firebase Admin SDK의 `DecodedIdToken` 타입을 기준으로 주요 항목과 의미를 정리했습니다.

## 1. 표준 JWT 클레임
- `iss`, `aud`: 토큰 발급자와 대상. 프로젝트가 올바른지 검증할 때 사용합니다.
- `sub`: 사용자 고유 식별자. Firebase `uid`와 동일하게 취급됩니다.
- `iat`, `exp`: 토큰 발급/만료 시각(Unix epoch). 만료 여부를 판단합니다.
- `auth_time`: 사용자가 인증을 완료한 시각. 강제 재인증이 필요한 보안 민감 작업에서 활용합니다.

## 2. Firebase 고유 클레임
- `uid`: Firebase 사용자 UID. `sub` 값과 동일합니다.
- `firebase`: Firebase 네임스페이스
  - `sign_in_provider`: 로그인 제공자(`google.com`, `password`, `apple.com` 등)
  - `identities`: 제공자별 사용자 식별자 딕셔너리
  - `sign_in_second_factor`, `second_factor_identifier`: 다단계 인증(MFA) 세부 정보(존재 시)
  - `tenant`: 멀티 테넌시 사용 시 테넌트 ID

## 3. 사용자 프로필 클레임(선택적)
- `email`, `email_verified`
- `phone_number`
- `picture`
- 그 외 제공자에서 전달하는 `name`, `locale` 등

## 4. 커스텀 클레임
- Admin SDK에서 `set_custom_user_claims`로 추가한 역할/권한 등 임의 키-값 쌍
- 예: `role: "admin"`, `plan: "premium"`
- 클라이언트가 변조할 수 없지만, 항상 서버에서 신뢰 검증 후 사용해야 합니다.

## 5. 참고 및 문헌
- Firebase Admin Node SDK `DecodedIdToken` 타입 정의(클레임 전체 목록)
  - <https://github.com/firebase/firebase-admin-node/blob/master/etc/firebase-admin.auth.api.md#_snippet_7>
- ID 토큰 검증 가이드
  - <https://firebase.google.com/docs/auth/admin/verify-id-tokens>

## 6. 프로젝트 적용 맥락
- `core.authentication.FirebaseAuthentication`이 `verify_id_token`으로 위 클레임을 검증한 뒤 `request.user.claims`에 저장합니다.
- `POST /api/auth/verify/` 엔드포인트는 주요 프로필 클레임(`uid`, `email`, `provider` 등)을 응답합니다.
- `POST /api/auth/sync/`는 클레임 데이터를 이용해 Firestore `users/{uid}` 문서를 생성/갱신합니다.

> **Tip**: 클레임 키는 표준/플랫폼/커스텀 값이 혼재하므로, 뷰나 서비스 단에서 존재 여부를 확인하고 안전하게 처리하세요.

