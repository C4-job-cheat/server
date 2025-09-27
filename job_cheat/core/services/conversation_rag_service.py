#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대화 내역 RAG 시스템 서비스

이 모듈은 ChatGPT 대화 내역을 청크 단위로 처리하고,
Firestore에 저장한 후 Pinecone에 임베딩하여 RAG 검색을 수행하는 서비스를 제공합니다.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime


from .cohere_service import CohereService
from .pinecone_service import PineconeService
from .firebase_storage import download_persona_json

logger = logging.getLogger(__name__)


class ConversationRAGServiceError(RuntimeError):
    """대화 RAG 서비스 관련 예외."""


class ConversationRAGService:
    """대화 내역 RAG 시스템을 관리하는 서비스."""
    
    def __init__(self):
        """서비스 초기화."""
        self.cohere_service = CohereService()
        self.pinecone_service = PineconeService()
    
    def process_conversation_json(self, user_id: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Firebase Storage에서 JSON 파일을 다운로드하여 대화 내역을 청크 단위로 처리합니다.
        
        Args:
            user_id: 사용자 ID
            document_id: 문서 ID (JSON 파일 ID)
            
        Returns:
            청크 딕셔너리들의 리스트
            
        Raises:
            ConversationRAGServiceError: 처리 실패 시
        """
        try:
            logger.info(f"대화 JSON 파일 처리 시작: user_id={user_id}, document_id={document_id}")
            
            # Firebase Storage에서 JSON 파일 다운로드
            result = download_persona_json(
                user_id=user_id,
                document_id=document_id
            )
            
            if not result["exists"]:
                raise ConversationRAGServiceError(f"JSON 파일을 찾을 수 없습니다: {result['path']}")
            
            # JSON 내용 파싱
            json_content = result["content"]
            data = json.loads(json_content)
            
            chunks = []
            chunk_index = 0
            
            # 대화 내역 순회
            conversations = data.get('conversations', [])
            for conv in conversations:
                messages = conv.get('messages', [])
                
                for i, message in enumerate(messages):
                    role = message.get('role')
                    text = message.get('content', '')
                    
                    if not text.strip():
                        continue
                    
                    # 청크 생성
                    chunk = {
                        'chunk_id': f"{document_id}-{chunk_index}",
                        'role': role,
                        'text': text,
                        'document_id': document_id,
                        'conversation_id': conv.get('conversation_id'),
                        'conversation_title': conv.get('title'),
                        'timestamp': datetime.utcnow().isoformat(),
                        'chunk_index': chunk_index
                    }
                    
                    chunks.append(chunk)
                    chunk_index += 1
            
            logger.info(f"청크 처리 완료: 총 {len(chunks)}개 청크 생성")
            return chunks
            
        except Exception as exc:
            logger.error(f"대화 JSON 처리 실패: {exc}")
            raise ConversationRAGServiceError(f"대화 JSON 처리 실패: {exc}") from exc
    
    
    async def embed_and_upsert_to_pinecone(self, chunks: List[Dict[str, Any]], user_id: str) -> bool:
        """
        User 발화만 임베딩하여 Pinecone에 업로드합니다.
        사용자별 namespace를 사용하여 데이터를 격리합니다.
        
        Args:
            chunks: 처리할 청크 리스트
            user_id: 사용자 ID (namespace로 사용)
            
        Returns:
            업로드 성공 여부
            
        Raises:
            ConversationRAGServiceError: 업로드 실패 시
        """
        try:
            logger.info(f"Pinecone 임베딩 및 업로드 시작: user_id={user_id}")
            
            # User 발화만 필터링
            user_chunks = [chunk for chunk in chunks if chunk['role'] == 'user']
            
            if not user_chunks:
                logger.warning("User 발화가 없어 업로드를 건너뜁니다.")
                return True
            
            logger.info(f"User 발화 {len(user_chunks)}개 임베딩 시작")
            
            # 텍스트 추출
            texts = [chunk['text'] for chunk in user_chunks]
            
            # 임베딩 생성
            embeddings = await self.cohere_service.embed_texts(
                texts,
                model=self.cohere_service._default_model,
                input_type="search_document"
            )
            
            if not embeddings:
                raise ConversationRAGServiceError("임베딩 생성 실패")
            
            # Pinecone 업로드 데이터 준비 (User 발화 + Assistant 답변 포함)
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(user_chunks, embeddings)):
                # Assistant 답변 찾기 (이전 청크가 Assistant인 경우)
                assistant_text = ""
                current_index = chunk['chunk_index']
                prev_index = current_index - 1
                
                # 이전 청크가 Assistant인지 확인
                for all_chunk in chunks:
                    if (all_chunk['chunk_index'] == prev_index and 
                        all_chunk['role'] == 'assistant'):
                        assistant_text = all_chunk['text']
                        break
                
                vector_data = {
                    'id': chunk['chunk_id'],
                    'values': embedding,
                    'metadata': {
                        'text': chunk['text'],  # User 발화
                        'assistant_text': assistant_text,  # Assistant 답변
                        'document_id': chunk['document_id'],
                        'conversation_id': chunk['conversation_id'],
                        'conversation_title': chunk['conversation_title'],
                        'timestamp': chunk['timestamp'],
                        'role': chunk['role']
                    }
                }
                vectors.append(vector_data)
            
            # Pinecone에 사용자별 namespace로 배치 업로드 (100개씩)
            batch_size = 100
            total_vectors = len(vectors)
            uploaded_count = 0
            
            for i in range(0, total_vectors, batch_size):
                batch_vectors = vectors[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_vectors + batch_size - 1) // batch_size
                
                logger.info(f"Pinecone 배치 {batch_num}/{total_batches} 업로드 중: {len(batch_vectors)}개 벡터")
                
                # 배치 업로드 (user_id를 namespace로 사용)
                self.pinecone_service.upsert_vectors(batch_vectors, namespace=user_id)
                uploaded_count += len(batch_vectors)
                
                logger.info(f"Pinecone 배치 {batch_num} 업로드 완료: {uploaded_count}/{total_vectors}개 벡터 업로드됨")
            
            logger.info(f"Pinecone 업로드 완료: 총 {uploaded_count}개 벡터 (namespace: {user_id})")
            return True
            
        except Exception as exc:
            logger.error(f"Pinecone 임베딩 및 업로드 실패: {exc}")
            raise ConversationRAGServiceError(f"Pinecone 임베딩 및 업로드 실패: {exc}") from exc
    
    async def get_rag_context(self, query: str, user_id: str, top_k: int = 5) -> str:
        """
        RAG 검색을 통해 관련 컨텍스트를 조회합니다.
        
        Args:
            query: 사용자 질문
            user_id: 사용자 ID
            top_k: 검색할 유사한 발화 개수 (기본값: 5)
            
        Returns:
            조합된 컨텍스트 문자열 (답변 → 질문 순서)
            
        Raises:
            ConversationRAGServiceError: 검색 실패 시
        """
        try:
            logger.info(f"RAG 컨텍스트 검색 시작: query='{query}', user_id='{user_id}'")
            
            # 1. 검색 단계: 쿼리 임베딩 및 유사도 검색
            query_embeddings = await self.cohere_service.embed_texts(
                [query],
                model="embed-multilingual-v3.0",
                input_type="search_query"
            )
            
            if not query_embeddings:
                raise ConversationRAGServiceError("쿼리 임베딩 생성 실패")
            
            # Pinecone에서 해당 사용자의 User 발화만 검색 (user_id namespace 사용)
            search_response = self.pinecone_service.query_similar(
                query_embeddings[0],
                top_k=top_k,
                include_metadata=True,
                namespace=user_id  # user_id를 namespace로 사용
            )
            
            matches = search_response.get('matches', [])
            if not matches:
                logger.warning("해당 사용자의 대화에서 유사한 발화를 찾을 수 없습니다.")
                return ""
            
            # 모든 매치를 처리하여 컨텍스트 조합
            context_parts = []
            
            for i, match in enumerate(matches):
                metadata = match.get('metadata', {})
                logger.info(f"유사한 User 청크 {i+1} 발견: {match['id']}")
                
                # Assistant 답변 추가 (먼저) - Pinecone 메타데이터에서 직접 가져오기
                assistant_text = metadata.get('assistant_text', '')
                if assistant_text:
                    context_parts.append(f"어시스턴트: {assistant_text}")
                
                # User 발화 추가 (나중에) - Pinecone 메타데이터에서 직접 가져오기
                user_text = metadata.get('text', '')
                if user_text:
                    context_parts.append(f"사용자: {user_text}")
                
                # 각 대화 사이에 구분선 추가
                if i < len(matches) - 1:
                    context_parts.append("---")
            
            # 최종 컨텍스트 조합 (답변 → 질문 순서)
            final_context = "\n\n".join(context_parts)
            
            logger.info(f"RAG 컨텍스트 검색 완료: {len(final_context)}자")
            return final_context
            
        except Exception as exc:
            logger.error(f"RAG 컨텍스트 검색 실패: {exc}")
            raise ConversationRAGServiceError(f"RAG 컨텍스트 검색 실패: {exc}") from exc


# 편의 함수들
def process_conversation_json(user_id: str, document_id: str) -> List[Dict[str, Any]]:
    """Firebase Storage에서 대화 JSON 파일을 다운로드하여 청크 리스트를 반환합니다."""
    service = ConversationRAGService()
    return service.process_conversation_json(user_id, document_id)




async def embed_and_upsert_to_pinecone(chunks: List[Dict[str, Any]], user_id: str) -> bool:
    """User 발화를 임베딩하여 Pinecone에 업로드합니다."""
    service = ConversationRAGService()
    return await service.embed_and_upsert_to_pinecone(chunks, user_id)


async def get_rag_context(query: str, user_id: str, top_k: int = 5) -> str:
    """RAG 검색을 통해 관련 컨텍스트를 조회합니다."""
    service = ConversationRAGService()
    return await service.get_rag_context(query, user_id, top_k)