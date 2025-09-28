# JSON 파일 확인 도구 사용법

## 📋 개요

Firebase Storage에 저장된 페르소나 JSON 파일들을 확인하고 분석하는 개발용 도구입니다. HTML 파일이 ChatGPT 대화 형식으로 변환되었는지 확인하고, 변환된 JSON 데이터의 구조와 내용을 분석할 수 있습니다.

## 🚀 설치 및 실행

### 필수 조건
- Django 프로젝트가 설정되어 있어야 함
- Firebase Storage 연결이 설정되어 있어야 함
- `uv` 패키지 매니저 사용

### 실행 방법
```powershell
# job_cheat 디렉토리에서 실행
cd job_cheat
uv run python check_json_files.py [인자들]
```

## 📖 사용법

### 1. 기본 사용법

#### 파일 목록 조회
```powershell
uv run python check_json_files.py <user_id>
```

**예시:**
```powershell
uv run python check_json_files.py test_user_postman
```

**출력 예시:**
```
🔍 사용자 test_user_postman의 파일 목록 조회 중...
📁 HTML 파일: 0개
📄 JSON 파일: 1개
  - users/test_user_postman/json/abc123-def456-ghi789.json (1,234,567 bytes)
    생성일: 2024-01-15 10:30:45
    수정일: 2024-01-15 10:30:45
```

#### 특정 JSON 파일 내용 확인
```powershell
uv run python check_json_files.py <user_id> <document_id>
```

**예시:**
```powershell
uv run python check_json_files.py test_user_postman abc123-def456-ghi789
```

**출력 예시:**
```
📥 JSON 파일 다운로드 중: abc123-def456-ghi789
✅ JSON 파일 다운로드 성공!
  - 경로: users/test_user_postman/json/abc123-def456-ghi789.json
  - 크기: 1,234,567 bytes
  - 타입: application/json

📊 JSON 내용 분석:
  - 총 대화 수: 5
  - 총 메시지 수: 127

🔍 JSON 구조 정보:
  - 최상위 키들: ['conversations', 'total_conversations', 'total_messages']
  - 대화 객체 키들: ['title', 'messages', 'created_at']

💬 첫 번째 대화 미리보기:
  - 제목: Python 프로그래밍 질문
  - 메시지 수: 25
  - 메시지 객체 키들: ['role', 'content', 'timestamp']
  - 첫 메시지: 안녕하세요! Python으로 웹 개발을 시작하려고 하는데...
```

### 2. 고급 사용법

#### 파일 목록만 조회
```powershell
uv run python check_json_files.py <user_id> list
```

#### JSON 파일을 로컬에 저장
```powershell
uv run python check_json_files.py <user_id> save <document_id> [output_file]
```

**예시:**
```powershell
# 기본 파일명으로 저장
uv run python check_json_files.py test_user_postman save abc123-def456-ghi789

# 사용자 지정 파일명으로 저장
uv run python check_json_files.py test_user_postman save abc123-def456-ghi789 my_chat_data.json
```

**저장 위치:**
- 기본 파일명: `downloaded_{user_id}_{document_id}.json`
- 저장 경로: 스크립트 실행 디렉토리

## 🔧 매개변수 설명

### 필수 매개변수

| 매개변수 | 설명 | 예시 |
|---------|------|------|
| `user_id` | Firebase Storage에서 파일을 조회할 사용자 ID | `test_user_postman` |

### 선택 매개변수

| 매개변수 | 설명 | 예시 |
|---------|------|------|
| `document_id` | 확인할 JSON 파일의 문서 ID | `abc123-def456-ghi789` |
| `list` | 파일 목록만 조회하는 명령 | `list` |
| `save` | JSON 파일을 로컬에 저장하는 명령 | `save` |
| `output_file` | 저장할 로컬 파일명 (선택사항) | `my_data.json` |

## 📊 출력 정보

### 파일 목록 조회 시
- HTML 파일 개수 및 목록
- JSON 파일 개수 및 목록
- 각 파일의 크기, 생성일, 수정일

### JSON 파일 분석 시
- 파일 메타데이터 (경로, 크기, 타입)
- JSON 구조 정보 (키 목록)
- 대화 통계 (총 대화 수, 총 메시지 수)
- 첫 번째 대화 미리보기 (제목, 메시지 수, 첫 메시지 내용)

## 🎯 사용 사례

### 1. 개발 과정에서 변환 확인
```powershell
# HTML 파일 업로드 후 변환 결과 확인
uv run python check_json_files.py test_user_postman
```

### 2. 특정 파일 상세 분석
```powershell
# 특정 JSON 파일의 내용을 자세히 확인
uv run python check_json_files.py test_user_postman abc123-def456-ghi789
```

### 3. 로컬에서 데이터 분석
```powershell
# JSON 파일을 로컬에 저장하여 외부 도구로 분석
uv run python check_json_files.py test_user_postman save abc123-def456-ghi789 analysis_data.json
```

## ⚠️ 주의사항

1. **인증 필요**: Firebase Storage에 접근하려면 적절한 인증이 설정되어 있어야 합니다.
2. **파일 크기**: 대용량 JSON 파일의 경우 다운로드에 시간이 걸릴 수 있습니다.
3. **네트워크 연결**: Firebase Storage에 접근하려면 인터넷 연결이 필요합니다.
4. **권한**: 해당 사용자의 파일에만 접근할 수 있습니다.

## 🐛 문제 해결

### 일반적인 오류

#### `TypeError: unsupported format string passed to NoneType.__format__`
- **원인**: Firebase Storage에서 파일 크기가 `None`으로 반환됨
- **해결**: 스크립트가 자동으로 처리하므로 무시해도 됨

#### `JSON 파일을 찾을 수 없습니다`
- **원인**: 잘못된 `user_id` 또는 `document_id` 사용
- **해결**: 파일 목록 조회로 올바른 ID 확인

#### `Firebase Storage 연결 실패`
- **원인**: Firebase 설정 문제 또는 네트워크 연결 문제
- **해결**: Firebase 설정 확인 및 네트워크 연결 상태 점검

## 📝 예시 시나리오

### 시나리오 1: 새로운 사용자의 파일 확인
```powershell
# 1. 파일 목록 확인
uv run python check_json_files.py new_user_123

# 2. 특정 파일 내용 확인
uv run python check_json_files.py new_user_123 doc456-789-abc

# 3. 로컬에 저장하여 분석
uv run python check_json_files.py new_user_123 save doc456-789-abc new_user_data.json
```

### 시나리오 2: 대용량 파일 처리
```powershell
# 1. 파일 목록으로 크기 확인
uv run python check_json_files.py user_with_large_files

# 2. 큰 파일을 로컬에 저장
uv run python check_json_files.py user_with_large_files save large_doc123 large_file.json
```

## 🔗 관련 파일

- **스크립트 위치**: `job_cheat/check_json_files.py`
- **관련 서비스**: `job_cheat/core/services/firebase_storage.py`
- **ChatGPT 변환기**: `job_cheat/core/services/chatgpt_converter.py`

## 📞 지원

문제가 발생하거나 추가 기능이 필요한 경우 개발팀에 문의하세요.
