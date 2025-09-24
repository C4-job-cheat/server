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


class PersonaJsonUploadError(RuntimeError):
    """페르소나 JSON 파일 업로드 중 발생한 예외."""


class PersonaFileDeleteError(RuntimeError):
    """페르소나 파일 삭제 중 발생한 예외."""


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
    # 요구사항에 따라 userid 기반으로 HTML 파일 저장
    blob_path = f"users/{user_id}/html/{user_id}.html"
    blob = bucket_instance.blob(blob_path)
    blob.cache_control = cache_control

    content_type = getattr(file_obj, "content_type", None) or "text/html"

    # 파일 포인터를 처음으로 이동 (업로드 전)
    file_obj.seek(0)

    try:
        blob.upload_from_file(file_obj, content_type=content_type)
        logger.info(f"Firebase Storage 업로드 성공: {blob_path}")
    except (gcloud_exceptions.GoogleCloudError, Exception) as exc:
        logger.exception("Firebase Storage 업로드 실패", extra={"user_id": user_id, "document_id": document_id})
        raise PersonaHtmlUploadError(str(exc)) from exc

    size = getattr(file_obj, "size", None)
    # 업로드 후 파일 포인터는 그대로 두고 호출자가 필요에 따라 관리하도록 함

    return {
        "path": blob_path,
        "content_type": content_type,
        "size": size if size is not None else blob.size,
    }


def upload_persona_json(
    *,
    user_id: str,
    document_id: str,
    json_content: str,
    bucket=None,
    cache_control: str = "public, max-age=3600",
) -> Dict[str, Any]:
    """JSON 문자열을 Storage에 업로드하고 메타데이터를 반환한다."""

    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not document_id:
        raise ValueError("document_id 값이 필요합니다.")
    if not json_content:
        raise ValueError("json_content 값이 필요합니다.")

    bucket_instance = _resolve_bucket(bucket=bucket)
    # 요구사항에 따라 userid.json으로 저장
    blob_path = f"users/{user_id}/json/{user_id}.json"
    blob = bucket_instance.blob(blob_path)
    blob.cache_control = cache_control

    try:
        blob.upload_from_string(json_content, content_type="application/json")
    except (gcloud_exceptions.GoogleCloudError, Exception) as exc:
        logger.exception("Firebase Storage JSON 업로드 실패", extra={"user_id": user_id, "document_id": document_id})
        raise PersonaJsonUploadError(str(exc)) from exc

    return {
        "path": blob_path,
        "content_type": "application/json",
        "size": len(json_content.encode('utf-8')),
    }


def delete_persona_file(
    *,
    file_path: str,
    bucket=None,
) -> bool:
    """Storage에서 파일을 삭제한다."""

    if not file_path:
        raise ValueError("file_path 값이 필요합니다.")

    bucket_instance = _resolve_bucket(bucket=bucket)
    blob = bucket_instance.blob(file_path)

    try:
        blob.delete()
        logger.info(f"파일 삭제 완료: {file_path}")
        return True
    except gcloud_exceptions.NotFound:
        logger.warning(f"삭제할 파일을 찾을 수 없음: {file_path}")
        return False
    except (gcloud_exceptions.GoogleCloudError, Exception) as exc:
        logger.exception("Firebase Storage 파일 삭제 실패", extra={"file_path": file_path})
        raise PersonaFileDeleteError(str(exc)) from exc

