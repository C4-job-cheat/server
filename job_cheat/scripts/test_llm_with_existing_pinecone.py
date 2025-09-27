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
    user_id = "test_user_structured_eval"  # 또는 "test_user_large_file"
    document_id = "chat_converted_structured"
    
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
        
        # 5단계: 결과 요약
        logger.info("\n=== LLM 역량 평가 결과 요약 ===")
        for competency_name, result in evaluation_results.items():
            if result:
                logger.info(f"\n📊 {competency_name}:")
                logger.info(f"  점수: {result.get('score', 'N/A')}/10")
                logger.info(f"  강점: {len(result.get('strengths', []))}개")
                logger.info(f"  개선점: {len(result.get('improvements', []))}개")
                logger.info(f"  핵심 인사이트: {len(result.get('key_insights', []))}개")
                
                # 첫 번째 강점과 개선점 출력
                strengths = result.get('strengths', [])
                if strengths:
                    logger.info(f"  주요 강점: {strengths[0].get('description', '')[:100]}...")
                
                improvements = result.get('improvements', [])
                if improvements:
                    logger.info(f"  주요 개선점: {improvements[0].get('description', '')[:100]}...")
        
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


async def save_competency_to_firestore(
    user_id: str,
    persona_id: str,
    competency_data: Dict[str, Any]
) -> bool:
    """역량 평가 결과를 Firestore에 저장합니다."""
    
    try:
        # Firestore 문서 업데이트 데이터 구성
        update_payload = {
            f"competencies.{competency_data['competency_name']}": {
                "score": competency_data.get("score", 0),
                "score_explanation": competency_data.get("score_explanation", ""),
                "strengths": competency_data.get("strengths", []),
                "improvements": competency_data.get("improvements", []),
                "overall_assessment": competency_data.get("overall_assessment", ""),
                "key_insights": competency_data.get("key_insights", []),
                "evaluated_at": "2025-01-27T16:00:00.000Z"  # 실제로는 현재 시간
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
