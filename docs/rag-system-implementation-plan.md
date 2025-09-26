# RAG 시스템 구축을 위한 상부 구현 계획 (2025 Q3 업데이트)

## 📋 프로젝트 개요

`/api/personas/inputs/` 요청 이후 저장되는 ChatGPT 대화 JSON을 기반으로 사용자 발화만 Cohere 임베딩 모델로 변환하고, Pinecone 벡터 DB에 저장한 뒤 내부 RAG 파이프라인에서 역량 평가에 활용합니다. 모든 임베딩은 비동기 작업으로 처리되어 사용자 응답속도를 유지합니다.

## 🎯 핵심 요구사항

1. **사용자 발화 기반 임베딩**: `chat-standard.json` 등에서 `role == "user"`인 메시지만 추출하여 임베딩
2. **Cohere 멀티링구얼 임베딩**: `embed-multilingual-v3.0` 모델 사용, `input_type="search_document"`
3. **Pinecone 벡터 저장소**: 사용자 UID를 Pinecone 네임스페이스로 사용하여 검색 가능한 dense 벡터 저장
4. **맥락 보존 메타데이터**: `conversation_title`, 직전 `assistant` 질문(`question`), chunk 연결 정보를 Pinecone 메타데이터로 보존
5. **비동기 처리**: HTML 업로드 후 즉시 응답, 임베딩·저장은 `rag_embedding_job` 백그라운드 스레드에서 수행
6. **역량 태깅 기반 확장성**: `competency_definitions` 전달 시 chunk 메타데이터의 `competency_tags` 채움 (향후 필터링 용도)
7. **Firestore 연동**: 페르소나 문서에서 임베딩 작업 상태(`embedding_status`)와 Pinecone 결과 정보를 추적

## 🏗️ 시스템 아키텍처

### 1. 데이터 플로우 (비동기 파이프라인)
```
HTML 업로드 → Storage 저장 → HTML→JSON 변환 → Firestore 문서 생성(embedding_status=queued)
                                                                    ↓
                    enqueue_embedding_job → JSON 다운로드 → 사용자 발화 및 질문 추출 → 512토큰 chunking
                                                                    ↓
                        Cohere 임베딩 생성 → Pinecone(namespace=uid) upsert → Firestore 상태 갱신
                                                                    ↓
                        (내부) 역량 평가 파이프라인 → 점수 계산 및 저장
```

### 2. 컴포넌트 구조 (핵심 파일)
```
job_cheat/
├── core/services/
│   ├── cohere_service.py          # Cohere SDK 래퍼, dotenv 로 API 키 로딩
│   ├── pinecone_service.py        # Pinecone 인덱스 생성·upsert·쿼리
│   ├── rag_embedding_service.py   # 대화 추출, chunking, 임베딩 생성, 벡터 포맷팅
│   └── rag_embedding_job.py       # 백그라운드 스레드 + asyncio 파이프라인 실행
├── personas/
│   ├── views.py                   # PersonaInputCreateView에서 업로드 처리 & 큐 등록
│   └── api/serializers.py         # 임베딩 상태 필드 포함한 응답 직렬화
└── docs/rag-system-implementation-plan.md
```

## 📊 데이터 모델 확장

### Firestore `personas/{persona_id}` 문서 주요 필드
```json
{
  "embedding_status": "queued | running | completed | failed",
  "embedding_message": "임베딩 작업 상태 메시지",
  "embedding_error": null,
  "embedding_started_at": "2025-09-26T05:12:34Z",
  "embedding_completed_at": "2025-09-26T05:12:55Z",
  "embeddings_count": 128,
  "vectorized_competency_tags": ["JG_07_C01", "JG_07_C03"],
  "has_embeddings": true,
  "embedding_model": "embed-multilingual-v3.0"
}
```

### Pinecone 메타데이터 스키마 (namespace = 사용자 UID)
```json
{
  "id": "conv_42_chunk_0",
  "values": [1.23, 0.98, ...],
  "metadata": {
    "content": "chunk 텍스트",
    "original_content": "전체 사용자 답변",
    "conversation_title": "2024년 인터뷰 대비",
    "question": "직전 assistant 질문",
    "role": "user",
    "chunk_index": 0,
    "previous_chunk_id": null,
    "next_chunk_id": "conv_42_chunk_1",
    "competency_tags": [],
    "created_at": "2025-09-26T05:11:02Z"
  }
}
```

## 🔧 핵심 서비스 요약

### `cohere_service.py`
- `load_dotenv()`로 `.env` 로드 후 `COHERE_API_KEY`, `COHERE_EMBED_MODEL` 읽기
- `embed_texts()`에서 비어 있는 문자열 필터링 후 `cohere.Client.embed()`를 `sync_to_async`로 감싸 호출
- 기본 `input_type="search_document"` 유지 (검색 적합도 최적화)

### `rag_embedding_service.py`
- `extract_user_conversations()`에서 JSON 파싱 후 `role == "user"` 발화만 수집, 직전 assistant 메시지를 `question`으로 포함
- `generate_embeddings()`에서 `tiktoken`의 `cl100k_base` 토크나이저로 512 토큰씩 chunking, chunk 연결 ID 계산
- Cohere 응답 벡터를 Pinecone 포맷으로 변환 (`_format_pinecone_vectors`)
- `process_user_conversations()`에서 chunk 임베딩 생성 후 `pinecone_service.upsert_vectors()` 호출

