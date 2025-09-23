# 데이터베이스 구조 (Firestore)

## 🗂️ 컬렉션 구조

### 1. users (컬렉션)

```
users/{userId}
├── email: string                     // 로그인 이메일
├── email_verified: boolean           // 이메일 검증 여부
├── display_name: string | null       // 사용자 이름 (없으면 null)
├── photo_url: string | null          // 프로필 이미지 URL
├── provider_id: string | null        // Firebase 로그인 제공자 ID
├── last_login_at: timestamp          // 마지막 로그인 시각
├── created_at: timestamp             // 문서 생성 시각
└── updated_at: timestamp             // 최근 동기화 시각

```

### 2. users/{userId}/personas (하위 컬렉션)

```
users/{userId}/personas/{personaId}
├── user_id: string                    // 🔐 보안: 이 페르소나의 주인
├── job_category: string               // 📌 페르소나의 희망 직군
├── job_title: string                  // 📌 페르소나의 희망 직무 (선택사항)
├── skills: string[]                   // 🛠️ 보유 기술 스택 및 자격증
├── competency_scores: {               // 📊 최종 계산된 5대 역량 점수
│   ├── expertise: number
│   ├── potential: number
│   ├── problem_solving: number
│   ├── collaboration: number
│   └── adaptability: number
│   }
├── competency_reasons: {              // 🎯 각 역량 점수의 이유/근거
│   ├── expertise: string
│   ├── potential: string
│   ├── problem_solving: string
│   ├── collaboration: string
│   └── adaptability: string
│   }
└── ai_analysis_summary: string        // 🤖 AI 종합 분석 요약
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

- evaluations 하위 컬렉션에서 개별 질문별 점수 저장
- 페르소나 완성 시 evaluations 데이터를 취합하여 최종 점수 계산

### After (신규)

- evaluations 하위 컬렉션 제거
- 페르소나 문서에 직접 최종 점수와 이유 저장
- 더 간단하고 효율적인 구조

## 📝 예시 데이터

### Persona 예시

```json
{
  "user_id": "KJH_user_id",
  "job_category": "IT개발·데이터",
  "job_title": "백엔드 개발자",
  "skills": [
    "Java",
    "Spring Boot",
    "Python",
    "Node.js",
    "AWS",
    "정보보안기사",
    "정보처리기사"
  ],
  "competency_scores": {
    "expertise": 85,
    "potential": 90,
    "problem_solving": 75,
    "collaboration": 80,
    "adaptability": 95
  },
  "competency_reasons": {
    "expertise": "컴퓨터공학 전공, Python/Node.js 3년 경험, AWS 자격증 보유로 기술적 역량이 우수함",
    "potential": "최근 Nest.js 학습, 지속적인 기술 트렌드 관심, 명확한 커리어 목표 설정으로 성장 가능성이 높음",
    "problem_solving": "프로젝트 중 발생한 기술적 문제를 체계적으로 분석하고 해결한 경험 다수 보유",
    "collaboration": "팀 프로젝트에서 백엔드 리드 역할 수행, 갈등 상황에서 데이터 기반 설득으로 해결",
    "adaptability": "기존 Java에서 Node.js로 전환, 새로운 프레임워크 학습 및 적용 경험 풍부"
  },
  "ai_analysis_summary": "종합적으로 적응력(95점)과 성장 잠재력(90점)이 가장 뛰어난 강점으로 평가됩니다..."
}
```
