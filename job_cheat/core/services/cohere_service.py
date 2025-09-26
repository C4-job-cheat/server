"""
Cohere 임베딩 서비스를 래핑한 모듈.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

import os
import cohere
from asgiref.sync import sync_to_async
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class CohereServiceError(RuntimeError):
    """Cohere 임베딩 서비스 예외."""


class CohereService:
    """Cohere 임베딩 API 연동 서비스."""

    def __init__(self) -> None:
        load_dotenv()
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            raise CohereServiceError("COHERE_API_KEY 환경 변수가 설정되지 않았습니다.")

        try:
            self._client = cohere.Client(api_key)
        except Exception as exc:  # pragma: no cover - SDK 초기화 예외 래핑
            logger.exception("Cohere 클라이언트 초기화 실패")
            raise CohereServiceError(f"Cohere 클라이언트 초기화 실패: {exc}") from exc

        self._default_model = os.getenv("COHERE_EMBED_MODEL", "embed-multilingual-v3.0")

    async def embed_texts(
        self,
        texts: Iterable[str],
        *,
        model: Optional[str] = None,
        input_type: str = "search_document",
    ) -> List[List[float]]:
        """텍스트 리스트를 Cohere 임베딩으로 변환한다."""

        text_list = [text for text in texts if text and text.strip()]
        if not text_list:
            return []

        chosen_model = model or self._default_model

        try:
            response = await sync_to_async(self._client.embed)(
                texts=text_list,
                model=chosen_model,
                input_type=input_type,
            )
        except Exception as exc:
            logger.exception("Cohere 임베딩 생성 실패")
            raise CohereServiceError(f"임베딩 생성 실패: {exc}") from exc

        embeddings = getattr(response, "embeddings", None)
        if embeddings is None:
            raise CohereServiceError("Cohere 응답에 embeddings 필드가 없습니다.")

        return embeddings


_cohere_service_instance: Optional[CohereService] = None


def get_cohere_service() -> CohereService:
    """Cohere 서비스 싱글톤 인스턴스를 반환한다."""

    global _cohere_service_instance
    if _cohere_service_instance is None:
        _cohere_service_instance = CohereService()
        logger.info("Cohere 임베딩 서비스 인스턴스 생성")
    return _cohere_service_instance