### `pinecone_service.py`
- `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_INDEX_DIMENSION(=1024)`, `PINECONE_METRIC(=cosine)` 등 환경 변수를 사용
- 인덱스가 없으면 `ServerlessSpec(cloud=AWS, region=us-east-1)`으로 생성
- `upsert_vectors()`는 Cohere 벡터와 메타데이터 리스트를 받아 Pinecone에 저장
- `query_similar()`는 향후 RAG 검색 시 메타데이터 필터(`competency_tags` 등) 지원

### `rag_embedding_job.py`
- `enqueue_embedding_job()`이 백그라운드 스레드에서 `_async_embedding_job()` 실행
- JSON 다운로드 실패, 임베딩 실패 상황별로 Firestore 상태를 `failed`로 갱신
- 성공 시 `embedding_status`를 `completed`로 변경하고 Pinecone 저장 결과를 문서에 반영

### `rag_vector_store.py`
- Firestore 기반 벡터 저장 로직은 제거되었으며, 현재는 사용자 임베딩 개수 조회 등 보조 기능만 유지

## 🔌 API 엔드포인트 현황

| 메서드 | 경로 | 설명 | 비고 |
| --- | --- | --- | --- |
| `POST` | `/api/personas/inputs/` | HTML 업로드 → JSON 변환 → Firestore 저장 → 임베딩 작업 큐잉 | 비동기 작업, 상태 필드 포함 |
| `GET` | `/api/personas/json/<document_id>/` | 변환된 JSON 조회 | 인증 필요 |
| `GET` | `/api/personas/files/` | 사용자 Storage 파일 목록 조회 | 인증 필요 |

> **참고**: 과거 노출되던 `/api/personas/<persona_id>/vectorize/`, `/api/personas/<persona_id>/evaluate-competencies/` 뷰는 삭제되었습니다. 임베딩/평가는 내부 서비스에서만 사용합니다.

## ⚙️ 기술 스택 및 설정

### 의존성 (`pyproject.toml`)
```toml
[project]
dependencies = [
    "cohere>=5.0.0",
    "pinecone-client>=4.0.0",
    "tiktoken>=0.7.0",
    "numpy>=1.26.0",
    "firebase-admin",
    "django",
]
```

### 환경 변수 예시 (`.env`)
```env
COHERE_API_KEY=your_cohere_api_key
COHERE_EMBED_MODEL=embed-multilingual-v3.0
COHERE_MAX_TOKENS_PER_CHUNK=512

PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=persona-conversations
PINECONE_INDEX_DIMENSION=1024
PINECONE_METRIC=cosine
PINECONE_REGION=us-east-1
PINECONE_CLOUD_PROVIDER=AWS
```

### Pinecone 인덱스 구성
- **이름**: `persona-conversations` (예시, 환경 변수로 정의)
- **차원**: 1024 (Cohere `embed-multilingual-v3.0` 출력과 동일)
- **Metric**: cosine
- **Type**: Serverless Dense Vector Index
- **Namespace**: 사용자 UID별 분리

## ✅ 구현 상태 (2025-09-26 기준)

| Phase | 항목 | 상태 | 비고 |
| --- | --- | --- | --- |
| Phase 1 | Cohere SDK 연동 | ✅ | `.env` 로딩, 예외 처리 완료 |
| Phase 1 | Pinecone 인덱스 구성 | ✅ | 존재 확인 후 자동 생성 |
| Phase 2 | 임베딩 서비스 고도화 | ✅ | chunking, 질문 메타데이터, Pinecone upsert |
| Phase 2 | 역량 평가 서비스 정비 | 🟡 | 내부 호출만 유지, 자동화 미완 |
| Phase 3 | 비동기 임베딩 파이프라인 | ✅ | 큐 등록 → 상태 업데이트 → 완료/실패 처리 |
| Phase 3 | API 정리 | ✅ | 불필요한 외부 뷰 제거 |
| Phase 4 | 테스트 보강 | 🟡 | Cohere/Pinecone mock 테스트 추가 예정 |
| Phase 4 | 성능/운영 최적화 | 🟡 | 재임베딩 전략, 벡터 정리 작업 필요 |

## 🔍 테스트 & 모니터링
- `job_cheat/scripts/test_cohere_embedding.py` 스크립트로 Cohere/Pinecone 연동 검증 (dotenv 로딩 포함)
- 실 환경에서는 Firestore 로그와 Pinecone usage dashboard로 상태 확인
- 향후 Django management command 기반 통합 테스트 도입 예정

## 📌 향후 과제
- 역량 평가 파이프라인 자동화 및 테스트 추가
- Pinecone 쿼리 API 구현 (질의 응답/추천용)
- chunk 메타데이터 기반 역량별 필터링 시나리오 구체화
- 대용량 사용자 대비 백그라운드 워커 확장 전략 수립

---

**작성일**: 2025-09-26  
**작성자**: AI Assistant  
**버전**: v1.1 (Cohere + Pinecone 전환 반영)
