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
├─ embedding_status: string           // 임베딩 상태 (queued/running/completed/failed)
├─ embedding_message: string          // 임베딩 상태 메시지
├─ embedding_error: string | null     // 임베딩 오류 메시지
├─ embedding_started_at: timestamp | null // 임베딩 시작 시각
├─ embedding_completed_at: timestamp | null // 임베딩 완료 시각
├─ embeddings_count: number           // 임베딩된 대화 수
├─ embedding_model: string | null     // 사용된 임베딩 모델
├─ has_embeddings: boolean            // 임베딩 존재 여부
├─ vectorized_competency_tags: string[] // 벡터화된 역량 태그들
├─ competencies: object               // 역량 평가 결과 (새로운 구조)
│   ├─ {competency_name}: {          // 역량별 평가 결과
│   │    score: number                // 역량 점수
│   │    score_explanation: string    // 점수 설명
│   │    key_insights: string[]       // 핵심 인사이트
│   │    evaluated_at: timestamp      // 평가 시각
│   │  }
│   └─ ...                           // 다른 역량들
├─ final_evaluation: string | null   // 최종 평가 결과
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
├─ user_id: string                    // 사용자 ID
├─ persona_id: string                // 페르소나 ID
├─ company_name: string               // 지원 회사 이름
├─ cover_letter: object[]            // 자기소개서 문단들
│   ├─ paragraph: string             // 문단 내용
│   └─ reason: string                // 문단 작성 이유
├─ style: string                     // 자기소개서 스타일 (experience/knowledge/creative)
├─ character_count: number           // 글자 수
├─ created_at: timestamp             // 생성 시각
└─ updated_at: timestamp             // 수정 시각
```

### 5. users/{userId}/personas/{personaId}/interview_sessions (하위 컬렉션)

```
users/{userId}/personas/{personaId}/interview_sessions/{sessionId}
├─ user_id: string                    // 사용자 ID
├─ persona_id: string                 // 페르소나 ID
├─ total_questions: number            // 총 질문 수
├─ total_time: number                 // 총 소요 시간 (초)
├─ average_answer_time: number        // 평균 답변 시간
├─ total_answers: number              // 총 답변 수
├─ average_answer_length: number      // 평균 답변 길이
├─ score: number                      // 총점
├─ grade: string                      // 등급 (A/B/C/D/E/F)
├─ status: string                     // 상태 (in_progress/completed)
├─ use_voice: boolean                 // 음성 면접 여부
├─ final_good_points: string[]        // 최종 잘한 점 목록
├─ final_improvement_points: string[] // 최종 개선할 점 목록
├─ created_at: timestamp              // 생성 시각
├─ updated_at: timestamp              // 수정 시각
└─ completed_at: timestamp | null     // 완료 시각
```

### 6. users/{userId}/personas/{personaId}/interview_sessions/{sessionId}/questions (하위 컬렉션)

```
users/{userId}/personas/{personaId}/interview_sessions/{sessionId}/questions/{questionId}
├─ question_id: string                // 질문 ID
├─ question_number: number            // 질문 번호
├─ question_type: string              // 질문 유형 (직무 지식/문제 해결 능력/프로젝트 경험/인성 및 가치관)
├─ question_text: string              // 질문 내용
├─ answer_text: string                // 답변 내용
├─ answer_length: number              // 답변 길이
├─ time_taken: number                 // 답변 소요 시간 (초)
├─ is_answered: boolean               // 답변 여부
├─ question_score: number             // 질문 점수
├─ good_points: string[]              // 잘한 점 목록
├─ improvement_points: string[]       // 개선할 점 목록
├─ sample_answer: string              // 모범 답변 예시
├─ question_intent: string[]          // 질문의 의도 목록
├─ created_at: timestamp              // 생성 시각
└─ updated_at: timestamp              // 수정 시각
```

### 7. users/{userId}/personas/{personaId}/recommendations (하위 컬렉션)

```
users/{userId}/personas/{personaId}/recommendations/{recommendationId}
├─ job_posting_id: string             // 공고 ID
├─ recommendation_score: number       // 추천 점수
├─ reason_summary: object             // 추천 이유 요약
│   ├─ match_points: string[]         // 일치하는 요소들
│   ├─ improvement_points: string[]   // 보완이 필요한 부분들
│   └─ growth_suggestions: string[]  // 성장 방향 제안들
└─ cover_letter: string               // 자기소개서 미리보기
```

### 8. scraps (컬렉션)

```
scraps/{scrapId}
├─ user_id: string                    // 사용자 ID
├─ persona_id: string                 // 페르소나 ID
└─ job_posting_id: string             // 공고 ID
```

## 🔄 주요 변경 사항

- 기존 `personas/{user_id}/inputs/{document_id}` 구조에서 `users/{user_id}/personas/{persona_id}` 계층 구조로 개편했습니다.
- 사용자 문서 아래에 페르소나·커버레터·인터뷰·추천 데이터를 하위 컬렉션으로 정리해 관리 효율을 높였습니다.
- HTML 원본 업로드와 JSON 변환 파일 정보를 함께 저장하여 이력 추적을 강화했습니다.
- `job_category` 기반으로 `core_competencies` 를 자동 생성하도록 구조를 확장했습니다.
- JSON 변환 정보(`json_file_path`, `json_content_type`, `json_file_size`, `conversations_count`, `html_file_deleted`)를 추가하여 파이프라인 상태를 추적합니다.
- **새로운 기능 추가**:
  - 면접 시스템: 질문 생성, 답변 평가, 세션 관리
  - 자기소개서 시스템: 문단별 구성, 스타일 지원
  - 추천 시스템: 사용자별 맞춤 공고 추천, 추천 이유 분석
  - 음성 면접 지원: Whisper를 통한 음성-텍스트 변환

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
  "html_file_path": "users/user123/html/persona456.html",
  "html_content_type": "text/html",
  "html_file_size": 2048576,
  "json_file_path": "users/user123/json/persona456.json",
  "json_content_type": "application/json",
  "json_file_size": 1024000,
  "conversations_count": 15,
  "html_file_deleted": true,
  "embedding_status": "completed",
  "embedding_message": "임베딩 작업이 성공적으로 완료되었습니다.",
  "embedding_error": null,
  "embedding_started_at": "2025-01-27T10:35:00.000000Z",
  "embedding_completed_at": "2025-01-27T10:40:00.000000Z",
  "embeddings_count": 128,
  "embedding_model": "embed-multilingual-v3.0",
  "has_embeddings": true,
  "vectorized_competency_tags": ["JG_07_C01", "JG_07_C03"],
  "competencies": {
    "문제 분해": {
      "score": 4,
      "score_explanation": "요구사항을 단계적으로 분해한 사례가 다수 발견됨",
      "key_insights": [
        "복잡한 프로젝트를 모듈 단위로 나누어 처리",
        "데이터 구조를 체계적으로 설계"
      ],
      "evaluated_at": "2025-01-27T11:00:00.000000Z"
    },
    "구현 정확성": {
      "score": 5,
      "score_explanation": "코드 품질이 높고 버그가 적음",
      "key_insights": [
        "깔끔한 코드 작성",
        "효율적인 알고리즘 구현"
      ],
      "evaluated_at": "2025-01-27T11:00:00.000000Z"
    }
  },
  "final_evaluation": "전반적으로 우수한 개발 역량을 보이며, 특히 문제 해결 능력과 구현 정확성이 뛰어남",
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:40:00.000000Z"
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
  "html_file_path": "users/user123/html/persona789.html",
  "html_content_type": "text/html",
  "html_file_size": 1024000,
  "json_file_path": "users/user123/json/persona789.json",
  "json_content_type": "application/json",
  "json_file_size": 512000,
  "conversations_count": 8,
  "html_file_deleted": true,
  "embedding_status": "queued",
  "embedding_message": "임베딩 작업이 대기열에 등록되었습니다.",
  "embedding_error": null,
  "embedding_started_at": null,
  "embedding_completed_at": null,
  "embeddings_count": 0,
  "embedding_model": null,
  "has_embeddings": false,
  "vectorized_competency_tags": [],
  "competencies": {},
  "final_evaluation": null,
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```

