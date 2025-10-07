# Job-Cheat Backend

취업 준비를 위한 AI 기반 플랫폼의 Django 백엔드 서비스입니다.

## 개요

Job-Cheat는 ChatGPT 대화 내역 하나만으로 완전한 취업 준비 서비스를 제공하는 플랫폼입니다.

### 주요 강점

**극도로 간단한 사용법**

- 다른 서비스: 복잡한 설문조사, 긴 자기소개서 작성, 여러 단계의 입력 과정
- Job-Cheat: ChatGPT 대화 내역 파일 하나만 업로드하면 끝

**AI 대화의 솔직함을 활용한 진정한 역량 평가**

- 사람들은 AI와 대화할 때 매우 솔직함: 실제 경험, 솔직한 의견, 숨겨진 강점까지 자연스럽게 드러남
- 자기객관화가 어려운 사람도 AI와의 대화에서 나온 진솔한 내용을 바탕으로 객관적 평가를 받을 수 있음
- 가상의 답변이 아닌, 실제로 한 말을 바탕으로 한 정확한 역량 분석

**완전 자동화된 맞춤형 서비스**

- 대화 내역에서 페르소나 추출, 역량 평가, 맞춤형 서비스까지 전체 파이프라인 자동화
- 대화에서 언급된 구체적인 경험과 사례를 활용한 진정성 있는 자기소개서
- 사용자의 실제 경험과 역량을 바탕으로 한 맞춤형 면접 질문 생성
- 실제 역량과 경험을 바탕으로 한 정밀한 채용공고 추천

### 간단한 사용 흐름

```
1. ChatGPT 대화 내역 파일 업로드 (30초)
2. AI가 자동으로 분석 및 처리 (2-3분)
3. 완성된 페르소나, 자기소개서, 면접 질문, 채용공고 추천 제공
```

### 기존 서비스 vs Job-Cheat

| 구분          | 기존 서비스                         | Job-Cheat                      |
| ------------- | ----------------------------------- | ------------------------------ |
| 입력 과정     | 복잡한 설문조사, 긴 자기소개서 작성 | 파일 업로드 1회                |
| 소요 시간     | 1-2시간                             | 30초                           |
| 데이터 정확성 | 사용자가 작성한 가상의 답변         | 실제 대화에서 나온 진솔한 내용 |
| 개인화 수준   | 템플릿 기반                         | 실제 경험과 역량 기반          |

## 아키텍처

```
job_cheat/
├── api/                    # REST API 엔드포인트
├── core/                   # 공통 서비스 및 유틸리티
├── personas/               # 페르소나 관리
├── interviews/             # 면접 서비스
├── cover_letters/          # 자기소개서 서비스
├── job_search/             # 채용공고 검색 및 추천
└── job_cheat/              # Django 프로젝트 설정
```

## 핵심 기능

### 1. 스마트 페르소나 분석 (`personas/`)

- ChatGPT 대화 내역 HTML 파일만 업로드하면 자동 처리
- 대화 내용에서 핵심 역량, 강점, 경험을 자동으로 분석
- 대화 내역을 벡터화하여 정확한 컨텍스트 검색 지원
- 실제 발화 내용을 바탕으로 한 정확한 역량 점수 산출

### 2. AI 면접 시뮬레이션 (`interviews/`)

- 사용자의 실제 경험과 역량을 바탕으로 한 개인화된 면접 질문
- TTS/STT를 활용한 실제 면접과 유사한 환경 제공
- AI가 답변을 즉시 분석하고 구체적인 피드백 제공
- 모범 답변과 함께 구체적인 개선 방향 제시

### 3. 진정성 있는 자기소개서 (`cover_letters/`)

- 대화에서 언급된 구체적인 사례와 경험을 자기소개서에 반영
- 지원하는 회사와 포지션에 맞는 맞춤형 자기소개서 생성
- 정중한 스타일부터 캐주얼한 스타일까지 선택 가능
- 글자 수와 내용을 자동으로 조정하여 완성도 높은 자기소개서 제공

### 4. 정밀한 채용공고 매칭 (`job_search/`)

- 사용자의 진짜 역량과 경험을 바탕으로 한 정확한 매칭
- 단순 키워드 매칭이 아닌, 대화 맥락을 이해한 깊이 있는 분석
- 왜 이 공고가 적합한지 구체적인 근거와 함께 제시

## 기술적 특징

### 통합 RAG 시스템

- ChatGPT 대화 기록 하나로 모든 서비스 제공
- 대화 분석부터 역량 평가, 맞춤형 서비스까지 완전한 연계
- 새로운 대화 파일 업로드 시 더욱 정확한 분석과 서비스 제공

### RAG 기반 역량 평가

- User 발화와 Assistant 답변 메타데이터를 모두 활용하여 대화 컨텍스트 보존
- Pinecone namespace 기반 완전한 데이터 격리
- 실제 대화 내용 인용으로 평가 신뢰성 극대화

### 임베딩 필터링 시스템

- ChatGPT 답변을 완전히 제외하고 사용자 발화만 임베딩하여 순수 사용자 역량 추출
- 이전 Assistant 답변을 메타데이터로 활용하여 사고 깊이 측정
- AI의 영향 없이 순수한 사용자 역량만 평가

### 완전 자동화된 파이프라인

- 설정 없이 파일 업로드만으로 모든 서비스 활성화
- 데이터 처리부터 서비스 제공까지 전 과정 자동화
- 새로운 AI 모델이나 서비스 추가가 용이한 확장 가능한 아키텍처

## 기술 스택

- **Backend**: Django 4.2, Python 3.12
- **Database**: Firestore
- **AI Services**: Google Gemini, Cohere, OpenAI Whisper
- **Storage**: Firebase Storage
- **Vector DB**: Pinecone
- **TTS/STT**: Google Cloud Text-to-Speech, Whisper

## 설치 및 실행

### 1. 의존성 설치

```bash
uv sync
```

### 2. 환경 변수 설정

```bash
# Firebase 인증 정보
export FIREBASE_CREDENTIALS="path/to/firebase-credentials.json"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/firebase-credentials.json"

# AI 서비스 API 키
export GEMINI_API_KEY="your_gemini_api_key"
export COHERE_API_KEY="your_cohere_api_key"
export PINECONE_API_KEY="your_pinecone_api_key"
```

### 3. 데이터베이스 마이그레이션

```bash
uv run python manage.py migrate
```

### 4. 서버 실행

```bash
# 일반 서버
uv run python manage.py runserver 0.0.0.0:8000

# ASGI 서버 (대용량 파일 업로드용)
uv run python runserver_asgi.py 0.0.0.0:8000
```

## 모듈별 상세 문서

### 핵심 모듈

- [**Core Services**](job_cheat/core/README_Core_Services.md) - 공통 인프라 서비스 및 유틸리티
- [**API App**](job_cheat/api/README_API_App.md) - REST API 엔드포인트

### 도메인 앱

- [**Personas**](job_cheat/personas/README_Personas_App.md) - 페르소나 데이터 관리
- [**Interviews**](job_cheat/interviews/README_Interviews_App.md) - AI 기반 면접 서비스
- [**Cover Letters**](job_cheat/cover_letters/README_Cover_Letters_App.md) - 자기소개서 생성 서비스
- [**Job Search**](job_cheat/job_search/README_Job_Search_App.md) - 채용공고 검색 및 추천

### 기술 문서

- [**Database Schema**](job_cheat/docs/README_Database_Schema.md) - 데이터베이스 스키마 설계
- [**Conversation RAG System**](job_cheat/core/services/README_Conversation_RAG_System.md) - RAG 시스템 구현 가이드
