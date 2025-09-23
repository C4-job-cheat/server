from __future__ import annotations

import logging
from typing import Any, Dict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from firebase_admin import storage
from google.cloud import exceptions as gcloud_exceptions

logger = logging.getLogger(__name__)


class PersonaHtmlUploadError(RuntimeError):
    """페르소나 HTML 파일 업로드 중 발생한 예외."""


def _resolve_bucket(bucket=None):
    """Firebase Storage 버킷 인스턴스를 가져온다."""

    if bucket is not None:
        return bucket

    bucket_name = getattr(settings, "FIREBASE_STORAGE_BUCKET", None)
    try:
        if bucket_name:
            return storage.bucket(name=bucket_name)
        return storage.bucket()
    except Exception as exc:  # pragma: no cover - 환경 설정 오류 보호
        raise ImproperlyConfigured("Firebase Storage 버킷을 초기화할 수 없습니다.") from exc


def upload_persona_html(
    *,
    user_id: str,
    document_id: str,
    file_obj,
    bucket=None,
    cache_control: str = "public, max-age=3600",
) -> Dict[str, Any]:
    """HTML 파일을 Storage에 업로드하고 메타데이터를 반환한다."""

    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not document_id:
        raise ValueError("document_id 값이 필요합니다.")

    bucket_instance = _resolve_bucket(bucket=bucket)
    blob_path = f"personas/{user_id}/inputs/{document_id}/{user_id}.html"
    blob = bucket_instance.blob(blob_path)
    blob.cache_control = cache_control

    content_type = getattr(file_obj, "content_type", None) or "text/html"

    file_obj.seek(0)

    try:
        blob.upload_from_file(file_obj, content_type=content_type)
    except (gcloud_exceptions.GoogleCloudError, Exception) as exc:
        logger.exception("Firebase Storage 업로드 실패", extra={"user_id": user_id, "document_id": document_id})
        raise PersonaHtmlUploadError(str(exc)) from exc

    size = getattr(file_obj, "size", None)
    # 업로드 후 재사용을 위해 포인터를 다시 원위치로 돌려둔다.
    try:
        file_obj.seek(0)
    except Exception:  # pragma: no cover - 일부 파일 객체는 seek 미지원
        pass

    return {
        "path": blob_path,
        "content_type": content_type,
        "size": size if size is not None else blob.size,
    }

