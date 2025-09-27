#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pinecone 검색 디버깅 스크립트

Pinecone에 저장된 벡터를 확인하고 검색 문제를 진단합니다.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Django 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_cheat.settings")

import django
django.setup()

from core.services.pinecone_service import get_pinecone_service

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_pinecone_search():
    """Pinecone 검색을 디버깅합니다."""
    
    user_id = "test_user_real_data"
    
    try:
        logger.info("=== Pinecone 검색 디버깅 시작 ===")
        
        # Pinecone 서비스 초기화
        pinecone_service = get_pinecone_service()
        
        # 1단계: 인덱스 통계 확인
        logger.info("1단계: Pinecone 인덱스 통계 확인 중...")
        try:
            stats = pinecone_service.index.describe_index_stats()
            logger.info(f"✅ 인덱스 통계: {stats}")
            
            # 네임스페이스별 벡터 수 확인
            namespaces = stats.get('namespaces', {})
            if user_id in namespaces:
                namespace_stats = namespaces[user_id]
                vector_count = namespace_stats.get('vector_count', 0)
                logger.info(f"✅ 사용자 {user_id}의 벡터 수: {vector_count}개")
            else:
                logger.warning(f"⚠️ 사용자 {user_id}의 네임스페이스를 찾을 수 없음")
                logger.info(f"사용 가능한 네임스페이스: {list(namespaces.keys())}")
        except Exception as exc:
            logger.error(f"❌ 인덱스 통계 확인 실패: {exc}")
            return
        
        # 2단계: 랜덤 벡터로 검색 테스트
        logger.info("2단계: 랜덤 벡터로 검색 테스트 중...")
        try:
            # 1024차원 랜덤 벡터 생성
            import random
            random_vector = [random.random() for _ in range(1024)]
            
            search_response = pinecone_service.query_similar(
                vector=random_vector,
                top_k=5,
                include_metadata=True,
                namespace=user_id
            )
            
            matches = search_response.get('matches', [])
            logger.info(f"✅ 랜덤 벡터 검색 결과: {len(matches)}개 매치")
            
            for i, match in enumerate(matches):
                logger.info(f"  매치 {i+1}: ID={match['id']}, Score={match['score']:.4f}")
                metadata = match.get('metadata', {})
                logger.info(f"    메타데이터: {metadata}")
                
        except Exception as exc:
            logger.error(f"❌ 랜덤 벡터 검색 실패: {exc}")
            return
        
        # 3단계: 실제 쿼리로 검색 테스트
        logger.info("3단계: 실제 쿼리로 검색 테스트 중...")
        try:
            from core.services.cohere_service import get_cohere_service
            
            cohere_service = get_cohere_service()
            query_embeddings = await cohere_service.embed_texts(
                ["해커톤이 무엇인가요?"],
                model="embed-multilingual-v3.0",
                input_type="search_query"
            )
            
            if query_embeddings:
                query_vector = query_embeddings[0]
                logger.info(f"✅ 쿼리 임베딩 생성 완료: {len(query_vector)}차원")
                
                search_response = pinecone_service.query_similar(
                    vector=query_vector,
                    top_k=5,
                    include_metadata=True,
                    namespace=user_id
                )
                
                matches = search_response.get('matches', [])
                logger.info(f"✅ 실제 쿼리 검색 결과: {len(matches)}개 매치")
                
                for i, match in enumerate(matches):
                    logger.info(f"  매치 {i+1}: ID={match['id']}, Score={match['score']:.4f}")
                    metadata = match.get('metadata', {})
                    logger.info(f"    텍스트: {metadata.get('text', 'N/A')[:100]}...")
                    logger.info(f"    역할: {metadata.get('role', 'N/A')}")
                    
            else:
                logger.error("❌ 쿼리 임베딩 생성 실패")
                
        except Exception as exc:
            logger.error(f"❌ 실제 쿼리 검색 실패: {exc}")
            return
        
        logger.info("=== Pinecone 검색 디버깅 완료 ===")
        
    except Exception as exc:
        logger.error(f"디버깅 실패: {exc}")
        raise


def main():
    """메인 함수."""
    asyncio.run(debug_pinecone_search())


if __name__ == "__main__":
    main()
