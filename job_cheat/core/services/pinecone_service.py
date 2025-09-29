"""Pinecone 벡터 스토어 연동 서비스."""

from __future__ import annotations

import os
from typing import Iterable, List, Optional

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec


class PineconeServiceError(RuntimeError):
    """Pinecone 연동 과정에서 발생한 예외."""


class PineconeService:
    """Pinecone 벡터 인덱스를 관리하는 서비스."""

    def __init__(self) -> None:
        load_dotenv()
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise PineconeServiceError("PINECONE_API_KEY 환경 변수가 설정되지 않았습니다.")

        self.index_name = os.getenv("PINECONE_INDEX_NAME", "job-cheat-vectors")
        dimension = int(os.getenv("PINECONE_INDEX_DIMENSION", "1024"))
        cloud_provider = os.getenv("PINECONE_CLOUD_PROVIDER", "aws").lower()
        region = os.getenv("PINECONE_REGION", "us-east-1")

        self.client = Pinecone(api_key=api_key)

        existing_indexes = []
        for index_info in self.client.list_indexes():
            name = getattr(index_info, "name", None)
            existing_indexes.append(name or index_info)

        if self.index_name not in existing_indexes:
            spec = ServerlessSpec(cloud=cloud_provider, region=region)
            self.client.create_index(
                name=self.index_name,
                dimension=dimension,
                metric="cosine",
                spec=spec,
            )

        self.index = self.client.Index(self.index_name)

    def upsert_vectors(
        self,
        vectors: Iterable[dict],
        *,
        namespace: Optional[str] = None,
    ) -> None:
        formatted = []
        for item in vectors:
            formatted.append(
                (
                    item["id"],
                    item["values"],
                    item.get("metadata"),
                )
            )
        if not formatted:
            return
        self.index.upsert(vectors=formatted, namespace=namespace)

    def query_similar(
        self,
        vector: List[float],
        *,
        namespace: Optional[str] = None,
        top_k: int = 5,
        include_metadata: bool = True,
        filter: Optional[dict] = None,
    ) -> dict:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 Pinecone 유사도 검색 시작")
        logger.info(f"   📊 벡터 차원: {len(vector) if vector else 0}")
        logger.info(f"   📋 namespace: {namespace}")
        logger.info(f"   📋 top_k: {top_k}")
        logger.info(f"   📋 include_metadata: {include_metadata}")
        logger.info(f"   📋 filter: {filter}")
        
        try:
            logger.info(f"📤 Pinecone index.query 호출 시작")
            logger.info(f"   🔗 index.query 호출")
            
            result = self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=include_metadata,
                namespace=namespace,
                filter=filter,
            )
            
            logger.info(f"📥 Pinecone 검색 완료")
            logger.info(f"   📊 결과 타입: {type(result)}")
            logger.info(f"   📊 매치 수: {len(result.get('matches', [])) if result and 'matches' in result else 0}")
            logger.info(f"   📊 검색 결과: {result}")
            
            return result
            
        except Exception as exc:
            logger.error(f"❌ Pinecone query 실패: {exc}")
            logger.error(f"   🔍 오류 타입: {type(exc).__name__}")
            raise PineconeServiceError(f"Pinecone query 실패: {exc}") from exc

    def delete_namespace(self, namespace: str) -> None:
        self.index.delete(delete_all=True, namespace=namespace)

    def namespace_vector_count(self, namespace: str) -> int:
        stats = self.index.describe_index_stats()
        namespaces = stats.get("namespaces", {})
        namespace_stats = namespaces.get(namespace, {})
        return namespace_stats.get("vector_count", 0)


_pinecone_service_instance: Optional[PineconeService] = None


def get_pinecone_service() -> PineconeService:
    global _pinecone_service_instance
    if _pinecone_service_instance is None:
        _pinecone_service_instance = PineconeService()
    return _pinecone_service_instance


