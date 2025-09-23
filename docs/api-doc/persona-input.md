# Persona HTML 입력 업로드 API

## 개요
- 사용자 페르소나 기본 정보와 HTML 파일을 업로드해 Firestore에 메타데이터를 저장하고 Firebase Storage에 파일을 기록합니다.
- Firestore 문서는 `personas/{user_id}/inputs/{document_id}` 경로에 생성되며, HTML 파일은 동일한 `document_id`를 사용해 `personas/{user_id}/inputs/{document_id}.html` 경로로 업로드합니다.

## 엔드포인트
- 메서드: `POST`
- 경로: `/api/personas/inputs/`
- URL name: `personas-input-create`

## 인증
- 헤더 `Authorization: Bearer <firebase-id-token>` 필수
- 토큰이 없거나 검증에 실패하면 401 또는 403으로 응답합니다.

## 요청
### 헤더
| 헤더 | 필수 | 설명 |
| --- | --- | --- |
| Authorization | ✅ | Firebase ID 토큰, 예시: `Bearer eyJhbGciOi...` |
| Content-Type | ✅ | `multipart/form-data`

### 폼 필드
| 필드 | 타입 | 필수 | 제약 및 설명 |
| --- | --- | --- | --- |
| persona_name | string | ✅ | 최대 60자, 공백 전용 문자열 불가 |
| job_category | string | ✅ | 최대 80자, ex) "프론트엔드" |
| job_role | string | ✅ | 최대 100자, ex) "시니어 프론트엔드 엔지니어" |
| school_name | string | ✅ | 예) "서울대학교" |
| major | string | ✅ | 예) "컴퓨터공학과" |
| skills | string[] / string | ✅ | 최소 1개 이상, 쉼표 구분 문자열 또는 JSON 배열 허용 |
| html_file | file | ✅ | MIME `text/html` 또는 `application/xhtml+xml`, 최대 5MB |

### 요청 예시
```bash
curl -X POST https://api.example.com/api/personas/inputs/ \
  -H "Authorization: Bearer <firebase-id-token>" \
  -F "persona_name=취업 전환 준비생" \
  -F "job_category=프론트엔드" \
  -F "job_role=시니어 프론트엔드 엔지니어" \
  -F "school_name=서울대학교" \\
  -F "major=컴퓨터공학과" \\
  -F "skills=React,TypeScript,Firebase" \
  -F "html_file=@/path/to/profile.html;type=text/html"
```

## 응답
### 201 Created
- 헤더: `Location: /api/personas/inputs/{document_id}`
- 본문:
```json
{
  "id": "b0a8d4c6-2b11-4f2b-9011-2a4d8c9c6b1a",
  "persona_name": "취업 전환 준비생",
  "job_category": "프론트엔드",
  "job_role": "시니어 프론트엔드 엔지니어",
  "school_name": "서울대학교",
  "major": "컴퓨터공학과",
  "skills": ["React", "TypeScript", "Firebase"],
  "html_file_path": "personas/user-123/inputs/b0a8d4c6-2b11-4f2b-9011-2a4d8c9c6b1a.html",
  "html_content_type": "text/html",
  "html_file_size": 48321,
  "created_at": "2024-05-21T12:30:00Z",
  "updated_at": "2024-05-21T12:30:00Z"
}
```

### 오류 응답
| 상태 코드 | 설명 | 예시 메시지 |
| --- | --- | --- |
| 400 Bad Request | 요청 데이터 검증 실패 | `{"skills": ["최소 한 개 이상의 기술이 필요합니다."]}` |
| 401 Unauthorized / 403 Forbidden | Firebase 인증 실패 또는 권한 없음 | `{"detail": "자격 증명이 유효하지 않습니다."}` |
| 413 Payload Too Large | 파일 크기가 허용 범위를 초과 | `{"detail": "HTML 파일은 최대 5MB까지 업로드할 수 있습니다."}` |
| 500 Internal Server Error | Firestore/Storage 저장 중 예외 발생 | `{"detail": "페르소나 입력을 저장할 수 없습니다: ..."}` |

## 비고
- Storage 버킷은 환경 변수 `FIREBASE_STORAGE_BUCKET`으로 지정합니다. 미설정 시 Firebase 기본 버킷을 사용합니다.
- `skills`는 쉼표로 구분된 문자열을 자동 분리하거나 JSON 배열 그대로 처리합니다.
- 업로드된 파일은 응답에 포함되지 않으며, 필요 시 `html_file_path`로 Firebase Storage에서 다운로드 URL을 생성해야 합니다.