## 🧠 Additional Fields: 임베딩 및 역량 평가

### 임베딩 관련 필드
- `embedding_status` (string): 임베딩 처리 상태 (queued/running/completed/failed)
- `embedding_message` (string): 임베딩 상태에 대한 설명 메시지
- `embedding_error` (string, optional): 임베딩 실패 시 오류 메시지
- `embedding_started_at` (timestamp, optional): 임베딩 작업 시작 시각
- `embedding_completed_at` (timestamp, optional): 임베딩 작업 완료 시각
- `embeddings_count` (number): 임베딩된 대화 청크 수
- `embedding_model` (string, optional): 사용된 임베딩 모델명
- `has_embeddings` (boolean): 임베딩 데이터 존재 여부
- `vectorized_competency_tags` (string[]): 벡터화된 역량 태그 목록

### 역량 평가 관련 필드 (새로운 구조)
- `competencies` (object): 역량별 평가 결과를 담는 객체
  - 각 역량명을 키로 하는 중첩 객체
  - `score` (number): 역량 점수
  - `score_explanation` (string): 점수에 대한 설명
  - `key_insights` (string[]): 핵심 인사이트 목록
  - `evaluated_at` (timestamp): 평가 완료 시각
- `final_evaluation` (string, optional): 최종 종합 평가 결과

