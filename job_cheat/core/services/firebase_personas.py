from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from firebase_admin import firestore
from google.api_core import exceptions as google_exceptions


logger = logging.getLogger(__name__)

USER_COLLECTION = "users"
PERSONA_SUBCOLLECTION = "personas"


class PersonaInputSaveError(RuntimeError):
    """페르소나 입력을 Firestore에 저장하는 과정에서 발생한 예외."""


class PersonaNotFoundError(RuntimeError):
    """요청한 페르소나 문서를 찾지 못했을 때 발생하는 예외."""


def _resolve_db(db=None):
    """Firestore 클라이언트가 설정되었는지 확인합니다."""

    resolved = db or getattr(settings, "FIREBASE_DB", None)
    if resolved is None:
        raise ImproperlyConfigured("Firestore 클라이언트를 찾을 수 없습니다. FIREBASE_DB 설정을 확인하세요.")
    return resolved


def _persona_doc_ref(user_id: str, persona_id: str, *, db=None):
    client = _resolve_db(db=db)
    return (
        client.collection(USER_COLLECTION)
        .document(user_id)
        .collection(PERSONA_SUBCOLLECTION)
        .document(persona_id)
    )


def save_user_persona_input(
    *,
    user_id: str,
    payload: Dict[str, Any],
    document_id: str | None = None,
    db=None,
) -> Dict[str, Any]:
    """사용자의 페르소나 입력을 Firestore에 저장하고 최종 데이터를 반환합니다."""

    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not isinstance(payload, dict):
        raise ValueError("payload는 딕셔너리여야 합니다.")

    client = _resolve_db(db=db)
    resolved_document_id = document_id or str(uuid4())
    doc_ref = (
        client.collection(USER_COLLECTION)
        .document(user_id)
        .collection(PERSONA_SUBCOLLECTION)
        .document(resolved_document_id)
    )

    firestore_payload = {
        **payload,
        "user_id": user_id,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    logger.info(
        "페르소나 입력 저장 시도",
        extra={"user_id": user_id, "document_id": resolved_document_id},
    )

    try:
        doc_ref.set(firestore_payload)
        snapshot = doc_ref.get()
    except google_exceptions.GoogleAPICallError as exc:
        logger.exception("Firestore API 호출 도중 오류", extra={"user_id": user_id})
        raise PersonaInputSaveError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - 예외 상황 로깅
        logger.exception("Firestore 저장 중 알 수 없는 오류", extra={"user_id": user_id})
        raise PersonaInputSaveError(str(exc)) from exc

    data = snapshot.to_dict() if snapshot.exists else firestore_payload
    data["id"] = resolved_document_id
    return data


def get_persona_document(*, user_id: str, persona_id: str, db=None) -> Dict[str, Any]:
    """사용자의 특정 페르소나 문서를 조회합니다."""
    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not persona_id:
        raise ValueError("persona_id 값이 필요합니다.")

    doc_ref = _persona_doc_ref(user_id, persona_id, db=db)
    snapshot = doc_ref.get()
    if not snapshot.exists:
        logger.warning("요청한 페르소나 문서를 찾지 못했습니다: user_id=%s, persona_id=%s", user_id, persona_id)
        raise PersonaNotFoundError("해당 페르소나 문서를 찾을 수 없습니다.")

    data = snapshot.to_dict() or {}
    data["id"] = persona_id
    return data


def update_persona_document(
    *,
    user_id: str,
    persona_id: str,
    payload: Dict[str, Any],
    db=None,
    merge: bool = True,
) -> Dict[str, Any]:
    """페르소나 문서의 일부 필드를 업데이트하고 최신 데이터를 반환합니다."""
    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not persona_id:
        raise ValueError("persona_id 값이 필요합니다.")
    if not isinstance(payload, dict):
        raise ValueError("payload는 딕셔너리여야 합니다.")

    doc_ref = _persona_doc_ref(user_id, persona_id, db=db)

    try:
        doc_ref.set(payload, merge=merge)
        snapshot = doc_ref.get()
    except google_exceptions.NotFound as exc:
        logger.warning("업데이트 대상 페르소나가 존재하지 않습니다: user_id=%s, persona_id=%s", user_id, persona_id)
        raise PersonaNotFoundError("해당 페르소나 문서를 찾을 수 없습니다.") from exc
    except google_exceptions.GoogleAPICallError as exc:
        logger.exception("Firestore API 호출 도중 오류", extra={"user_id": user_id, "persona_id": persona_id})
        raise PersonaInputSaveError(str(exc)) from exc

    data = snapshot.to_dict() if snapshot.exists else payload
    data["id"] = persona_id
    return data


def mark_competency_evaluation(
    *,
    user_id: str,
    persona_id: str,
    competency_scores: Dict[str, int],
    evaluation_version: str,
    evaluated_at: datetime | None = None,
    metadata: Optional[Dict[str, Any]] = None,
    db=None,
) -> Dict[str, Any]:
    """핵심역량 평가 결과를 페르소나 문서에 기록합니다."""
    from datetime import datetime as _dt

    evaluated_at = evaluated_at or _dt.utcnow()
    evaluation_payload: Dict[str, Any] = {
        "scores": competency_scores,
        "evaluated_at": evaluated_at,
        "version": evaluation_version,
    }
    if metadata:
        evaluation_payload.update(metadata)

    payload = {
        "competency_evaluation": evaluation_payload,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    return update_persona_document(
        user_id=user_id,
        persona_id=persona_id,
        payload=payload,
        db=db,
    )
