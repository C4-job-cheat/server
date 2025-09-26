# 데이터베이스 구조 (Firestore)

## 주요 컬렉션 구조

### 1. users (컬렉션)

```
users/{userId}
├─ email: string                     // 로그인 이메일
├─ email_verified: boolean           // 이메일 인증 여부
├─ display_name: string | null       // 사용자 표시 이름 (없으면 null)
├─ last_login_at: timestamp          // 마지막 로그인 시각
├─ created_at: timestamp             // 문서 생성 시각
└─ updated_at: timestamp             // 최근 업데이트 시각
```

### 2. users/{userId}/personas (하위 컬렉션)

```
users/{userId}/personas/{personaId}
├─ user_id: string                    // 소유자 Firebase UID
├─ job_category: string               // 희망 직군 (필수)
├─ job_role: string | null            // 희망 직무 (선택)
├─ school_name: string | null         // 졸업/재학 학교 (선택)
├─ major: string | null               // 전공 (선택)
├─ skills: string[]                   // 보유 기술 목록 (선택)
├─ certifications: string[]           // 자격증 목록 (선택)
├─ core_competencies: object[]        // 직군별 핵심 역량 (자동 생성)
├─ html_file_path: string             // 업로드한 HTML 파일 경로
├─ html_content_type: string          // HTML MIME 타입
├─ html_file_size: number             // HTML 파일 크기 (bytes)
├─ json_file_path: string             // 변환된 JSON 파일 경로
├─ json_content_type: string          // JSON MIME 타입
├─ json_file_size: number             // JSON 파일 크기 (bytes)
├─ conversations_count: number        // 대화 기록 수
├─ html_file_deleted: boolean         // HTML 파일 삭제 여부
├─ competency_evaluation: {           // 역량 평가 결과(중첩 객체)
│    scores: object                   // 역량 ID별 점수 맵
│    evaluated_at: timestamp          // 평가 완료 시각
│    version: string                  // 평가 파이프라인 버전
│    model: string | null             // (선택) 사용한 모델명
│    system_prompt_version: string | null // (선택) 시스템 프롬프트 버전
│    details: object[] | null         // (선택) 평가 근거 로그 목록
│  }
├─ created_at: timestamp              // 문서 생성 시각
└─ updated_at: timestamp              // 최근 업데이트 시각
```

### 3. job_postings (컬렉션)

```
job_postings/{jobPostingId}
├─ company_name: string
├─ company_logo: string                // 회사 로고 URL
├─ title: string
├─ job_category: string
├─ job_title: string
├─ hires_count: number
├─ job_description: string
├─ requirements: string[]
├─ preferred: string[]
├─ required_qualifications: string[]
├─ preferred_qualifications: string[]
├─ ideal_candidate: string[]          // 인재상 7문항
├─ work_conditions: {
│    employment_type: string
│    location: string
│    position: string
│  }
├─ benefits: string[]
├─ registration_date: string
├─ application_deadline: string
└─ required_competencies: {           // 핵심 역량 5종 점수
     expertise: number
     potential: number
     problem_solving: number
     collaboration: number
     adaptability: number
   }
```

### 4. users/{userId}/personas/{personaId}/cover_letters (하위 컬렉션)

```
users/{userId}/personas/{personaId}/cover_letters/{coverLetterId}
├─ company_name: string
├─ strength: string
├─ experience: string
├─ style: string
├─ writing_rationale: string
├─ final_draft: string
├─ char_count: number
└─ updated_at: string
```

### 5. users/{userId}/personas/{personaId}/interview_sessions (하위 컬렉션)

```
users/{userId}/personas/{personaId}/interview_sessions/{sessionId}
├─ user_id: string
├─ cover_letter_id: string
├─ overall_analysis: object
├─ feedback: object
└─ final_score: object
```

### 6. users/{userId}/personas/{personaId}/interview_sessions/{sessionId}/questions (하위 컬렉션)

```
users/{userId}/personas/{personaId}/interview_sessions/{sessionId}/questions/{questionId}
├─ order: number
├─ question_text: string
├─ question_purpose: string
├─ answer_tips: string
├─ user_answer: object
└─ analysis: object
```

### 7. recommendations (컬렉션)

```
recommendations/{recommendationId}
├─ job_posting_id: string
├─ recommendation_score: number
└─ reason_summary: object
```

### 8. scraps (컬렉션)

```
scraps/{scrapId}
├─ user_id: string
├─ persona_id: string
└─ job_posting_id: string
```

## 🔄 주요 변경 사항

