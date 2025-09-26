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
├── core_competencies: object[]         // 🎯 직군별 핵심 역량 (job_category 기반 자동 설정)
├── html_file_path: string             // 📄 업로드된 HTML 파일 경로
├── html_content_type: string           // 📄 HTML 파일 MIME 타입
├── html_file_size: number              // 📄 HTML 파일 크기 (bytes)
├── json_file_path: string              // 📄 변환된 JSON 파일 경로
├── json_content_type: string           // 📄 JSON 파일 MIME 타입
├── json_file_size: number              // 📄 JSON 파일 크기 (bytes)
├── conversations_count: number          // 📄 대화 수
├── html_file_deleted: boolean          // 📄 HTML 파일 삭제 여부
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
- **직군별 핵심 역량 자동 설정**: `job_category` 기반으로 `core_competencies` 필드 자동 추가
- JSON 변환 파일 정보 추가 (`json_file_path`, `json_content_type`, `json_file_size`, `conversations_count`, `html_file_deleted`)

## 📝 예시 데이터

### Persona 예시

```json
{
  "user_id": "firebase_uid_123",
  "job_category": "소프트웨어개발",
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
  "core_competencies": [
    {
      "id": "JG_07_C01",
      "name": "문제 분해",
      "description": "요구를 모듈·인터페이스로 구조화하는 역량"
    },
    {
      "id": "JG_07_C02",
      "name": "구현 역량",
      "description": "언어·알고리즘을 활용해 기능을 정확히 구현하는 역량"
    },
    {
      "id": "JG_07_C03",
      "name": "디버깅",
      "description": "재현·가설·검증 루프로 오류를 해결하는 역량"
    },
    {
      "id": "JG_07_C04",
      "name": "학습 지속성",
      "description": "새로운 기술을 습득·적용하는 태도"
    },
    {
      "id": "JG_07_C05",
      "name": "협업 규범",
      "description": "리뷰·커밋·이슈 관리를 준수하는 태도"
    }
  ],
  "html_file_path": "personas/user123/persona456/resume.html",
  "html_content_type": "text/html",
  "html_file_size": 2048576,
  "json_file_path": "personas/user123/persona456/resume.json",
  "json_content_type": "application/json",
  "json_file_size": 1024000,
  "conversations_count": 15,
  "html_file_deleted": true,
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```

### 최소 입력 예시 (job_category와 html_file만 제공)
```json
{
  "user_id": "firebase_uid_123",
  "job_category": "디자인",
  "job_role": "",
  "school_name": "",
  "major": "",
  "skills": [],
  "certifications": [],
  "core_competencies": [
    {
      "id": "JG_10_C01",
      "name": "문제 해석",
      "description": "사용자 문제와 제약을 정확히 읽어내는 역량"
    },
    {
      "id": "JG_10_C02",
      "name": "시각적 구현력",
      "description": "아이디어를 시각적으로 명확히 구현하는 크래프트 역량"
    },
    {
      "id": "JG_10_C03",
      "name": "디자인 설명",
      "description": "사용자·비즈니스 원리에 근거해 디자인을 설득하는 능력"
    },
    {
      "id": "JG_10_C04",
      "name": "일관성",
      "description": "디자인 시스템·가이드를 일관 적용하는 태도"
    },
    {
      "id": "JG_10_C05",
      "name": "공감·창의성",
      "description": "사용자 맥락을 반영해 새로운 해법을 제안하는 역량"
    }
  ],
  "html_file_path": "personas/user123/persona789/resume.html",
  "html_content_type": "text/html",
  "html_file_size": 1024000,
  "json_file_path": "personas/user123/persona789/resume.json",
  "json_content_type": "application/json",
  "json_file_size": 512000,
  "conversations_count": 8,
  "html_file_deleted": true,
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```
