"""
RAG 기반 핵심역량 평가 서비스 구현.
Gemini 모델과 Firestore 벡터 저장소를 이용해 페르소나 역량을 점수화합니다.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .gemini_service import get_gemini_service
from .job_competencies import JobCompetenciesService
from .pinecone_service import get_pinecone_service, PineconeServiceError
from .cohere_service import get_cohere_service, CohereServiceError
from .pinecone_service import get_pinecone_service
from .cohere_service import get_cohere_service
from .firebase_personas import (
    PersonaNotFoundError,
    get_persona_document,
    mark_competency_evaluation,
)

logger = logging.getLogger(__name__)

COMPETENCY_EVALUATION_VERSION = "v2.0"
SYSTEM_PROMPT_VERSION = "v1.0"

SYSTEM_PROMPT = """
당신은 Job-Cheat 플랫폼의 인사 평가 LLM 에이전트입니다.

역할과 규칙은 다음과 같습니다.
- 역할: 한국어 채용 시장을 이해하는 HR 전문가로서, 특정 직군의 핵심역량을 정량·정성 평가합니다.
- 임무: 시스템이 제공한 직군별 핵심역량 정의, 벡터 검색 컨텍스트, 사용자 대화를 모두 고려하여 근거 기반의 평가를 제공합니다.
- 출력: 지정된 JSON 스키마를 100% 준수하며, 불확실성이 있으면 `confidence` 값을 낮게 설정하고 근거 부족을 명시합니다.
- 제한: 외부 지식이나 추측을 사용하지 않고, 제공된 데이터만으로 판단합니다. JSON 외의 자연어 서술은 금지됩니다.

항상 위 원칙을 준수하며 평가를 수행하세요.
"""

COMPETENCY_EVALUATION_PROMPT = """
당신은 전문 인사담당자입니다. 주어진 데이터와 대화 기록을 바탕으로 특정 핵심역량을 평가해주세요.

## 평가 대상 역량
- 역량 ID: {competency_id}
- 역량명: {competency_name}
- 설명: {competency_description}

## 사용자 기본 정보
- 직군: {job_category}
- 직무: {job_role}
- 보유 기술: {skills}
- 자격증: {certifications}

## 참조해야 할 벡터 검색 컨텍스트 (관련성 높은 순)
{vector_contexts}

## 사용자 대화 기록 (최대 {conversation_limit}건)
{relevant_conversations}

## 평가 기준 (10점 만점)
- 90-100점: 해당 역량에서 전문가 수준의 능력을 보여줌
- 70-89점: 해당 역량에서 숙련된 수준의 능력을 보여줌
- 50-69점: 해당 역량에서 기본적인 수준의 능력을 보여줌
- 30-49점: 해당 역량에서 미숙한 수준의 능력을 보여줌
- 10-29점: 해당 역량에서 초보 수준의 능력을 보여줌

## 응답 형식 (JSON)
{{
  "score": 정수점수(1-100),
  "confidence": "매우높음|높음|보통|낮음|매우낮음 중 하나",
  "reasoning": "점수 근거 설명",
  "strong_signals": ["긍정 신호 1", "긍정 신호 2"],
  "risk_factors": ["주의 신호 1", "주의 신호 2"],
  "recommended_actions": ["추천 개선 행동 1", "추천 개선 행동 2"],
  "evidence": [
    {{
      "source": "vector_context" 또는 "conversation",
      "reference_id": "컨텍스트 또는 대화 ID",
      "snippet": "관련 문장",
      "relevance_score": 0.0에서 1.0 사이 수치
    }}
  ]
}}