- 기존 `personas/{user_id}/inputs/{document_id}` 구조에서 `users/{user_id}/personas/{persona_id}` 계층 구조로 개편했습니다.
- 사용자 문서 아래에 페르소나·커버레터·인터뷰 데이터를 하위 컬렉션으로 정리해 관리 효율을 높였습니다.
- HTML 원본 업로드와 JSON 변환 파일 정보를 함께 저장하여 이력 추적을 강화했습니다.
- `job_category` 기반으로 `core_competencies` 를 자동 생성하도록 구조를 확장했습니다.
- JSON 변환 정보(`json_file_path`, `json_content_type`, `json_file_size`, `conversations_count`, `html_file_deleted`)를 추가하여 파이프라인 상태를 추적합니다.

## 💾 페르소나 문서 예시

```json
{
  "user_id": "firebase_uid_123",
  "job_category": "소프트웨어 개발",
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
      "description": "요구사항을 모듈·데이터 단위로 구조화해 해결하는 역량"
    },
    {
      "id": "JG_07_C02",
      "name": "구현 정확성",
      "description": "언어·알고리즘을 활용해 기능을 정확히 구현하는 능력"
    },
    {
      "id": "JG_07_C03",
      "name": "디버깅",
      "description": "운영·가설·테스트 루프를 통해 이슈를 해결하는 역량"
    },
    {
      "id": "JG_07_C04",
      "name": "학습 민첩성",
      "description": "새로운 기술을 빠르게 습득하고 적용하는 자세"
    },
    {
      "id": "JG_07_C05",
      "name": "업무 규범",
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
  "competency_evaluation": {
    "scores": {
      "문제 분해": 4,
      "구현 정확성": 5,
      "디버깅": 4,
      "학습 민첩성": 3,
      "업무 규범": 5
    },
    "evaluated_at": "2025-01-27T11:00:00.000000Z",
    "version": "v1.0",
    "model": "gemini-1.5-pro",
    "system_prompt_version": "2025-01-15",
    "details": [
      {
        "competency_id": "JG_07_C01",
        "score": 4,
        "reasoning": "요구사항을 단계적으로 분해한 사례 다수",
        "confidence": 0.78
      }
      // ... 추가 역량 세부 설명 생략 ...
    ]
  },
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```

### 최소 입력 예시 (job_category + html_file 필수 제공)

```json
{
  "user_id": "firebase_uid_123",
  "job_category": "디자이너",
  "job_role": "",
  "school_name": "",
  "major": "",
  "skills": [],
  "certifications": [],
  "core_competencies": [
    {
      "id": "JG_10_C01",
      "name": "문제 분석",
      "description": "사용자 문제를 요약하고 이해하는 역량"
    },
    {
      "id": "JG_10_C02",
      "name": "시각 구현력",
      "description": "아이디어를 시각 요소로 명확히 구현하는 크래프트 능력"
    },
    {
      "id": "JG_10_C03",
      "name": "데이터 해석",
      "description": "사용자·비즈니스 데이터를 근거로 인사이트를 도출하는 역량"
    },
    {
      "id": "JG_10_C04",
      "name": "도구 활용",
      "description": "디자인 시스템·에디터 도구를 효과적으로 활용하는 정도"
    },
    {
      "id": "JG_10_C05",
      "name": "공감·창의성",
      "description": "사용자 맥락을 반영해 새로운 해결책을 제안하는 능력"
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
  "competency_evaluation": null,
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```

## 🧠 Additional Fields: competency_scores

- `competency_evaluation` (object): 역량 평가 결과를 담는 중첩 객체.
- `competency_evaluation.scores` (object): 역량 이름(e.g. `문제 분해`)을 키로 하는 점수 맵.
- `competency_evaluation.evaluated_at` (timestamp): 최신 RAG 평가 시각 (ISO 포맷).
- `competency_evaluation.version` (string): 파이프라인 버전(e.g. `v1.0`).
- `competency_evaluation.model` (string, optional): 점수 산출에 사용된 Gemini 모델명.
- `competency_evaluation.system_prompt_version` (string, optional): 평가에 사용된 시스템 프롬프트 버전.
- `competency_evaluation.details` (array, optional): 평가 근거·추론 스냅샷 목록.

## 🧾 Collection: user_vector_embeddings

```
user_vector_embeddings/{userId}
├─ embeddings: [{ conversation_id, content, embedding[], competency_tags[], created_at }]
├─ metadata: { total_conversations, last_updated, embedding_model }
└─ created_at: timestamp
```

> 😊 참고: 모든 문서는 UTF-8로 저장되며, 필드명은 Firestore 규약을 따릅니다.
