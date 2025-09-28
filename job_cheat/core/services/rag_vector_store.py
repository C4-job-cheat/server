"""
RAG 벡터 스토어 서비스 구현.
사용자별 대화 임베딩을 Firestore에 저장하고 벡터 유사도를 계산합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from django.conf import settings
from firebase_admin import firestore

from .cohere_service import get_cohere_service

logger = logging.getLogger(__name__)


class RAGVectorStoreError(RuntimeError):
    """RAG 벡터 스토어 처리 중 발생한 예외."""


class RAGVectorStore:
    """사용자별 벡터 데이터베이스를 관리하는 서비스."""

    def __init__(self) -> None:
        """Firestore 컬렉션 핸들을 초기화합니다."""
        self.db = getattr(settings, "FIREBASE_DB", None)
        if not self.db:
            raise RAGVectorStoreError("Firebase Firestore 클라이언트가 초기화되지 않았습니다.")

        self.collection_name = getattr(settings, "RAG_VECTOR_COLLECTION", "user_vector_embeddings")
        self._cohere = get_cohere_service()
        logger.info("RAG 벡터 스토어 서비스 초기화 완료")

    def _collection(self):
        return self.db.collection(self.collection_name)

    async def create_user_vector_db(self, user_id: str) -> str:
        """사용자 전용 벡터 DB 문서를 생성하거나 이미 존재하면 그대로 반환합니다."""
        if not user_id:
            raise ValueError("user_id가 비어 있습니다.")

        try:
            doc_ref = self._collection().document(user_id)
            if doc_ref.get().exists:
                logger.debug("기존 사용자 벡터 DB가 발견되어 재사용합니다: %s", user_id)
                return user_id

            initial_data = {
                "embeddings": [],
                "metadata": {
                    "total_conversations": 0,
                    "last_updated": firestore.SERVER_TIMESTAMP,
                    "embedding_model": self._cohere._default_model,
                    "created_at": firestore.SERVER_TIMESTAMP,
                },
            }
            doc_ref.set(initial_data, merge=True)
            logger.info("사용자 벡터 DB 생성 완료: %s", user_id)
            return user_id
        except Exception as exc:  # pragma: no cover - Firestore 오류 래핑
            logger.error("사용자 벡터 DB 생성 실패: %s", exc)
            raise RAGVectorStoreError(f"벡터 DB 생성 실패: {exc}") from exc

    async def store_embeddings(self, user_id: str, embeddings: List[Dict[str, Any]]) -> bool:
        """임베딩 벡터 목록을 Firestore에 추가합니다."""
        if not user_id:
            raise ValueError("user_id가 비어 있습니다.")
        if not embeddings:
            logger.warning("저장할 임베딩이 없어 요청을 무시했습니다.")
            return True

        doc_ref = self._collection().document(user_id)

        try:
            def _tx(transaction):
                snapshot = doc_ref.get(transaction=transaction)
                existing = []
                if snapshot.exists:
                    existing = snapshot.to_dict().get("embeddings", [])

                updated_embeddings = existing + embeddings
                transaction.set(
                    doc_ref,
                    {
                        "embeddings": updated_embeddings,
                        "metadata": {
                            "total_conversations": len(updated_embeddings),
                            "last_updated": firestore.SERVER_TIMESTAMP,
                            "embedding_model": self._cohere._default_model,
                        },
                    },
                    merge=True,
                )

            transaction = self.db.transaction()
            transaction.call(_tx)
            logger.info("임베딩 저장 완료: user_id=%s, count=%d", user_id, len(embeddings))
            return True
        except Exception as exc:  # pragma: no cover - Firestore 오류 래핑
            logger.error("임베딩 저장 실패: %s", exc)
            raise RAGVectorStoreError(f"임베딩 저장 실패: {exc}") from exc

    async def search_similar_conversations(
        self,
        user_id: str,
        query: str,
        competency_id: str | None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """쿼리 문장과 유사한 대화를 코사인 유사도로 검색합니다."""
        if not user_id:
            raise ValueError("user_id가 비어 있습니다.")
        if not query:
            raise ValueError("query가 비어 있습니다.")

        doc_ref = self._collection().document(user_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            logger.warning("사용자 벡터 DB가 존재하지 않습니다: %s", user_id)
            return []

        data = snapshot.to_dict() or {}
        all_embeddings: List[Dict[str, Any]] = data.get("embeddings", [])
        if not all_embeddings:
            logger.warning("사용자 임베딩이 없습니다: %s", user_id)
            return []

        if competency_id:
            filtered = [item for item in all_embeddings if competency_id in item.get("competency_tags", [])]
        else:
            filtered = list(all_embeddings)

        if not filtered:
            logger.info("태그로 필터링된 결과가 없어 전체 임베딩을 사용합니다: %s", competency_id)
            filtered = list(all_embeddings)

        try:
            query_embeddings = await self._cohere.embed_texts(
                [query],
                model=self._cohere._default_model,
                input_type="search_query",
            )
        except Exception as exc:  # pragma: no cover - Gemini 오류 래핑
            logger.error("쿼리 임베딩 생성 실패: %s", exc)
            raise RAGVectorStoreError(f"쿼리 임베딩 생성 실패: {exc}") from exc

        if not query_embeddings:
            logger.warning("쿼리 임베딩 결과가 비어 있어 검색을 중단했습니다.")
            return []

        query_vec = np.asarray(query_embeddings[0], dtype=float)
        query_norm = np.linalg.norm(query_vec)
        if not np.isfinite(query_norm) or query_norm == 0:
            logger.warning("쿼리 임베딩 노름이 0이어서 검색을 중단했습니다.")
            return []

        scored_results: List[Dict[str, Any]] = []
        for item in filtered:
            vector = np.asarray(item.get("embedding", []), dtype=float)
            if vector.shape != query_vec.shape:
                logger.debug("임베딩 차원이 일치하지 않아 건너뜁니다: %s", item.get("conversation_id"))
                continue
            denom = np.linalg.norm(vector)
            if denom == 0 or not np.isfinite(denom):
                logger.debug("임베딩 노름이 0이어서 건너뜁니다: %s", item.get("conversation_id"))
                continue
            score = float(np.dot(query_vec, vector) / (query_norm * denom))
            scored_results.append(
                {
                    "conversation_id": item.get("conversation_id"),
                    "content": item.get("content", ""),
                    "score": score,
                    "competency_tags": item.get("competency_tags", []),
                    "created_at": item.get("created_at"),
                }
            )

        scored_results.sort(key=lambda entry: entry["score"], reverse=True)
        top_results = scored_results[: max(top_k, 0)]
        logger.info("유사 대화 검색 완료: user_id=%s, returned=%d", user_id, len(top_results))
        return top_results

    async def get_user_embeddings_count(self, user_id: str) -> int:
        """사용자 임베딩 개수를 반환합니다."""
        if not user_id:
            raise ValueError("user_id가 비어 있습니다.")

        snapshot = self._collection().document(user_id).get()
        if not snapshot.exists:
            return 0
        data = snapshot.to_dict() or {}
        return len(data.get("embeddings", []))

    async def delete_user_vector_db(self, user_id: str) -> bool:
        """사용자 벡터 DB 문서를 삭제합니다."""
        if not user_id:
            raise ValueError("user_id가 비어 있습니다.")

        try:
            self._collection().document(user_id).delete()
            logger.info("사용자 벡터 DB 삭제 완료: %s", user_id)
            return True
        except Exception as exc:  # pragma: no cover - Firestore 오류 래핑
            logger.error("사용자 벡터 DB 삭제 실패: %s", exc)
            return False


_vector_store_instance: Optional[RAGVectorStore] = None


def get_vector_store() -> RAGVectorStore:
    """RAG 벡터 스토어 서비스 싱글턴을 반환합니다."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = RAGVectorStore()
        logger.info("RAG 벡터 스토어 서비스 인스턴스 생성")
    return _vector_store_instance
