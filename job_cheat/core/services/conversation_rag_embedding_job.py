"""
새로운 대화 RAG 시스템을 사용하는 임베딩 백그라운드 작업 모듈.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from threading import Thread
from typing import Any, Dict, List, Optional

from firebase_admin import firestore

from .firebase_personas import update_persona_document
from .firebase_storage import (
    PersonaJsonDownloadError,
    download_persona_json,
)
from .conversation_rag_service import (
    ConversationRAGServiceError,
    ConversationRAGService,
)
from .gemini_service import GeminiService
from .rag_competency_evaluator import RAGCompetencyEvaluator

logger = logging.getLogger(__name__)


def enqueue_conversation_rag_job(
    *,
    user_id: str,
    persona_id: str,
    competency_definitions: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """새로운 대화 RAG 시스템을 사용하는 임베딩 백그라운드 작업을 큐에 등록한다."""

    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not persona_id:
        raise ValueError("persona_id 값이 필요합니다.")

    thread = Thread(
        target=_run_conversation_rag_job,
        args=(user_id, persona_id, competency_definitions or []),
        daemon=True,
    )
    thread.start()


def _run_conversation_rag_job(
    user_id: str,
    persona_id: str,
    competency_definitions: List[Dict[str, Any]],
) -> None:
    """새로운 이벤트 루프에서 대화 RAG 임베딩 작업을 실행한다."""

    try:
        asyncio.run(
            _async_conversation_rag_job(
                user_id=user_id,
                persona_id=persona_id,
                competency_definitions=competency_definitions,
            )
        )
    except Exception as exc:  # pragma: no cover - 최상위 예외 로깅
        logger.exception("대화 RAG 임베딩 백그라운드 작업이 실패했습니다: %s", exc)
        try:
            update_persona_document(
                user_id=user_id,
                persona_id=persona_id,
                payload={
                    "embedding_status": "failed",
                    "embedding_error": str(exc),
                    "embedding_completed_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
            )
        except Exception:
            logger.exception("대화 RAG 임베딩 실패 상태를 Firestore에 기록하지 못했습니다.")


async def _async_conversation_rag_job(
    *,
    user_id: str,
    persona_id: str,
    competency_definitions: List[Dict[str, Any]],
) -> None:
    """실제 대화 RAG 임베딩 파이프라인을 실행하고 Firestore 문서를 갱신한다."""

    start_timestamp = datetime.utcnow()

    try:
        update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload={
                "embedding_status": "running",
                "embedding_started_at": start_timestamp,
                "embedding_error": None,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )
    except Exception:
        logger.exception("대화 RAG 임베딩 시작 상태를 기록하는 데 실패했습니다.")

    try:
        download_result = download_persona_json(
            user_id=user_id,
            document_id=persona_id,
        )
    except PersonaJsonDownloadError as exc:
        logger.exception("대화 RAG 임베딩 작업용 JSON 다운로드 실패")
        _mark_conversation_rag_embedding_failed(user_id, persona_id, f"json_download_failed: {exc}")
        return

    if not download_result.get("exists") or not download_result.get("content"):
        logger.warning("대화 RAG 임베딩 작업용 JSON 콘텐츠가 없습니다: user_id=%s, persona_id=%s", user_id, persona_id)
        _mark_conversation_rag_embedding_failed(user_id, persona_id, "json_content_missing")
        return

    # 새로운 대화 RAG 서비스 사용
    conversation_rag_service = ConversationRAGService()
    
    try:
        logger.info(f"대화 RAG 임베딩 파이프라인 시작: user_id={user_id}, persona_id={persona_id}")
        
        # 1단계: JSON 파일에서 청크 생성
        chunks = conversation_rag_service.process_conversation_json(
            user_id=user_id,
            document_id=persona_id
        )
        
        if not chunks:
            logger.warning("처리할 청크가 없습니다.")
            _mark_conversation_rag_embedding_failed(user_id, persona_id, "no_chunks_to_process")
            return
        
        logger.info(f"청크 생성 완료: {len(chunks)}개")
        
        # 2단계: Pinecone에 임베딩 업로드
        embed_success = await conversation_rag_service.embed_and_upsert_to_pinecone(
            chunks=chunks,
            user_id=user_id
        )
        
        if not embed_success:
            logger.error("Pinecone 임베딩 업로드 실패")
            _mark_conversation_rag_embedding_failed(user_id, persona_id, "pinecone_upload_failed")
            return
        
        logger.info("Pinecone 임베딩 업로드 완료")
        
        # 3단계: 역량 평가 수행 (competency_definitions가 있는 경우)
        competency_evaluation_results = {}
        if competency_definitions:
            logger.info(f"역량 평가 시작: {len(competency_definitions)}개 역량")
            
            try:
                # Gemini 서비스와 RAG 역량 평가 서비스 초기화
                gemini_service = GeminiService()
                rag_evaluator = RAGCompetencyEvaluator()
                
                for competency in competency_definitions:
                    competency_name = competency.get('name', '')
                    competency_description = competency.get('description', '')
                    competency_query = competency.get('query', '')
                    
                    if not all([competency_name, competency_description, competency_query]):
                        logger.warning(f"역량 정보가 불완전합니다: {competency}")
                        continue
                    
                    logger.info(f"역량 평가 중: {competency_name}")
                    
                    try:
                        # RAG 컨텍스트 검색
                        context = await conversation_rag_service.get_rag_context(
                            query=competency_query,
                            user_id=user_id,
                            top_k=3
                        )
                        
                        if context:
                            logger.info(f"RAG 컨텍스트 조회 성공: {len(context):,}자")
                            
                            # LLM 역량 평가 수행
                            evaluation_result = await _evaluate_competency_with_citations(
                                competency_name=competency_name,
                                competency_description=competency_description,
                                context=context,
                                gemini_service=gemini_service
                            )
                            
                            if evaluation_result:
                                competency_evaluation_results[competency_name] = evaluation_result
                                logger.info(f"✅ {competency_name} 역량 평가 완료: {evaluation_result.get('score', 'N/A')}/10")
                            else:
                                logger.warning(f"⚠️ {competency_name} 역량 평가 실패")
                        else:
                            logger.warning(f"⚠️ {competency_name}에 대한 RAG 컨텍스트 없음")
                            
                    except Exception as exc:
                        logger.error(f"❌ {competency_name} 역량 평가 실패: {exc}")
                        continue
                
                # 역량 평가 결과를 Firestore에 저장
                if competency_evaluation_results:
                    await _save_competency_evaluations_to_firestore(
                        user_id=user_id,
                        persona_id=persona_id,
                        evaluation_results=competency_evaluation_results
                    )
                    logger.info(f"역량 평가 결과 저장 완료: {len(competency_evaluation_results)}개")
                else:
                    logger.warning("저장할 역량 평가 결과가 없습니다.")
                    
            except Exception as exc:
                logger.error(f"역량 평가 과정에서 오류 발생: {exc}")
        else:
            logger.info("역량 정의가 없어 역량 평가를 건너뜁니다.")
        
        # 4단계: RAG 검색 테스트 (선택사항)
        try:
            test_context = await conversation_rag_service.get_rag_context(
                query="테스트 쿼리",
                user_id=user_id,
                top_k=1
            )
            logger.info(f"RAG 검색 테스트 완료: {len(test_context)}자 컨텍스트")
        except Exception as exc:
            logger.warning(f"RAG 검색 테스트 실패 (무시): {exc}")
        
        # 성공 상태 업데이트
        update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload={
                "embedding_status": "completed",
                "embedding_message": "대화 RAG 임베딩이 완료되었습니다.",
                "embeddings_count": len([chunk for chunk in chunks if chunk['role'] == 'user']),
                "embedding_model": "embed-multilingual-v3.0",
                "has_embeddings": True,
                "vectorized_competency_tags": [],  # 대화 RAG에서는 역량 태깅 없음
                "embedding_error": None,
                "embedding_completed_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )
        
        logger.info(f"대화 RAG 임베딩 파이프라인 완료: user_id={user_id}, persona_id={persona_id}")
        
    except ConversationRAGServiceError as exc:
        logger.exception("대화 RAG 임베딩 파이프라인 실행 실패")
        _mark_conversation_rag_embedding_failed(user_id, persona_id, f"conversation_rag_failed: {exc}")
        return
    except Exception as exc:  # pragma: no cover - 예기치 못한 예외 로깅
        logger.exception("대화 RAG 임베딩 파이프라인 중 알 수 없는 오류")
        _mark_conversation_rag_embedding_failed(user_id, persona_id, f"unknown_conversation_rag_error: {exc}")
        return


async def _evaluate_competency_with_citations(
    competency_name: str,
    competency_description: str,
    context: str,
    gemini_service: GeminiService
) -> Optional[Dict[str, Any]]:
    """실제 대화 내용을 인용하여 역량을 평가합니다."""
    
    evaluation_prompt = f"""
