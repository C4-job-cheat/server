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

        logger.info(f"🔗 Cohere 임베딩 서비스 시작")
        logger.info(f"   📝 입력 텍스트 수: {len(list(texts)) if texts else 0}")
        logger.info(f"   📋 모델: {model or self._default_model}")
        logger.info(f"   📋 입력 타입: {input_type}")

        text_list = [text for text in texts if text and text.strip()]
        logger.info(f"   📊 필터링된 텍스트 수: {len(text_list)}")
        
        if not text_list:
            logger.warning(f"⚠️ 빈 텍스트 리스트")
            return []

        chosen_model = model or self._default_model
        logger.info(f"   🎯 사용할 모델: {chosen_model}")

        try:
            logger.info(f"📤 Cohere API 호출 시작")
            logger.info(f"   🔗 _client.embed 호출")
            logger.info(f"   📋 texts: {len(text_list)}개")
            logger.info(f"   📋 model: {chosen_model}")
            logger.info(f"   📋 input_type: {input_type}")
            
            # sync_to_async 대신 직접 호출 (Gemini API와 같은 방식)
            logger.info(f"🔄 Cohere 클라이언트 직접 호출 시작")
            response = self._client.embed(
                texts=text_list,
                model=chosen_model,
                input_type=input_type,
            )
            logger.info(f"✅ Cohere 클라이언트 직접 호출 완료")
            
            logger.info(f"📥 Cohere API 응답 수신")
            logger.info(f"   📊 응답 타입: {type(response)}")
            
        except Exception as exc:
            logger.error(f"❌ Cohere 임베딩 생성 실패: {exc}")
            logger.error(f"   🔍 오류 타입: {type(exc).__name__}")
            logger.exception("Cohere 임베딩 생성 실패")
            raise CohereServiceError(f"임베딩 생성 실패: {exc}") from exc

        embeddings = getattr(response, "embeddings", None)
        logger.info(f"🔍 응답에서 embeddings 추출")
        logger.info(f"   📊 embeddings 존재 여부: {embeddings is not None}")
        
        if embeddings is None:
            logger.error(f"❌ Cohere 응답에 embeddings 필드가 없음")
            raise CohereServiceError("Cohere 응답에 embeddings 필드가 없습니다.")

        logger.info(f"✅ Cohere 임베딩 생성 완료")
        logger.info(f"   📊 임베딩 수: {len(embeddings) if embeddings else 0}")
        logger.info(f"   📊 임베딩 차원: {len(embeddings[0]) if embeddings and embeddings[0] else 0}")

        return embeddings


_cohere_service_instance: Optional[CohereService] = None


def get_cohere_service() -> CohereService:
    """Cohere 서비스 싱글톤 인스턴스를 반환한다."""

    global _cohere_service_instance
    if _cohere_service_instance is None:
        _cohere_service_instance = CohereService()
        logger.info("Cohere 임베딩 서비스 인스턴스 생성")
    return _cohere_service_instance

