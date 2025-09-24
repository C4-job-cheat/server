from __future__ import annotations

import logging
from typing import Any, Dict
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


def _resolve_db(db=None):
    """Firestore 클라이언트를 확보하지 못하면 구성 오류를 발생시킨다."""

    resolved = db or getattr(settings, "FIREBASE_DB", None)
    if resolved is None:
        raise ImproperlyConfigured("Firestore 클라이언트를 찾을 수 없습니다. FIREBASE_DB 설정을 확인하세요.")
    return resolved


def save_user_persona_input(
    *,
    user_id: str,
    payload: Dict[str, Any],
    document_id: str | None = None,
    db=None,
) -> Dict[str, Any]:
    """사용자별 페르소나 입력을 Firestore에 저장하고 생성된 문서를 반환한다."""

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
        logger.exception("Firestore API 호출 중 오류", extra={"user_id": user_id})
        raise PersonaInputSaveError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - 예기치 못한 오류 방지
        logger.exception("Firestore 저장 중 알 수 없는 오류", extra={"user_id": user_id})
        raise PersonaInputSaveError(str(exc)) from exc

    data = snapshot.to_dict() if snapshot.exists else firestore_payload
    data["id"] = resolved_document_id
    return data
