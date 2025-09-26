# 저장소 가이드라인

## 필수 요구사항
- 한국어로 답변
- 한국어로 .md 확장자의 문서 
- 코드 주석 한글로 작성
- 이모지 및 한글 잘 표현되는 utf-8 인코딩 항상 유지


## 프로젝트 구조 및 모듈 구성
- `job_cheat/`에는 Django 프로젝트 루트(`manage.py`, `pyproject.toml`, 공용 Firebase 구성 파일)가 위치한다.
- `job_cheat/job_cheat/`에는 프로젝트 설정(`settings.py`), URL 라우팅, ASGI/WSGI 엔트리 포인트가 들어 있다. Django 데이터베이스 설정 대신 이곳에서 Firebase 자격 증명과 Firestore 클라이언트를 구성한다.
- `job_cheat/api/`는 `/api/auth/verify/`, `/api/auth/sync/`와 같은 HTTP 엔드포인트(뷰 + URL)를 제공한다.
- `job_cheat/core/`에는 `FirebaseAuthentication`과 Firestore 연동 서비스 모듈(예: `core/services/firebase_users.py`) 등 공용 유틸리티가 포함된다.
- 기능 앱은 `job_cheat/` 하위에 위치하며(`personas/`, `cover_letters/`, `interviews/`, `job_search/` 등), 각자의 URL, 뷰, 템플릿을 캡슐화한다.
- 재사용 가능 자산(템플릿, 정적 파일)은 앱 단위 폴더에 저장하고, 생성 파일·서비스 계정 키·기타 비밀 정보는 커밋하지 않는다.

## 환경 및 도구
- Python 3.12+를 목표로 하며, `uv venv`로 환경을 만들고 개발 전에 생성된 가상환경을 활성화한다.
- 의존성은 `pyproject.toml`에 정의하고 `uv sync`로만 설치·잠근다(`pip` 사용 금지).
- Firebase 서비스 계정 자격 증명과 기타 로컬 설정은 환경 변수 또는 Git에 무시되는 `.env`에 보관한다.

## 빌드, 테스트, 개발 명령
- `uv run python manage.py runserver 0.0.0.0:8000` → Firestore 클라이언트를 로드한 채 수동 테스트용 개발 서버를 실행한다.
- `uv run python manage.py shell_plus`(설치된 경우) 또는 `uv run python manage.py shell` → Firestore 데이터 접근 패턴을 안전하게 탐색한다.
- Firestore 데이터 모델은 Django ORM 밖에 있으므로 `migrate`/`createsuperuser`는 생략하고, Firebase Admin SDK나 Firebase Console로 컬렉션을 관리한다.

## 코딩 스타일 및 네이밍 규칙
- 4칸 들여쓰기의 PEP 8을 따르며, 줄 길이는 88자 이내로 유지해 `black`과 호환되게 한다.
- 함수·모듈은 `snake_case`, 모델·폼은 `PascalCase`, 정적 자산은 케밥 케이스를 사용한다.
- 뷰별 템플릿은 각 앱 아래에 함께 배치한다(예: `personas/templates/personas/`, `cover_letters/templates/cover_letters/`). `api` 앱은 JSON 엔드포인트를 제공하며 일반적으로 템플릿이 없다.

## 테스트 가이드라인
- Django `TestCase`(또는 request factory 유틸리티)로 단위 테스트를 작성한다. 앱 단위 테스트는 각 앱 폴더 하위(예: `personas/tests.py`, `personas/tests/`)에 배치하고, API 엔드포인트 테스트는 `api/tests.py`에 추가한다.
- Pull Request를 열기 전에 `uv run python manage.py test`를 실행한다. 뷰, Firestore 서비스 계층, 입력을 처리하는 폼에 높은 커버리지를 목표로 한다.
- 각 앱의 `tests/fixtures/`에 저장된 팩토리나 픽스처를 사용해 테스트를 결정적으로 유지하고, Firestore 클라우드 상태에 의존하지 말며 에뮬레이터나 모킹을 활용한다.

## 커밋 및 Pull Request 가이드라인
- 커밋 메시지는 명령형(`Add job board search view`)으로 작성하고 72자 이하를 유지한다. 필요 시 `Refs #id`로 이슈를 참조한다.
- Pull Request는 집중도를 유지하고, 변경 사항을 설명하며, Firestore 보안 규칙·인덱스 업데이트를 명확히 하고, UI 또는 API 변경 시 스크린샷이나 cURL 스니펫을 첨부한다.
- 테스트 증거(명령 출력 또는 커버리지 요약)를 포함하고, 후속 작업이 있으면 PR 설명에 표시한다.

## 보안 및 구성 팁
- API 키나 자격 증명을 커밋하지 않는다. 비밀은 환경 변수로 로드하고 필요할 때 `settings.py`에서 읽도록 업데이트한다.
- Firestore 보안 규칙과 인덱스 변경 사항을 신중히 검토하고, 프로덕션 배포 전에 스테이징 프로젝트에서 테스트한다.
