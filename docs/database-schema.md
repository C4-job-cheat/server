# 데이터베이스 구조 (Firestore)

## 🗂️ 컬렉션 구조

### 1. users (컬렉션)

```
users/{userId}
├── email: string                     // 로그인 이메일
├── email_verified: boolean           // 이메일 검증 여부
├── display_name: string | null       // 사용자 이름 (없으면 null)
├── last_login_at: timestamp          // 마지막 로그인 시각
├── created_at: timestamp             // 문서 생성 시각
└── updated_at: timestamp             // 최근 동기화 시각

```

### 2. users/{userId}/personas (하위 컬렉션)

```
users/{userId}/personas/{personaId}
├── user_id: string                    // 🔐 보안: 이 페르소나의 주인
├── job_category: string               // 📌 페르소나의 희망 직군 (필수)
├── job_role: string | null             // 📌 페르소나의 희망 직무 (선택사항)
├── school_name: string | null           // 🎓 졸업/재학 학교명 (선택사항)
├── major: string | null                 // 🎓 전공 (선택사항)
├── skills: string[]                     // 🛠️ 보유 기술 스택 (선택사항, 빈 배열 허용)
├── certifications: string[]           // 🏆 자격증 및 인증서 (선택사항, 빈 배열 허용)
├── html_file_path: string             // 📄 업로드된 HTML 파일 경로
├── html_content_type: string           // 📄 HTML 파일 MIME 타입
├── html_file_size: number              // 📄 HTML 파일 크기 (bytes)
├── created_at: timestamp               // 📅 문서 생성 시각
└── updated_at: timestamp               // 📅 최근 업데이트 시각
```

### 3. job_postings (컬렉션)

```
job_postings/{jobPostingId}
├── company_name: string
├── company_logo: string                 // 회사 로고 URL
├── title: string
├── job_category: string
├── job_title: string
├── hires_count: number
├── job_description: string
├── requirements: string[]
├── preferred: string[]
├── required_qualifications: string[]
├── preferred_qualifications: string[]
├── ideal_candidate: string[]              // 7. 인재상
├── work_conditions: {
│   ├── employment_type: string
│   ├── location: string
│   └── position: string
│   }
├── benefits: string[]
├── registration_date: string
├── application_deadline: string
└── required_competencies: {           // 7. 요구 5가지 역량의 점수
    ├── expertise: number
    ├── potential: number
    ├── problem_solving: number
    ├── collaboration: number
    └── adaptability: number
    }
```

### 4. users/{userId}/personas/{personaId}/cover_letters (하위 컬렉션)

```
users/{userId}/personas/{personaId}/cover_letters/{coverLetterId}
├── company_name: string
├── strength: string
├── experience: string
├── style: string
├── writing_rationale: string
├── final_draft: string
├── char_count: number
└── updated_at: string
```

### 5. users/{userId}/personas/{personaId}/interview_sessions (하위 컬렉션)

```
users/{userId}/personas/{personaId}/interview_sessions/{sessionId}
├── user_id: string
├── cover_letter_id: string
├── overall_analysis: object
├── feedback: object
└── final_score: object
```

### 6. users/{userId}/personas/{personaId}/interview_sessions/{sessionId}/questions (하위 컬렉션)

```
users/{userId}/personas/{personaId}/interview_sessions/{sessionId}/questions/{questionId}
├── order: number
├── question_text: string
├── question_purpose: string
├── answer_tips: string
├── user_answer: object
└── analysis: object
```

### 7. recommendations (컬렉션)

```
recommendations/{recommendationId}
├── job_posting_id: string
├── recommendation_score: number
└── reason_summary: object
```

### 8. scraps (컬렉션)

```
scraps/{scrapId}
├── user_id: string
├── persona_id: string
└── job_posting_id: string
```

## 🔄 주요 변경사항

### Before (기존)

- `personas/{user_id}/inputs/{document_id}` 구조 사용
- 별도의 `personas` 컬렉션에서 사용자별 페르소나 관리

### After (신규)

- `users/{user_id}/personas/{persona_id}` 구조로 변경
- 사용자 문서 하위에 페르소나 하위 컬렉션으로 계층적 구조
- HTML 파일 업로드 기능 추가
- 사용자별 여러 페르소나 생성 가능한 확장 가능한 구조

## 📝 예시 데이터

### Persona 예시

```json
{
  "user_id": "firebase_uid_123",
  "job_category": "개발자",
  "job_role": "백엔드 개발자",
  "school_name": "서울대학교",
  "major": "컴퓨터공학과",
  "skills": [
    "Python",
    "Django",
    "PostgreSQL",
    "Redis",
    "AWS"
  ],
  "certifications": [
    "AWS Solutions Architect",
    "Django Professional"
  ],
  "html_file_path": "personas/user123/persona456/resume.html",
  "html_content_type": "text/html",
  "html_file_size": 2048576,
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```

### 최소 입력 예시 (job_category와 html_file만 제공)
```json
{
  "user_id": "firebase_uid_123",
  "job_category": "디자이너",
  "job_role": "",
  "school_name": "",
  "major": "",
  "skills": [],
  "certifications": [],
  "html_file_path": "personas/user123/persona789/resume.html",
  "html_content_type": "text/html",
  "html_file_size": 1024000,
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```