## 🧾 Collection: user_vector_embeddings

```
user_vector_embeddings/{userId}
├─ embeddings: object[]               // 임베딩 데이터 배열
│   ├─ conversation_id: string        // 대화 ID
│   ├─ content: string                // 임베딩된 텍스트 내용
│   ├─ embedding: number[]             // 벡터 임베딩 값들
│   ├─ competency_tags: string[]      // 역량 태그들
│   └─ created_at: timestamp          // 생성 시각
├─ metadata: object                   // 메타데이터
│   ├─ total_conversations: number    // 총 대화 수
│   ├─ last_updated: timestamp        // 마지막 업데이트 시각
│   └─ embedding_model: string        // 사용된 임베딩 모델
└─ created_at: timestamp              // 문서 생성 시각
```

## 🔧 추가 컬렉션: job_postings

```
job_postings/{jobPostingId}
├─ company_name: string               // 회사명
├─ company_logo: string                // 회사 로고 URL
├─ title: string                      // 공고 제목
├─ job_category: string               // 직무 분야
├─ job_title: string                  // 직무명
├─ hires_count: number                // 채용 인원
├─ job_description: string            // 업무 설명
├─ requirements: string[]               // 필수 요구사항
├─ preferred: string[]                // 우대사항
├─ required_qualifications: string[]  // 필수 자격요건
├─ preferred_qualifications: string[] // 우대 자격요건
├─ ideal_candidate: string[]          // 인재상 (7문항)
├─ work_conditions: object            // 근무 조건
│   ├─ employment_type: string        // 고용 형태
│   ├─ location: string               // 근무지
│   └─ position: string               // 직급
├─ benefits: string[]                 // 복리후생
├─ registration_date: string          // 등록일
├─ application_deadline: string       // 지원 마감일
└─ required_competencies: object      // 핵심 역량 5종 점수
    ├─ expertise: number              // 전문성
    ├─ potential: number              // 잠재력
    ├─ problem_solving: number        // 문제해결능력
    ├─ collaboration: number          // 협업능력
    └─ adaptability: number           // 적응력
```

> 😊 참고: 모든 문서는 UTF-8로 저장되며, 필드명은 Firestore 규약을 따릅니다.
