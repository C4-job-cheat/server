
### Firebase 서비스 계정 키 얻는 방법
- Firebase 콘솔 → 프로젝트 설정 → 서비스 계정 → “새 비공개 키 생성”
- 내려받은 JSON을
  - 방법 1: 파일로 보관하고 `.env`의 `FIREBASE_CREDENTIALS`에 파일 경로 기입
  - 방법 2: JSON 내용을 한 줄로 변환해 `FIREBASE_CREDENTIALS_JSON`에 그대로 기입
- 둘 중 하나만 설정하세요. 둘 다 비우면 ADC(Application Default Credentials)를 시도합니다.

### ADC(대안)
- GCP 환경 또는 로컬 gcloud 로그인 사용 시:
```powershell
gcloud auth application-default login
```
- 이 경우 `.env`에서 `FIREBASE_CREDENTIALS`, `FIREBASE_CREDENTIALS_JSON`를 비워두면 됩니다. `FIREBASE_PROJECT_ID`만 채워주세요.

### 보안 유의
- `.env`는 절대 커밋하지 마세요. 이미 `.gitignore`에 포함되어 있어야 합니다.
- 서비스 계정 키는 팀 공유 저장소가 아닌 안전한 비밀 저장소(예: 1Password, Vault 등)에 보관하세요.

### 적용 후 실행
```powershell
cd C:\Users\JHSHIN\ProgrammingCodes\team-project\job-cheat
uv sync
uv run python manage.py runserver 0.0.0.0:8000
```

- 프론트에서 받은 Firebase ID 토큰을 `POST /api/auth/verify/`에 전송하면 서버에서 검증하여 `uid`, `email`, `provider` 등을 응답합니다.
