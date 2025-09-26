"""
페르소나 임베딩 파이프라인을 비동기적으로 실행하는 백그라운드 작업 모듈.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from threading import Thread
from typing import Any, Dict, List, Optional

from firebase_admin import firestore

from .firebase_personas import update_persona_document
from .firebase_storage import (
    PersonaJsonDownloadError,
    download_persona_json,
)
from .rag_embedding_service import (
    RAGEmbeddingServiceError,
    get_embedding_service,
)

logger = logging.getLogger(__name__)


def enqueue_embedding_job(
    *,
    user_id: str,
    persona_id: str,
    competency_definitions: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """임베딩 백그라운드 작업을 큐에 등록한다."""

    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not persona_id:
        raise ValueError("persona_id 값이 필요합니다.")

    thread = Thread(
        target=_run_embedding_job,
        args=(user_id, persona_id, competency_definitions or []),
        daemon=True,
    )
    thread.start()


def _run_embedding_job(
    user_id: str,
    persona_id: str,
    competency_definitions: List[Dict[str, Any]],
) -> None:
    """새로운 이벤트 루프에서 임베딩 작업을 실행한다."""

    try:
        asyncio.run(
            _async_embedding_job(
                user_id=user_id,
                persona_id=persona_id,
                competency_definitions=competency_definitions,
            )
        )
    except Exception as exc:  # pragma: no cover - 최상위 예외 로깅
        logger.exception("임베딩 백그라운드 작업이 실패했습니다: %s", exc)
        try:
            update_persona_document(
                user_id=user_id,
                persona_id=persona_id,
                payload={
                    "embedding_status": "failed",
                    "embedding_error": str(exc),
                    "embedding_completed_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
            )
        except Exception:
            logger.exception("임베딩 실패 상태를 Firestore에 기록하지 못했습니다.")


async def _async_embedding_job(
    *,
    user_id: str,
    persona_id: str,
    competency_definitions: List[Dict[str, Any]],
) -> None:
    """실제 임베딩 파이프라인을 실행하고 Firestore 문서를 갱신한다."""

    start_timestamp = datetime.utcnow()

    try:
        update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload={
                "embedding_status": "running",
                "embedding_started_at": start_timestamp,
                "embedding_error": None,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )
    except Exception:
        logger.exception("임베딩 시작 상태를 기록하는 데 실패했습니다.")

    try:
        download_result = download_persona_json(
            user_id=user_id,
            document_id=persona_id,
        )
    except PersonaJsonDownloadError as exc:
        logger.exception("임베딩 작업용 JSON 다운로드 실패")
        _mark_embedding_failed(user_id, persona_id, f"json_download_failed: {exc}")
        return

    if not download_result.get("exists") or not download_result.get("content"):
        logger.warning("임베딩 작업용 JSON 콘텐츠가 없습니다: user_id=%s, persona_id=%s", user_id, persona_id)
        _mark_embedding_failed(user_id, persona_id, "json_content_missing")
        return

    embedding_service = get_embedding_service()
    try:
        result = await embedding_service.process_user_conversations(
            user_id=user_id,
            json_content=download_result["content"],
            competency_definitions=competency_definitions,
        )
        embeddings_info = await embedding_service.get_user_embeddings_info(user_id)
    except RAGEmbeddingServiceError as exc:
        logger.exception("임베딩 파이프라인 실행 실패")
        _mark_embedding_failed(user_id, persona_id, f"embedding_failed: {exc}")
        return
    except Exception as exc:  # pragma: no cover - 예기치 못한 예외 로깅
        logger.exception("임베딩 파이프라인 중 알 수 없는 오류")
        _mark_embedding_failed(user_id, persona_id, f"unknown_embedding_error: {exc}")
        return

    unique_tags = result.get("unique_competency_tags", [])

    try:
        update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload={
                "embedding_status": "completed" if result.get("success") else "skipped",
                "embedding_message": result.get("message", ""),
                "embeddings_count": result.get("embeddings_count", 0),
                "embedding_model": embeddings_info.get("embedding_model") if embeddings_info else None,
                "has_embeddings": embeddings_info.get("has_embeddings", False) if embeddings_info else False,
                "vectorized_competency_tags": unique_tags,
                "embedding_error": None,
                "embedding_completed_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )
    except Exception:
        logger.exception("임베딩 완료 상태를 Firestore에 기록하지 못했습니다.")


def _mark_embedding_failed(user_id: str, persona_id: str, reason: str) -> None:
    """임베딩 실패 상태를 Firestore 문서에 반영한다."""

    try:
        update_persona_document(
            user_id=user_id,
            persona_id=persona_id,
            payload={
                "embedding_status": "failed",
                "embedding_error": reason,
                "embedding_completed_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )
    except Exception:  # pragma: no cover - 실패 상태 기록 실패시 로그만 남김
        logger.exception("임베딩 실패 상태 기록에 실패했습니다: %s", reason)

