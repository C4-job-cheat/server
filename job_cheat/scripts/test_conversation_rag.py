#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대화 RAG 시스템 테스트 스크립트

이 스크립트는 conversation_rag_service.py의 함수들을 테스트합니다.
"""

import asyncio
import json
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

from core.services.conversation_rag_service import (
    process_conversation_json,
    embed_and_upsert_to_pinecone,
    get_rag_context
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_conversation_rag_pipeline():
    """전체 RAG 파이프라인을 테스트합니다."""
    
    # 테스트 데이터 설정
    user_id = "my_test_user"
    document_id = "7e17f2bf-e124-44b1-93c9-b7a30102cab7"
    
    try:
        logger.info("=== 대화 RAG 시스템 테스트 시작 ===")
        
        # 1단계: JSON 파일 처리 (Firebase Storage에서 다운로드)
        logger.info("1단계: Firebase Storage에서 JSON 파일 다운로드 및 처리 중...")
        chunks = process_conversation_json(user_id, document_id)
        logger.info(f"✅ 청크 생성 완료: {len(chunks)}개")
        
        # 청크 정보 출력
        for i, chunk in enumerate(chunks[:3]):  # 처음 3개만 출력
            logger.info(f"  청크 {i}: {chunk['chunk_id']} - {chunk['role']} - {chunk['text'][:50]}...")
        
        # 2단계: Pinecone 임베딩 및 업로드
        logger.info("2단계: Pinecone 임베딩 및 업로드 중...")
        embed_success = await embed_and_upsert_to_pinecone(chunks, user_id)
        if embed_success:
            logger.info("✅ Pinecone 업로드 완료")
        else:
            logger.error("❌ Pinecone 업로드 실패")
            return
        
        # 3단계: RAG 검색 테스트
        logger.info("3단계: RAG 검색 테스트 중...")
        test_queries = [
            "해커톤이 무엇인가요?",
            "PM의 역할은 무엇인가요?",
            "백엔드 개발자는 무엇을 하나요?"
        ]
        
        for query in test_queries:
            logger.info(f"  쿼리: '{query}'")
            context = await get_rag_context(query, user_id)
            if context:
                logger.info(f"  ✅ 컨텍스트 조회 성공: {len(context)}자")
                logger.info(f"  컨텍스트 미리보기: {context[:200]}...")
            else:
                logger.warning(f"  ⚠️ 컨텍스트를 찾을 수 없음")
            logger.info("")
        
        logger.info("=== 대화 RAG 시스템 테스트 완료 ===")
        
    except Exception as exc:
        logger.error(f"테스트 실패: {exc}")
        raise


def main():
    """메인 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description="대화 RAG 시스템 테스트")
    
    args = parser.parse_args()
    
    asyncio.run(test_conversation_rag_pipeline())
    

if __name__ == "__main__":
    main()
