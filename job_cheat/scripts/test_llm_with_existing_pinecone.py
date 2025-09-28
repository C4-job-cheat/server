#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
기존 Pinecone 데이터를 활용한 LLM 테스트 스크립트

이미 Pinecone에 저장된 벡터 데이터를 사용하여:
1. RAG 컨텍스트 검색 테스트
2. LLM 역량 평가 테스트
3. JSON 형식 응답 테스트
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Django 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_cheat.settings")

import django
django.setup()

from core.services.conversation_rag_service import ConversationRAGService
from core.services.gemini_service import GeminiService
from core.services.firebase_personas import update_persona_document

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_llm_with_existing_pinecone():
    """기존 Pinecone 데이터를 활용한 LLM 테스트를 수행합니다."""
    
    # 기존에 저장된 사용자 ID (이전 테스트에서 사용한 것)
    user_id = "my_test_user"  # 또는 "test_user_large_file"
    document_id = "within_overall_evaluation"
    
    try:
        logger.info("=== 기존 Pinecone 데이터를 활용한 LLM 테스트 시작 ===")
        
        # 1단계: 대화 RAG 서비스 초기화
        logger.info("1단계: 대화 RAG 서비스 초기화 중...")
        conversation_rag_service = ConversationRAGService()
        gemini_service = GeminiService()
        
        # 2단계: Pinecone 데이터 확인
        logger.info("2단계: Pinecone 데이터 확인 중...")
        try:
            from core.services.pinecone_service import get_pinecone_service
            pinecone_service = get_pinecone_service()
            
            # 인덱스 통계 확인
            stats = pinecone_service.index.describe_index_stats()
            namespaces = stats.get('namespaces', {})
            
            if user_id in namespaces:
                namespace_stats = namespaces[user_id]
                vector_count = namespace_stats.get('vector_count', 0)
                logger.info(f"✅ 사용자 {user_id}의 벡터 수: {vector_count}개")
            else:
                logger.warning(f"⚠️ 사용자 {user_id}의 네임스페이스를 찾을 수 없음")
                logger.info(f"사용 가능한 네임스페이스: {list(namespaces.keys())}")
                return
                
        except Exception as exc:
            logger.error(f"❌ Pinecone 데이터 확인 실패: {exc}")
            return
        
        # 3단계: RAG 컨텍스트 검색 테스트
        logger.info("3단계: RAG 컨텍스트 검색 테스트 중...")
        
        test_queries = [
            "프로그래밍 기술과 개발 능력",
            "프로젝트 관리 및 팀 협업",
            "문제 해결 및 창의적 사고",
            "커뮤니케이션 및 리더십"
        ]
        
        rag_results = {}
        for query in test_queries:
            logger.info(f"  쿼리: '{query}'")
            try:
                context = await conversation_rag_service.get_rag_context(
                    query=query,
                    user_id=user_id,
                    top_k=3
                )
                
                if context:
                    logger.info(f"  ✅ 컨텍스트 조회 성공: {len(context):,}자")
                    rag_results[query] = context
                else:
                    logger.warning(f"  ⚠️ 컨텍스트를 찾을 수 없음")
                    rag_results[query] = None
                    
            except Exception as exc:
                logger.error(f"  ❌ RAG 검색 실패: {exc}")
                rag_results[query] = None
        
        # 4단계: LLM 역량 평가 테스트 (JSON 형식)
        logger.info("4단계: LLM 역량 평가 테스트 중...")
        
        competencies = [
            {
                "name": "프로그래밍_기술",
                "description": "프로그래밍 언어, 프레임워크, 개발 도구에 대한 이해와 활용 능력",
                "query": "프로그래밍 기술과 개발 능력"
            },
            {
                "name": "프로젝트_관리", 
                "description": "프로젝트 기획, 일정 관리, 팀 협업, 리소스 관리 능력",
                "query": "프로젝트 관리 및 팀 협업"
            },
            {
                "name": "문제_해결",
                "description": "문제 분석, 해결책 도출, 비판적 사고, 창의적 접근 능력", 
                "query": "문제 해결 및 창의적 사고"
            },
            {
                "name": "협업_소통",
                "description": "팀워크, 커뮤니케이션, 갈등 해결, 리더십 능력",
                "query": "커뮤니케이션 및 리더십"
            }
        ]
        
        evaluation_results = {}
        
        for competency in competencies:
            logger.info(f"\n--- {competency['name']} 역량 평가 중... ---")
            
            # 해당 역량에 대한 RAG 컨텍스트 가져오기
            context = rag_results.get(competency['query'])
            
            if context:
                logger.info(f"RAG 컨텍스트 사용: {len(context):,}자")
                
                # LLM 역량 평가 수행
                evaluation_data = await evaluate_competency_with_citations(
                    competency_name=competency['name'],
                    competency_description=competency['description'],
                    context=context,
                    gemini_service=gemini_service
                )
                
                if evaluation_data:
                    logger.info(f"✅ {competency['name']} 역량 평가 완료")
                    logger.info(f"점수: {evaluation_data.get('score', 'N/A')}/10")
                    
                    # Firestore에 저장
                    save_success = await save_competency_to_firestore(
                        user_id=user_id,
                        persona_id=document_id,
                        competency_data=evaluation_data
                    )
                    
                    if save_success:
                        evaluation_results[competency['name']] = evaluation_data
                        logger.info(f"✅ {competency['name']} 결과 Firestore 저장 완료")
                    else:
                        logger.error(f"❌ {competency['name']} 결과 Firestore 저장 실패")
                else:
                    logger.warning(f"⚠️ {competency['name']} 역량 평가 실패")
            else:
                logger.warning(f"⚠️ {competency['name']}에 대한 RAG 컨텍스트 없음")
        
        # 5단계: 최종 평가 수행
        logger.info("\n5단계: 최종 평가 수행 중...")
        
        if evaluation_results:
            # 모든 역량 평가 결과를 합쳐서 최종 평가 수행
            final_evaluation = await perform_final_evaluation(
                competency_results=evaluation_results,
                gemini_service=gemini_service
            )
            
            if final_evaluation:
                logger.info("✅ 최종 평가 완료")
                
                # 최종 평가 결과를 Firestore에 저장
                final_save_success = await save_final_evaluation_to_firestore(
                    user_id=user_id,
                    persona_id=document_id,
                    final_evaluation_text=final_evaluation
                )
                
                if final_save_success:
                    logger.info("✅ 최종 평가 결과 Firestore 저장 완료")
                else:
                    logger.error("❌ 최종 평가 결과 Firestore 저장 실패")
            else:
                logger.warning("⚠️ 최종 평가 실패")
        
        # 6단계: 결과 요약
        logger.info("\n=== LLM 역량 평가 결과 요약 ===")
        
        # 개별 역량 평가 결과 요약
        for competency_name, result in evaluation_results.items():
            if result:
                logger.info(f"\n📊 {competency_name}:")
                logger.info(f"  점수: {result.get('score', 'N/A')}/100")
                logger.info(f"  핵심 인사이트: {len(result.get('key_insights', []))}개")
                
                # 첫 번째 핵심 인사이트 출력
                insights = result.get('key_insights', [])
                if insights:
                    logger.info(f"  주요 인사이트: {insights[0][:100]}...")
        
        # 최종 평가 결과 요약
        if evaluation_results:
            logger.info(f"\n🎯 최종 평가:")
            logger.info(f"  {final_evaluation}")
        
        logger.info(f"\n✅ 총 {len(evaluation_results)}개 역량 평가 완료")
        logger.info("=== 기존 Pinecone 데이터를 활용한 LLM 테스트 완료 ===")
        
    except Exception as exc:
        logger.error(f"테스트 실패: {exc}")
        raise


