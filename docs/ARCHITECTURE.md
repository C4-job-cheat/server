## 앱 아키텍처 개요

이 프로젝트는 API 전용 백엔드로, 기능(도메인)별 앱으로 분리되어 있습니다. 모든 엔드포인트는 `api/<feature>/...` 경로로 노출되며, 전역 인증은 `core.authentication.FirebaseAuthentication`를 사용합니다.

- **전역 인증/공용 모듈**: `core`
- **기능 앱**: `personas`, `cover_letters`, `interviews`, `job_search`
- **프로젝트 라우팅**: `job_cheat/job_cheat/urls.py`에서 각 기능 앱의 `urls.py`를 `api/<feature>/` 하위로 include

---

## 앱별 역할과 기능

### core
- **역할**: 전역 인증/공용 유틸 보관. 현재 Firebase idToken 기반 인증 클래스 제공.
- **주요 기능**:
  - `FirebaseAuthentication`: `Authorization: Bearer <idToken>` 검증
  - `FirebaseUser`: DRF 권한체크용 사용자 객체

### personas
- **역할**: 사용자(지원자) 페르소나 생성/관리 API 제공.
- **예상 기능**:
  - 입력 이력/목표 직무 기반 페르소나 생성
  - 페르소나 조회/수정/버전 관리
  - 결과 캐싱 및 이력 관리(Firestore 등)

### cover_letters
- **역할**: 자기소개서(자소서) 생성/편집/추천 API 제공.
- **예상 기능**:
  - JD/페르소나 기반 자소서 초안 생성
  - 항목별 개선 제안 및 리라이팅
  - 버전/히스토리 관리, 내보내기

### interviews
- **역할**: 모의면접 시나리오/질문 생성과 답변 평가 API 제공.
- **예상 기능**:
  - 직무/경력 기반 질문 리스트 생성
  - 대화형 모의면접 세션, 답변 피드백/스코어링
  - 세션 기록/리뷰

### job_search
- **역할**: 채용 공고 탐색/집계/추천 API 제공.
- **예상 기능**:
  - 외부 채용 사이트/검색 API 연동(Provider 패턴)
  - 필터/정렬/저장(북마크)/이력 관리
  - 페르소나/자소서와 연계 추천

---

## 라우팅

- 프로젝트 레벨(`job_cheat/job_cheat/urls.py`):
  - `api/personas/` → `personas.urls`
  - `api/cover-letters/` → `cover_letters.urls`
  - `api/interviews/` → `interviews.urls`
  - `api/job-search/` → `job_search.urls`

- 기본 인증/권한(전역):
  - `DEFAULT_AUTHENTICATION_CLASSES = ["core.authentication.FirebaseAuthentication"]`
  - `DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]`

---

## 현재 디렉터리 트리(요약)

```text
job_cheat/
  core/
    __init__.py
    authentication.py
  personas/
    __init__.py
    apps.py
    urls.py
    views.py
  cover_letters/
    __init__.py
    apps.py
    urls.py
    views.py
  interviews/
    __init__.py
    apps.py
    urls.py
    views.py
  job_search/
    __init__.py
    apps.py
    urls.py
    views.py
  job_cheat/
    settings.py
    urls.py
```

---

## 개발 가이드

- 공용 로직은 `core/`에 추가하고, 기능별 비즈니스 로직은 각 앱에서 자급자족합니다.
- 각 앱은 다음 구조로 확장하는 것을 권장합니다.

```text
<feature_app>/
  urls.py         # 엔드포인트 라우팅
  views.py        # 얇은 컨트롤러(입출력/권한)
  serializers.py  # 입력/출력 스키마(필요 시)
  services/       # 비즈니스 로직
  repositories/   # 데이터 접근(Firestore/외부 API 래퍼)
  tests/          # 단위/통합 테스트
```

- 모든 API는 기본적으로 Firebase 인증이 적용됩니다. 공개 엔드포인트는 뷰에서 `AllowAny`로 명시적으로 허용하세요.