다음은 한 사용자의 ChatGPT 대화 기록에서 추출한 관련 컨텍스트입니다.

=== 대화 컨텍스트 ===
{context}

=== 평가 요청 ===
{competency_name}: {competency_description}

=== 평가 지침 ===
1. 위 대화 컨텍스트를 바탕으로 사용자의 {competency_name} 역량을 구체적으로 평가해주세요.
2. **반드시 대화 내용에서 실제 인용문을 포함하여 근거를 제시해주세요.**
3. 인용할 때는 "사용자: [인용문]" 또는 "어시스턴트: [인용문]" 형식으로 명확히 표시해주세요.
4. 강점과 개선점을 균형있게 분석해주세요.
5. 평가 점수(1-10점)와 함께 구체적인 이유를 설명해주세요.

=== 응답 형식 (JSON) ===
{{
    "competency_name": "{competency_name}",
    "score": 8,
    "score_explanation": "점수에 대한 구체적인 설명",
    "strengths": [
        {{
            "description": "강점 설명",
            "evidence": "대화에서 인용한 구체적 근거",
            "citation": "사용자: [실제 인용문]"
        }}
    ],
    "improvements": [
        {{
            "description": "개선점 설명",
            "suggestion": "구체적인 개선 방안",
            "evidence": "대화에서 인용한 구체적 근거",
            "citation": "사용자: [실제 인용문]"
        }}
    ],
    "overall_assessment": "전체적인 평가 및 종합 의견",
    "key_insights": [
        "핵심 인사이트 1",
        "핵심 인사이트 2"
    ]
}}
"""
    
    try:
        # Gemini를 사용한 구조화된 평가 수행
        evaluation_result = await gemini_service.generate_structured_response(
            prompt=evaluation_prompt,
            response_format="json"
        )
        
        if evaluation_result:
            # JSON 파싱 (Gemini 서비스에서 이미 정리됨)
            try:
                import json
                evaluation_data = json.loads(evaluation_result.strip())
                return evaluation_data
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.error(f"원본 응답: {evaluation_result}")
                return None
        else:
            logger.warning("LLM 평가 결과가 비어있음")
            return None
            
    except Exception as exc:
        logger.error(f"역량 평가 실패: {exc}")
        return None


async def _save_competency_evaluations_to_firestore(
    user_id: str,
    persona_id: str,
    evaluation_results: Dict[str, Any]
) -> bool:
    """역량 평가 결과를 Firestore에 저장합니다."""
    
    try:
        # Firestore 문서 업데이트 데이터 구성
        update_payload = {}
        
        for competency_name, evaluation_data in evaluation_results.items():
            update_payload[f"competencies.{competency_name}"] = {
                "score": evaluation_data.get("score", 0),
                "score_explanation": evaluation_data.get("score_explanation", ""),
                "strengths": evaluation_data.get("strengths", []),
                "improvements": evaluation_data.get("improvements", []),
                "overall_assessment": evaluation_data.get("overall_assessment", ""),
                "key_insights": evaluation_data.get("key_insights", []),
                "evaluated_at": firestore.SERVER_TIMESTAMP
            }
        
        # Firestore 문서 업데이트
        result = update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload=update_payload
        )
        
        if result:
            logger.info(f"✅ 역량 평가 결과 Firestore 저장 완료: {len(evaluation_results)}개")
            return True
        else:
            logger.error(f"❌ 역량 평가 결과 Firestore 저장 실패")
            return False
            
    except Exception as exc:
        logger.error(f"Firestore 저장 실패: {exc}")
        return False


def _mark_conversation_rag_embedding_failed(user_id: str, persona_id: str, reason: str) -> None:
    """대화 RAG 임베딩 실패 상태를 Firestore 문서에 반영한다."""

    try:
        update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload={
                "embedding_status": "failed",
                "embedding_error": reason,
                "embedding_completed_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )
    except Exception:  # pragma: no cover - 실패 상태 기록 실패시 로그만 남김
        logger.exception("대화 RAG 임베딩 실패 상태 기록에 실패했습니다: %s", reason)