async def evaluate_competency_with_citations(
    competency_name: str,
    competency_description: str,
    context: str,
    gemini_service: GeminiService
) -> Dict[str, Any]:
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
3. 평가 점수(1-100점)와 함께 구체적인 이유를 설명해주세요.
4. "key_insights" 배열에 핵심 인사이트를 3개를 포함해주세요.

중요: 위 요청에 대해 반드시 유효한 JSON 형식으로만 응답해주세요.
- 다른 설명이나 마크다운 코드 블록(```json)은 절대 포함하지 마세요.
- JSON 객체만 반환해주세요.
- 응답은 반드시 {{로 시작하고 }}로 끝나야 합니다.
- 모든 문자열 값은 반드시 따옴표로 감싸주세요.

=== 응답 형식 (JSON) ===
{{
    "competency_name": "{competency_name}",
    "score": 1~100,
    "score_explanation": "점수에 대한 구체적인 설명",
    "key_insights": [
        "핵심 인사이트 1",
        "핵심 인사이트 2",
        "핵심 인사이드 3"
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
            # JSON 파싱
            try:
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


async def perform_final_evaluation(
    competency_results: Dict[str, Any],
    gemini_service: GeminiService
) -> Dict[str, Any]:
    """모든 역량 평가 결과를 종합하여 최종 평가를 수행합니다."""
    
    # 모든 역량 평가 결과를 컨텍스트로 구성
    context_parts = []
    for competency_name, result in competency_results.items():
        if result:
            context_parts.append(f"""
=== {competency_name} 역량 평가 결과 ===
점수: {result.get('score', 'N/A')}/100
점수 설명: {result.get('score_explanation', '')}
핵심 인사이트:
{chr(10).join(f"- {insight}" for insight in result.get('key_insights', []))}
""")
    
    context = "\n".join(context_parts)
    
    final_evaluation_prompt = f"""
다음은 한 사용자의 역량 평가 결과입니다.

=== 개별 역량 평가 결과 ===
{context}

=== 최종 평가 요청 ===
위의 모든 역량 평가 결과를 종합하여 사용자의 전체적인 역량 수준을 평가해주세요. 

**별도의 소제목이나 구분 기호를 사용하지 말고**, 아래 내용을 모두 자연스럽게 하나의 완성된 글로 엮어서 800자 이내로 서술해주세요.
1. 전체적인 역량 수준에 대한 종합적인 평가
2. 주요 강점과 우수한 영역
3. 개선이 필요한 부분과 구체적인 개선 방안
4. 커리어 관점에서의 인사이트와 조언

평가는 자연스러운 문장으로 작성해주세요. JSON 형식이 아닌 일반 텍스트로 응답해주세요.
"""
    
    try:
        logger.info(f"최종 평가 수행 중: {final_evaluation_prompt}")
        # Gemini를 사용한 최종 평가 수행 (일반 텍스트)
        evaluation_result = await gemini_service.generate_structured_response(
            prompt=final_evaluation_prompt,
            response_format="text"
        )
        
        if evaluation_result:
            # 단순 문자열로 반환
            return evaluation_result.strip()
        else:
            logger.warning("최종 평가 결과가 비어있음")
            return None
            
    except Exception as exc:
        logger.error(f"최종 평가 실패: {exc}")
        return None


async def save_final_evaluation_to_firestore(
    user_id: str,
    persona_id: str,
    final_evaluation_text: str
) -> bool:
    """최종 평가 결과를 Firestore에 저장합니다."""
    
    try:
        # Firestore 문서 업데이트 데이터 구성 (단순 문자열)
        update_payload = {
            "final_evaluation": final_evaluation_text
        }
        
        # Firestore 문서 업데이트
        result = update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload=update_payload
        )
        
        if result:
            logger.info("✅ 최종 평가 결과 Firestore 저장 완료")
            return True
        else:
            logger.error("❌ 최종 평가 결과 Firestore 저장 실패")
            return False
            
    except Exception as exc:
        logger.error(f"최종 평가 Firestore 저장 실패: {exc}")
        return False


async def save_competency_to_firestore(
    user_id: str,
    persona_id: str,
    competency_data: Dict[str, Any]
) -> bool:
    """역량 평가 결과를 Firestore에 저장합니다."""
    
    try:
        # Firestore 문서 업데이트 데이터 구성 (중첩 구조)
        update_payload = {
            "competencies": {
                competency_data['competency_name']: {
                    "score": competency_data.get("score", 0),
                    "score_explanation": competency_data.get("score_explanation", ""),
                    "key_insights": competency_data.get("key_insights", []),
                    "evaluated_at": "2025-01-27T16:00:00.000Z"  # 실제로는 현재 시간
                }
            }
        }
        
        # Firestore 문서 업데이트
        result = update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload=update_payload
        )
        
        if result:
            logger.info(f"✅ {competency_data['competency_name']} 역량 평가 결과 Firestore 저장 완료")
            return True
        else:
            logger.error(f"❌ {competency_data['competency_name']} 역량 평가 결과 Firestore 저장 실패")
            return False
            
    except Exception as exc:
        logger.error(f"Firestore 저장 실패: {exc}")
        return False


def main():
    """메인 함수."""
    asyncio.run(test_llm_with_existing_pinecone())


if __name__ == "__main__":
    main()