반드시 JSON만 반환하고, 값이 없을 경우 해당 배열을 빈 배열로 유지해주세요.
"""


class RAGCompetencyEvaluatorError(RuntimeError):
    """핵심역량 평가 과정에서 발생한 예외."""


class RAGCompetencyEvaluator:
    """RAG 파이프라인을 통해 페르소나 핵심역량을 평가하는 서비스."""

    def __init__(self) -> None:
        self.gemini_service = get_gemini_service()
        self.pinecone_service = get_pinecone_service()
        self.cohere_service = get_cohere_service()
        self.job_competencies = JobCompetenciesService()
        logger.info("RAG 핵심역량 평가 서비스 초기화 완료")

    async def evaluate_persona_competencies(
        self,
        *,
        user_id: str,
        persona_id: str,
        top_k: int = 5,
        vector_context_top_k: int = 3,
        conversation_limit: int = 5,
    ) -> Dict[str, Any]:
        """특정 페르소나의 핵심역량을 평가하고 Firestore에 결과를 기록합니다."""
        if not user_id:
            raise ValueError("user_id가 비어 있습니다.")
        if not persona_id:
            raise ValueError("persona_id가 비어 있습니다.")

        try:
            persona = get_persona_document(user_id=user_id, persona_id=persona_id)
        except PersonaNotFoundError:
            raise

        core_competencies = self._resolve_competencies(persona)
        if not core_competencies:
            raise RAGCompetencyEvaluatorError("평가할 핵심역량 정보를 찾을 수 없습니다.")

        evaluation_started_at = datetime.utcnow()
        competency_scores: Dict[str, int] = {}
        evaluation_details: List[Dict[str, Any]] = []
        evaluation_errors: List[Dict[str, Any]] = []

        for competency in core_competencies:
            competency_id = competency.get("id")
            competency_name = competency.get("name", "")
            competency_description = competency.get("description", "")
            query = self._build_query(competency_name, competency_description)

            try:
                search_results = await self._search_similar_conversations(
                    user_id=user_id,
                    query=query,
                    competency_id=competency_id,
                    top_k=top_k,
                )
            except Exception as exc:  # pragma: no cover - Pinecone/임베딩 오류 래핑
                logger.exception("유사 대화 검색 실패")
                evaluation_errors.append(
                    {
                        "competency_id": competency_id,
                        "competency_name": competency_name,
                        "error": f"similarity_search_failed: {exc}",
                    }
                )
                search_results = []
            relevant_conversations = self._format_conversations(search_results, limit=conversation_limit)
            prompt = await self._generate_competency_prompt(
                persona=persona,
                competency=competency,
                relevant_conversations=relevant_conversations,
                vector_contexts=self._format_vector_contexts(search_results, limit=vector_context_top_k),
                conversation_limit=conversation_limit,
            )

            try:
                evaluation_response = await self._call_gemini_for_evaluation(prompt)
            except RAGCompetencyEvaluatorError as exc:
                evaluation_errors.append(
                    {
                        "competency_id": competency_id,
                        "competency_name": competency_name,
                        "error": f"llm_evaluation_failed: {exc}",
                    }
                )
                continue
            score = self._extract_score(evaluation_response)
            competency_scores[competency_id or competency_name] = score

            evaluation_details.append(
                {
                    "competency_id": competency_id,
                    "competency_name": competency_name,
                    "score": score,
                    "reasoning": evaluation_response.get("reasoning", ""),
                    "confidence": evaluation_response.get("confidence"),
                    "strong_signals": evaluation_response.get("strong_signals", []),
                    "risk_factors": evaluation_response.get("risk_factors", []),
                    "recommended_actions": evaluation_response.get("recommended_actions", []),
                    "evidence": evaluation_response.get("evidence", []),
                    "conversation_count": len(relevant_conversations),
                    "has_errors": False,
                }
            )

        evaluation_metadata = {
            "model": self.gemini_service.text_model,
            "system_prompt_version": SYSTEM_PROMPT_VERSION,
            "details": evaluation_details,
            "vector_store": {
                "backend": "pinecone",
                "namespace": user_id,
            },
        }

        updated_doc = mark_competency_evaluation(
            user_id=user_id,
            persona_id=persona_id,
            competency_scores=competency_scores,
            evaluation_version=COMPETENCY_EVALUATION_VERSION,
            evaluated_at=datetime.utcnow(),
            metadata=evaluation_metadata,
        )

        evaluation_completed_at = datetime.utcnow()

        return {
            "user_id": user_id,
            "persona_id": persona_id,
            "competency_scores": competency_scores,
            "evaluation_version": COMPETENCY_EVALUATION_VERSION,
            "evaluation_started_at": evaluation_started_at.isoformat() + "Z",
            "evaluation_completed_at": evaluation_completed_at.isoformat() + "Z",
            "details": evaluation_details,
            "errors": evaluation_errors,
            "persona_snapshot": updated_doc,
        }

    def _resolve_competencies(self, persona: Dict[str, Any]) -> List[Dict[str, Any]]:
        current = persona.get("core_competencies") or []
        if current:
            logger.info(f"📋 페르소나에 저장된 core_competencies 사용: {len(current)}개")
            logger.info(f"   📊 저장된 역량: {[comp.get('name', 'Unknown') for comp in current]}")
            return current

        job_category = persona.get("job_category", "")
        if not job_category:
            logger.warning("❌ job_category가 없어서 빈 리스트 반환")
            return []
        
        logger.info(f"📤 직군별 핵심역량 조회: {job_category}")
        competencies = self.job_competencies.get_core_competencies_by_job_category(job_category)
        logger.info(f"📥 직군별 핵심역량 조회 결과: {len(competencies)}개")
        logger.info(f"   📊 조회된 역량: {[comp.get('name', 'Unknown') for comp in competencies]}")
        return competencies

    def _build_query(self, name: str, description: str) -> str:
        parts = [part.strip() for part in [name, description] if part and part.strip()]
        return " - ".join(parts) if parts else "핵심역량"

    async def _search_similar_conversations(
        self,
        *,
        user_id: str,
        query: str,
        competency_id: Optional[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        if not query:
            return []

        try:
            embeddings = await self.cohere_service.embed_texts(
                [query],
                model=self.cohere_service._default_model,
                input_type="search_query",
            )
        except CohereServiceError as exc:
            raise RAGCompetencyEvaluatorError(f"쿼리 임베딩 생성 실패: {exc}") from exc

        if not embeddings:
            return []

        vector = embeddings[0]
        if not vector:
            return []
        filter_clause = None
        if competency_id:
            filter_clause = {"competency_tags": {"$contains": competency_id}}

        try:
            response = self.pinecone_service.query_similar(
                vector,
                namespace=user_id,
                top_k=top_k,
                include_metadata=True,
                filter=filter_clause,
            )
        except PineconeServiceError as exc:
            raise RAGCompetencyEvaluatorError(f"Pinecone 검색 실패: {exc}") from exc

        matches = response.get("matches", []) or []
        formatted: List[Dict[str, Any]] = []
        for match in matches:
            metadata = match.get("metadata", {}) or {}
            formatted.append(
                {
                    "conversation_id": match.get("id") or metadata.get("parent_conversation_id"),
                    "content": metadata.get("content", ""),
                    "score": float(match.get("score", 0.0)),
                    "competency_tags": metadata.get("competency_tags", []),
                }
            )
        return formatted

    def _format_vector_contexts(
        self,
        search_results: Iterable[Dict[str, Any]],
        *,
        limit: int,
    ) -> str:
        if not search_results:
            return "(참조할 벡터 컨텍스트가 없습니다.)"

        formatted_lines: List[str] = []
        for idx, item in enumerate(search_results, start=1):
            if idx > max(0, limit):
                break
            formatted_lines.append(
                "- [{idx}] 점수={score:.3f}, 대화ID={cid}: {snippet}".format(
                    idx=idx,
                    score=float(item.get("score", 0.0)),
                    cid=item.get("conversation_id", "unknown"),
                    snippet=item.get("content", "").strip() or "(내용 없음)",
                )
            )
        return "\n".join(formatted_lines)

    def _format_conversations(
        self,
        search_results: Iterable[Dict[str, Any]],
        *,
        limit: int,
    ) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        for idx, item in enumerate(search_results, start=1):
            if idx > max(0, limit):
                break
            formatted.append(
                {
                    "conversation_id": item.get("conversation_id"),
                    "content": item.get("content", ""),
                    "score": float(item.get("score", 0.0)),
                }
            )
        return formatted

    async def _generate_competency_prompt(
        self,
        *,
        persona: Dict[str, Any],
        competency: Dict[str, Any],
        relevant_conversations: List[Dict[str, Any]],
        vector_contexts: str,
        conversation_limit: int,
    ) -> str:
        if not relevant_conversations:
            conversation_block = "(관련 대화가 없습니다. 최소한의 정보를 바탕으로 평가해주세요.)"
        else:
            formatted = []
            for item in relevant_conversations:
                formatted.append(
                    "- 대화ID={conversation_id}, 유사도={score:.3f}: {content}".format(
                        conversation_id=item.get("conversation_id", "unknown"),
                        score=float(item.get("score", 0.0)),
                        content=item.get("content", "").strip() or "(내용 없음)",
                    )
                )
            conversation_block = "\n".join(formatted)

        return COMPETENCY_EVALUATION_PROMPT.format(
            competency_id=competency.get("id", ""),
            competency_name=competency.get("name", ""),
            competency_description=competency.get("description", ""),
            job_category=persona.get("job_category", ""),
            job_role=persona.get("job_role", ""),
            skills=", ".join(persona.get("skills", [])) or "(제공되지 않음)",
            certifications=", ".join(persona.get("certifications", [])) or "(제공되지 않음)",
            vector_contexts=vector_contexts,
            relevant_conversations=conversation_block,
            conversation_limit=max(0, conversation_limit),
        )

    async def _call_gemini_for_evaluation(self, prompt: str) -> Dict[str, Any]:
        try:
            full_prompt = f"{SYSTEM_PROMPT.strip()}\n\n{prompt.strip()}"
            response = await self.gemini_service.generate_structured_response(
                full_prompt,
                response_format="json",
            )
            if isinstance(response, dict):
                return response
            if isinstance(response, str):
                parsed = self._parse_llm_json(response)
                if parsed is not None:
                    return parsed
                return {"raw_response": response}
        except json.JSONDecodeError as exc:
            logger.warning("Gemini 응답 JSON 파싱 실패: %s", exc)
            return {"raw_response": response}
        except Exception as exc:  # pragma: no cover - Gemini 호출 예외 래핑
            logger.error("Gemini 평가 호출 실패: %s", exc)
            raise RAGCompetencyEvaluatorError(f"Gemini 평가 호출 실패: {exc}") from exc

        return {"raw_response": response}

    def _parse_llm_json(self, raw: str) -> Optional[Dict[str, Any]]:
        if not raw or not raw.strip():
            return None

        candidate = raw.strip()

        fenced = re.match(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
        if fenced:
            candidate = fenced.group(1).strip()

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            logger.warning("Gemini 응답 JSON 파싱 실패: 원본 응답 일부=%s", candidate[:200])
            return None

    def _extract_score(self, evaluation_response: Dict[str, Any]) -> int:
        raw_score = evaluation_response.get("score")
        try:
            score = int(raw_score)
        except (TypeError, ValueError):
            score = 0
        score = max(1, min(100, score)) if score else 50
        return score


_evaluator_instance: Optional[RAGCompetencyEvaluator] = None


def get_competency_evaluator() -> RAGCompetencyEvaluator:
    """핵심역량 평가 서비스 싱글턴을 반환합니다."""
    global _evaluator_instance
    if _evaluator_instance is None:
        _evaluator_instance = RAGCompetencyEvaluator()
        logger.info("RAG 핵심역량 평가 서비스 인스턴스 생성")
    return _evaluator_instance
