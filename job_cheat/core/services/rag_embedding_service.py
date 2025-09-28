"""
RAG 임베딩 서비스 모듈
사용자 대화기록을 임베딩으로 변환하는 서비스를 제공합니다.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import numpy as np

from django.conf import settings

from .cohere_service import get_cohere_service
from .pinecone_service import get_pinecone_service

import tiktoken

MAX_TOKENS_PER_CHUNK = getattr(settings, "COHERE_MAX_TOKENS_PER_CHUNK", 400)
TOKENIZER = tiktoken.get_encoding("cl100k_base")

logger = logging.getLogger(__name__)


class RAGEmbeddingServiceError(RuntimeError):
    """RAG 임베딩 서비스 관련 예외."""


class RAGEmbeddingService:
    """사용자 대화기록을 임베딩으로 변환하는 서비스"""
    
    def __init__(self):
        """임베딩 서비스 초기화"""
        self.cohere_service = get_cohere_service()
        self.pinecone_service = get_pinecone_service()
        self.embedding_model = getattr(settings, "COHERE_EMBED_MODEL", "embed-multilingual-v3.0")
        
        logger.info("RAG 임베딩 서비스 초기화 완료")
    
    async def extract_user_conversations(self, json_content: str) -> List[Dict[str, Any]]:
        """
        JSON에서 사용자 발화만 추출
        
        Args:
            json_content: ChatGPT 대화 JSON 내용
            
        Returns:
            사용자 대화 리스트 (conversation_id, content 포함)
            
        Raises:
            RAGEmbeddingServiceError: 대화 추출 실패 시
        """
        if not json_content:
            raise ValueError("JSON 내용이 비어있습니다.")
        
        try:
            logger.info("사용자 대화 추출 시작")
            
            # JSON 파싱
            try:
                data = json.loads(json_content)
            except json.JSONDecodeError as exc:
                raise RAGEmbeddingServiceError(f"JSON 파싱 실패: {exc}") from exc
            
            # 대화 데이터 구조 확인 및 사용자 발화 추출
            conversations = []

            if isinstance(data, dict) and "conversations" in data:
                # 표준 ChatGPT 내보내기 형식
                for conv_data in data["conversations"]:
                    conversation_title = conv_data.get("title")
                    last_assistant_message: Optional[str] = None
                    if isinstance(conv_data, dict) and "messages" in conv_data:
                        for message in conv_data["messages"]:
                            role = message.get("role")
                            content = message.get("content", "")
                            if role == "user":
                                conversations.append({
                                    "conversation_id": conv_data.get("id", f"conv_{len(conversations)}"),
                                    "content": content,
                                    "timestamp": message.get("timestamp"),
                                    "role": "user",
                                    "conversation_title": conversation_title,
                                    "question": last_assistant_message,
                                })
                            elif role == "assistant":
                                last_assistant_message = content

            elif isinstance(data, list):
                # 간단한 리스트 형식
                last_assistant_message: Optional[str] = None
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        role = item.get("role")
                        content = item.get("content", "")
                        if role == "user":
                            conversations.append({
                                "conversation_id": f"conv_{i}",
                                "content": content,
                                "timestamp": item.get("timestamp"),
                                "role": "user",
                                "conversation_title": item.get("title"),
                                "question": last_assistant_message,
                            })
                        elif role == "assistant":
                            last_assistant_message = content
                        elif "messages" in item:
                            conversation_title = item.get("title")
                            nested_assistant_message: Optional[str] = None
                            for j, message in enumerate(item["messages"]):
                                msg_role = message.get("role")
                                msg_content = message.get("content", "")
                                if msg_role == "user":
                                    conversations.append({
                                        "conversation_id": item.get("id", f"conv_{i}_{j}"),
                                        "content": msg_content,
                                        "timestamp": message.get("timestamp"),
                                        "role": "user",
                                        "conversation_title": conversation_title,
                                        "question": nested_assistant_message,
                                    })
                                elif msg_role == "assistant":
                                    nested_assistant_message = msg_content
            
            # 빈 내용 필터링
            filtered_conversations = [
                conv for conv in conversations 
                if conv["content"] and conv["content"].strip()
            ]
            
            logger.info(f"사용자 대화 추출 완료 - 총 {len(filtered_conversations)}개 대화")
            return filtered_conversations
            
        except Exception as exc:
            logger.error(f"사용자 대화 추출 실패: {exc}")
            raise RAGEmbeddingServiceError(f"대화 추출 실패: {exc}") from exc
    
    async def generate_embeddings(
        self,
        conversations: List[Dict[str, Any]],
        *,
        competencies: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        대화 내용을 임베딩으로 변환
        
        Args:
            conversations: 대화 데이터 리스트
            
        Returns:
            임베딩 데이터 리스트
            
        Raises:
            RAGEmbeddingServiceError: 임베딩 생성 실패 시
        """
        if not conversations:
            logger.warning("임베딩할 대화 데이터가 비어있습니다.")
            return []
        
        try:
            logger.info(f"임베딩 생성 시작 - 대화 개수: {len(conversations)}")

            chunked_items: List[Dict[str, Any]] = []
            texts: List[str] = []

            for conv in conversations:
                content = conv["content"]
                title = conv.get("conversation_title")
                token_ids = TOKENIZER.encode(content)
                total_chunks = max(1, (len(token_ids) + MAX_TOKENS_PER_CHUNK - 1) // MAX_TOKENS_PER_CHUNK)

                if len(token_ids) <= MAX_TOKENS_PER_CHUNK:
                    chunked_items.append({
                        "conversation": conv,
                        "chunk_index": 0,
                        "text": content,
                        "title": title,
                        "total_chunks": total_chunks,
                    })
                    texts.append(content)
                    continue

                start = 0
                chunk_index = 0
                while start < len(token_ids):
                    end = start + MAX_TOKENS_PER_CHUNK
                    chunk_token_ids = token_ids[start:end]
                    chunk_text = TOKENIZER.decode(chunk_token_ids)
                    chunked_items.append({
                        "conversation": conv,
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                        "title": title,
                        "total_chunks": total_chunks,
                    })
                    texts.append(chunk_text)
                    start = end
                    chunk_index += 1

            if not texts:
                logger.warning("임베딩할 텍스트가 없어 요청을 중단했습니다.")
                return []

            embeddings = await self.cohere_service.embed_texts(
                texts,
                model=self.embedding_model,
                input_type="search_document",
            )

            embedding_data: List[Dict[str, Any]] = []
            for chunk_info, embedding in zip(chunked_items, embeddings):
                conv = chunk_info["conversation"]
                chunk_index = chunk_info["chunk_index"]
                text = chunk_info["text"]
                title = chunk_info["title"]
                total_chunks = chunk_info["total_chunks"]

                conversation_id = conv["conversation_id"]
                if chunk_index > 0:
                    conversation_id = f"{conversation_id}_chunk_{chunk_index}"

                prev_chunk_id = None
                if chunk_index == 0:
                    prev_chunk_id = None
                elif chunk_index == 1:
                    prev_chunk_id = conv["conversation_id"]
                else:
                    prev_chunk_id = f"{conv['conversation_id']}_chunk_{chunk_index - 1}"

                next_chunk_id = None
                if chunk_index < total_chunks - 1:
                    if chunk_index == 0:
                        next_chunk_id = f"{conv['conversation_id']}_chunk_1"
                    else:
                        next_chunk_id = f"{conv['conversation_id']}_chunk_{chunk_index + 1}"

                embedding_data.append({
                    "conversation_id": conversation_id,
                    "content": text,
                    "embedding": embedding,
                    "competency_tags": [],
                    "created_at": conv.get("timestamp"),
                    "role": conv["role"],
                    "parent_conversation_id": conv["conversation_id"],
                    "chunk_index": chunk_index,
                    "original_content": conv["content"],
                    "conversation_title": title,
                    "next_chunk_id": next_chunk_id,
                    "previous_chunk_id": prev_chunk_id,
                })

            if competencies:
                embedding_data = await self._tag_embeddings(
                    embedding_data=embedding_data,
                    competency_definitions=competencies,
                )
            
            logger.info(f"임베딩 생성 완료 - 총 {len(embedding_data)}개")
            return embedding_data
            
        except Exception as exc:
            logger.error(f"임베딩 생성 실패: {exc}")
            raise RAGEmbeddingServiceError(f"임베딩 생성 실패: {exc}") from exc
    
    def _format_pinecone_vectors(self, embeddings: List[Dict[str, Any]]) -> List[dict]:
        vectors: List[dict] = []
        for item in embeddings:
            metadata = {
                "content": item["content"],
                "role": item.get("role"),
                "created_at": str(item.get("created_at")) if item.get("created_at") is not None else None,
                "parent_conversation_id": item.get("parent_conversation_id"),
                "chunk_index": item.get("chunk_index"),
                "conversation_title": item.get("conversation_title"),
                "next_chunk_id": item.get("next_chunk_id"),
                "previous_chunk_id": item.get("previous_chunk_id"),
                "competency_tags": item.get("competency_tags", []),
                "question": item.get("question"),
            }
            metadata = {k: v for k, v in metadata.items() if v is not None}
            vectors.append(
                {
                    "id": item["conversation_id"],
                    "values": item["embedding"],
                    "metadata": metadata,
                }
            )
        return vectors
    
    async def process_user_conversations(
        self,
        user_id: str,
        json_content: str,
        *,
        competency_definitions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        사용자 대화기록 전체 처리 파이프라인
        
        Args:
            user_id: 사용자 ID
            json_content: ChatGPT 대화 JSON 내용
            
        Returns:
            처리 결과 정보
            
        Raises:
            RAGEmbeddingServiceError: 처리 실패 시
        """
        try:
            logger.info(f"사용자 대화기록 처리 시작 - 사용자 ID: {user_id}")

            conversations = await self.extract_user_conversations(json_content)

            if not conversations:
                logger.warning(f"사용자 {user_id}의 대화 데이터가 없습니다.")
                return {
                    "success": True,
                    "message": "처리할 대화 데이터가 없습니다.",
                    "conversations_count": 0,
                    "embeddings_count": 0
                }

            embeddings = await self.generate_embeddings(
                conversations,
                competencies=competency_definitions,
            )

            formatted = self._format_pinecone_vectors(embeddings)
            namespace = user_id
            self.pinecone_service.upsert_vectors(formatted, namespace=namespace)

            logger.info(f"사용자 대화기록 처리 완료 - 사용자 ID: {user_id}")
            unique_tags = sorted({tag for item in embeddings for tag in item.get("competency_tags", []) if tag})
            return {
                "success": True,
                "message": "대화기록 처리 및 임베딩 저장이 완료되었습니다.",
                "conversations_count": len(conversations),
                "embeddings_count": len(embeddings),
                "unique_competency_tags": unique_tags,
            }

        except Exception as exc:
            logger.error(f"사용자 대화기록 처리 실패: {exc}")
            raise RAGEmbeddingServiceError(f"대화기록 처리 실패: {exc}") from exc
    
    async def get_user_embeddings_info(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 임베딩 정보 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            임베딩 정보
        """
        try:
            embeddings_count = 0
            try:
                embeddings_count = await self.pinecone_service.namespace_vector_count(user_id)
            except Exception as exc:
                logger.warning("Pinecone 벡터 수 확인 실패: %s", exc)

            return {
                "user_id": user_id,
                "embeddings_count": embeddings_count,
                "embedding_model": self.embedding_model,
                "has_embeddings": embeddings_count > 0,
            }

        except Exception as exc:
            logger.error(f"사용자 임베딩 정보 조회 실패: {exc}")
            return {
                "user_id": user_id,
                "embeddings_count": 0,
                "embedding_model": self.embedding_model,
                "has_embeddings": False,
                "error": str(exc),
            }

    async def _tag_embeddings(
        self,
        *,
        embedding_data: List[Dict[str, Any]],
        competency_definitions: List[Dict[str, Any]],
        similarity_threshold: float = 0.25,
        max_tags: int = 3,
    ) -> List[Dict[str, Any]]:
        """임베딩 벡터를 직군 핵심역량과 매칭해 competency_tags를 채운다."""

        if not competency_definitions:
            return embedding_data

        competency_payloads: List[str] = []
        competency_ids: List[str] = []
        for competency in competency_definitions:
            comp_id = competency.get("id")
            name = competency.get("name", "")
            description = competency.get("description", "")
            if comp_id:
                competency_ids.append(comp_id)
                competency_payloads.append(f"{name}: {description}".strip())

        if not competency_ids:
            return embedding_data

        competency_embeddings = await self.gemini_service.generate_embeddings_batch(competency_payloads)
        competency_vectors = [np.asarray(vec, dtype=float) for vec in competency_embeddings]

        normalized_competency_vectors: List[np.ndarray] = []
        for vector in competency_vectors:
            norm = np.linalg.norm(vector)
            if norm == 0 or not np.isfinite(norm):
                normalized_competency_vectors.append(vector)
            else:
                normalized_competency_vectors.append(vector / norm)

        for item in embedding_data:
            raw_embedding = np.asarray(item.get("embedding", []), dtype=float)
            norm = np.linalg.norm(raw_embedding)
            if norm == 0 or not np.isfinite(norm):
                item["competency_tags"] = []
                continue

            normalized_embedding = raw_embedding / norm
            scores: List[tuple[str, float]] = []
            for comp_id, comp_vector in zip(competency_ids, normalized_competency_vectors):
                comp_norm = np.linalg.norm(comp_vector)
                if comp_norm == 0 or not np.isfinite(comp_norm):
                    continue
                similarity = float(np.clip(np.dot(normalized_embedding, comp_vector / comp_norm), -1.0, 1.0))
                scores.append((comp_id, similarity))

            scores.sort(key=lambda entry: entry[1], reverse=True)

            selected_tags: List[str] = [
                comp_id for comp_id, score in scores
                if score >= similarity_threshold
            ][:max_tags]

            if not selected_tags and scores:
                selected_tags = [scores[0][0]]

            item["competency_tags"] = selected_tags

        return embedding_data


# 전역 인스턴스 (싱글톤 패턴)
_embedding_service_instance: Optional[RAGEmbeddingService] = None


def get_embedding_service() -> RAGEmbeddingService:
    """
    임베딩 서비스 인스턴스를 반환합니다 (싱글톤).
    
    Returns:
        RAGEmbeddingService 인스턴스
    """
    global _embedding_service_instance
    
    if _embedding_service_instance is None:
        _embedding_service_instance = RAGEmbeddingService()
        logger.info("임베딩 서비스 싱글톤 인스턴스 생성")
    
    return _embedding_service_instance
