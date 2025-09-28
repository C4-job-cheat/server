# API 명세서 목록

이 디렉토리는 Job Cheat 백엔드 API의 상세 명세서를 포함합니다.

## 인증 관련 API

### [POST /api/auth/verify/](auth-verify.md)
- Firebase ID 토큰 검증
- 사용자 클레임 정보 반환

### [POST /api/auth/sync/](auth-sync.md)
- Firebase 사용자 정보를 Firestore에 동기화
- 새 사용자 생성 또는 기존 사용자 업데이트

## 기능별 API

### Personas (페르소나 관리)

#### [POST /api/personas/inputs/](persona-input.md)
- 페르소나 기본 정보와 HTML 파일 업로드
- Firestore에 페르소나 메타데이터 저장

#### [GET /api/personas/health/](personas-health.md)
- Personas 앱 상태 확인

### Cover Letters (자기소개서)

#### [GET /api/cover-letters/health/](cover-letters-health.md)
- Cover Letters 앱 상태 확인

### Interviews (모의면접)

#### [GET /api/interviews/health/](interviews-health.md)
- Interviews 앱 상태 확인

### Job Search (채용 공고 검색)

#### [GET /api/job-search/health/](job-search-health.md)
- Job Search 앱 상태 확인

## 공통 사항

### 인증
- 모든 API는 Firebase ID 토큰 기반 인증을 사용합니다.
- 요청 헤더에 `Authorization: Bearer <firebase-id-token>`을 포함해야 합니다.

### 응답 형식
- 성공 응답: JSON 형태의 데이터
- 오류 응답: `{"detail": "오류 메시지"}` 형태

### 상태 코드
- `200 OK`: 성공
- `201 Created`: 리소스 생성 성공
- `400 Bad Request`: 요청 데이터 오류
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 없음
- `500 Internal Server Error`: 서버 오류
- `503 Service Unavailable`: 서비스 이용 불가

## 개발 환경 설정

### 로컬 개발 서버 실행
```bash
cd job_cheat
uv run python manage.py runserver 0.0.0.0:8000
```

### Firebase 토큰 테스트
```bash
# 토큰 검증
curl -X POST http://localhost:8000/api/auth/verify/ \
  -H "Authorization: Bearer <firebase-id-token>"

# 사용자 동기화
curl -X POST http://localhost:8000/api/auth/sync/ \
  -H "Authorization: Bearer <firebase-id-token>"
```

## 관련 문서

- [데이터베이스 스키마](../database-schema.md)
- [아키텍처 개요](../ARCHITECTURE.md)
- [Firebase 인증 가이드](../firebase-auth-firestore-user-sync.md)
