"""Gemini API 연동 서비스 모듈."""

from __future__ import annotations

import logging
import os
from typing import Iterable, List, Optional

import google.generativeai as genai
from asgiref.sync import sync_to_async
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


class GeminiServiceError(RuntimeError):
    """Gemini 연동 과정에서 발생한 예외."""


class GeminiService:
    """Gemini 텍스트/임베딩 API 연동 서비스."""

    def __init__(self) -> None:
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise GeminiServiceError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

        genai.configure(api_key=api_key)

        self.text_model: str = os.getenv("GEMINI_TEXT_MODEL", "gemini-1.5-pro")
        self.embedding_model: str = os.getenv(
            "GEMINI_EMBEDDING_MODEL",
            "text-embedding-004",
        )

        self._generative_model = genai.GenerativeModel(self.text_model)

    async def generate_structured_response(
        self,
        prompt: str,
        *,
        response_format: str = "text",
    ) -> str:
        """프롬프트를 Gemini 모델에 전달해 응답을 반환한다."""

        if not prompt:
            raise ValueError("prompt 값이 비어 있습니다.")

        def _call_model() -> str:
            try:
                result = self._generative_model.generate_content(prompt)
            except Exception as exc:  # pragma: no cover - 외부 API 오류 래핑
                logger.error("Gemini 텍스트 생성 실패: %s", exc)
                raise GeminiServiceError(f"Gemini 텍스트 생성 실패: {exc}") from exc

            text = getattr(result, "text", None)
            if not text:
                # 후보 응답 중 첫 번째 텍스트를 추출
                for candidate in getattr(result, "candidates", []) or []:
                    for part in getattr(candidate, "content", {}).get("parts", []):
                        maybe_text = getattr(part, "text", None)
                        if maybe_text:
                            return maybe_text
                logger.warning("Gemini 응답에서 텍스트를 찾지 못했습니다. 원본 응답을 문자열로 변환합니다.")
                return str(result)

            return text

        response = await sync_to_async(_call_model, thread_sensitive=True)()

        if response_format == "json":
            return response
        return response

    async def generate_embeddings_batch(
        self,
        texts: Iterable[str],
        *,
        task_type: str = "retrieval_document",
    ) -> List[List[float]]:
        """여러 텍스트에 대한 임베딩 벡터를 생성한다."""

        payload = [text for text in texts if text and text.strip()]
        if not payload:
            return []

        async def _embed(text: str) -> Optional[List[float]]:
            def _call_embed() -> Optional[List[float]]:
                try:
                    response = genai.embed_content(
                        model=self.embedding_model,
                        content=text,
                        task_type=task_type,
                    )
                except Exception as exc:  # pragma: no cover - 외부 API 오류 래핑
                    logger.error("Gemini 임베딩 생성 실패: %s", exc)
                    raise GeminiServiceError(f"Gemini 임베딩 생성 실패: {exc}") from exc

                embedding = response.get("embedding") if isinstance(response, dict) else None
                if embedding is None:
                    logger.warning("Gemini 임베딩 응답에 embedding 필드가 없습니다.")
                return embedding

            return await sync_to_async(_call_embed, thread_sensitive=True)()

        embeddings: List[List[float]] = []
        for text in payload:
            vector = await _embed(text)
            if vector:
                embeddings.append(vector)

        return embeddings


_gemini_service_instance: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Gemini 서비스 싱글턴 인스턴스를 반환한다."""

    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
        logger.info("Gemini 서비스 인스턴스 생성")
    return _gemini_service_instance


