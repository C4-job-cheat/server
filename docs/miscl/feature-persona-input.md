# persona 폼 입력 Firestore 저장 체크리스트

## 아키텍처 개요
- [x] 엔드포인트는 `POST /api/personas/inputs/`로 정의하고 `personas/urls.py`에 URL name `personas-input-create`로 등록
- [x] Django 뷰는 `FirebaseAuthentication` 기반 인증 후 요청 본문을 `PersonaInputSerializer`에 전달하도록 설계
- [x] Firestore 경로는 `personas/{user_id}/inputs/{document_id}` 구조를 사용해 사용자별 persona 입력을 그룹화
- [x] 문서 ID는 `uuid4`로 생성하고 Firestore `created_at`, `updated_at`는 서버 타임스탬프로 기록

## 요청/응답 계약 정의
- [x] 클라이언트 요청 헤더에 `Authorization: Bearer <firebase-id-token>` 강제, 미제공 시 401/403 응답
- [x] 요청 JSON 스키마를 다음과 같이 문서화하고 유효성 검사에 반영
  ```json
  {
    "persona_name": "취업 전환 준비생",
    "experience_summary": "3년차 프론트엔드 개발자로서 ...",
    "target_role": "시니어 프론트엔드 엔지니어",
    "goals": ["리액트 숙련도 강조", "AI 협업 경험 언급"],
    "challenges": "테스트 자동화 경험 부족",
    "skills": ["React", "TypeScript", "Firebase"],
    "tone_preferences": "전문적이되 따뜻한 어조",
    "additional_context": {
      "company": "잡치트",
      "industry": "HR Tech"
    }
  }
  ```
- [x] 선택 필드(`tone_preferences`, `additional_context`)는 누락 시 기본값 처리, 필수 필드는 공백 문자열 허용 금지
- [x] 성공 응답은 201 상태 코드와 함께 Firestore 문서 ID·타임스탬프를 반환
  ```json
  {
    "id": "b0a8d4c6-...",
    "created_at": "2024-05-21T12:30:00Z",
    "persona_name": "취업 전환 준비생"
  }
  ```
- [x] 에러 응답 케이스 정의: 400(검증 실패), 401/403(인증·권한 오류), 500(Firestore 예외)
- [ ] OpenAPI 스키마에 요청/응답 예시와 오류 코드 표 추가 (`schema/personas.yaml` 또는 DRF Spectacular 활용)

## Django 엔드포인트 구현
- [x] `personas/urls.py`에 `path("inputs/", views.PersonaInputCreateView.as_view(), name="personas-input-create")` 추가
- [x] 뷰 클래스는 `APIView` 또는 `GenericAPIView`를 상속하고 `permission_classes=[IsAuthenticated]`, `authentication_classes=[FirebaseAuthentication]` 지정
- [x] 뷰 내부에서 파일 업로드 후 `firebase_personas.save_user_persona_input(user_id=user_id, payload=serializer.to_firestore_payload(...), document_id=document_id)` 호출
- [x] 저장 완료 후 serializer의 `to_representation` 사용해 응답 본문 구성

## Serializer 및 검증 로직
- [x] `personas/api/serializers.py`에 `PersonaInputSerializer` 생성, `serializers.Serializer` 기반 필드 정의
  ```python
  class PersonaInputSerializer(serializers.Serializer):
      persona_name = serializers.CharField(max_length=60)
      experience_summary = serializers.CharField()
      target_role = serializers.CharField(max_length=80)
      goals = serializers.ListField(child=serializers.CharField(), allow_empty=False)
      challenges = serializers.CharField(allow_blank=True, required=False)
      skills = serializers.ListField(child=serializers.CharField(), allow_empty=True)
      tone_preferences = serializers.CharField(max_length=120, required=False, allow_blank=True)
      additional_context = serializers.DictField(child=serializers.CharField(), required=False)
  ```
- [x] `validate_skills` 등 커스텀 검증기로 공백 값 제거, 대소문자 정규화 처리
- [x] `additional_context` 딕셔너리에 허용 키 목록(`company`, `industry`, `note`) 검증 로직 추가
- [ ] Firestore 저장 필드와 serializer 필드 매핑 표 작성해 문서화 (`persona_name -> personaName`, 등)
- [ ] 향후 버전 확장을 위해 serializer `Meta.version = "v1"` 등 버전 태그 부여를 고려

## Firestore 연동 로직
- [x] `core/services/firebase_personas.py`에 `save_user_persona_input(user_id: str, payload: dict) -> dict` 함수 작성
- [x] Firestore 클라이언트는 `job_cheat/core/firebase.py` 등 기존 초기화 모듈에서 import하여 재사용
- [x] 저장 시 다음 데이터 구조 유지
  ```python
  data = {
      "persona_name": payload["persona_name"],
      "experience_summary": payload["experience_summary"],
      "target_role": payload["target_role"],
      "goals": payload["goals"],
      "challenges": payload.get("challenges"),
      "skills": payload["skills"],
      "tone_preferences": payload.get("tone_preferences"),
      "additional_context": payload.get("additional_context", {}),
      "created_at": firestore.SERVER_TIMESTAMP,
      "updated_at": firestore.SERVER_TIMESTAMP,
  }
  ```
- [ ] Firestore 예외(`GoogleAPICallError`, `AlreadyExists`)를 캐치하여 로깅하고 `django.core.exceptions.ValidationError` 또는 503으로 매핑
- [ ] Firestore 호출 전후 로깅(`logger.info`)을 추가해 추적성 확보, PII는 마스킹 처리

## 테스트 및 검증
- [x] `personas/tests/test_views.py`에서 인증 토큰 모킹 및 성공/실패 플로우 테스트
- [x] `core/services/tests/test_firebase_personas.py`에서 Firestore 모킹(`mock.patch("firebase_admin.firestore.client")`)하여 저장 호출 확인
- [x] serializer 테스트: 필수 필드 누락, 리스트 빈 값, `additional_context` 키 제한 등 검증
- [x] `uv run python manage.py test personas`로 회귀 테스트, 필요 시 CI 파이프라인에 추가

## 문서화 및 후속 작업
- [ ] 엔드포인트 명세를 `docs/api/personas.md` 또는 사내 위키에 복사, 프런트엔드 팀 공유
- [ ] 환경 변수(`FIREBASE_PROJECT_ID`, `FIREBASE_PERSONA_COLLECTION` 등) 변화 여부 점검 및 `.env.example` 갱신
- [ ] Firestore 보안 규칙에 `match /personas/{userId}/inputs/{inputId}` 경로에 대한 쓰기 조건 추가 (`request.auth.uid == userId`)
- [ ] QA를 위해 Postman 컬렉션 또는 cURL 스크립트 준비, 예시 요청 저장


