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


class PersonaJsonDownloadError(RuntimeError):
    """페르소나 JSON 파일 다운로드 중 발생한 예외."""


class PersonaFileListError(RuntimeError):
    """페르소나 파일 목록 조회 중 발생한 예외."""


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
    # 요구사항에 따라 userid 기반으로 HTML 파일 저장 (document_id 사용)
    blob_path = f"users/{user_id}/html/{document_id}.html"
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
    # 요구사항에 따라 userid.json으로 저장 (document_id 사용)
    blob_path = f"users/{user_id}/json/{document_id}.json"
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
        # 예외를 발생시키지 않고 False를 반환하여 프로세스를 계속 진행
        return False


def upload_interview_audio(
    *,
    user_id: str,
    interview_session_id: str,
    question_id: str,
    audio_data: bytes,
    bucket=None,
    cache_control: str = "public, max-age=3600",
) -> Dict[str, Any]:
    """면접 질문 TTS 오디오 파일을 Storage에 업로드하고 메타데이터를 반환한다."""

    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not interview_session_id:
        raise ValueError("interview_session_id 값이 필요합니다.")
    if not question_id:
        raise ValueError("question_id 값이 필요합니다.")
    if not audio_data:
        raise ValueError("audio_data 값이 필요합니다.")

    bucket_instance = _resolve_bucket(bucket=bucket)
    # 면접 오디오 파일 저장 경로: users/{user_id}/interviews/{session_id}/questions/{question_id}.mp3
    blob_path = f"users/{user_id}/interviews/{interview_session_id}/questions/{question_id}.mp3"
    blob = bucket_instance.blob(blob_path)
    blob.cache_control = cache_control

    try:
        blob.upload_from_string(audio_data, content_type="audio/mpeg")
        logger.info(f"면접 오디오 파일 Firebase Storage 업로드 성공: {blob_path}")
    except (gcloud_exceptions.GoogleCloudError, Exception) as exc:
        logger.exception("면접 오디오 파일 Firebase Storage 업로드 실패", extra={
            "user_id": user_id, 
            "interview_session_id": interview_session_id, 
            "question_id": question_id
        })
        raise PersonaHtmlUploadError(str(exc)) from exc

    # Firebase Storage 공개 URL 생성
    public_url = blob.public_url
    
    # 결제 계정 문제로 인한 임시 해결책: 로컬 파일 서빙
    # TODO: Firebase 결제 계정 문제 해결 후 제거
    try:
        # 로컬에 오디오 파일 저장
        import os
        from django.conf import settings
        
        # 로컬 오디오 파일 저장 경로 (staticfiles 디렉토리 사용)
        local_audio_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'audio', 'interviews')
        os.makedirs(local_audio_dir, exist_ok=True)
        
        local_file_path = os.path.join(local_audio_dir, f"{question_id}.mp3")
        with open(local_file_path, 'wb') as f:
            f.write(audio_data)
        
        # 로컬 서빙 URL 생성 (ngrok URL 포함)
        from django.conf import settings
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        local_url = f"{base_url}/static/audio/interviews/{question_id}.mp3"
        logger.info(f"로컬 오디오 파일 저장: {local_file_path}")
        logger.info(f"로컬 서빙 URL: {local_url}")
        
        # 로컬 URL을 우선 사용 (Firebase URL은 백업으로 유지)
        return {
            "path": blob_path,
            "content_type": "audio/mpeg",
            "size": len(audio_data),
            "url": local_url,  # 로컬 URL 사용
            "firebase_url": public_url,  # Firebase URL 백업
        }
        
    except Exception as e:
        logger.warning(f"로컬 파일 저장 실패, Firebase URL 사용: {e}")
        return {
            "path": blob_path,
            "content_type": "audio/mpeg",
            "size": len(audio_data),
            "url": public_url,
        }


def download_persona_json(
    *,
    user_id: str,
    document_id: str,
    bucket=None,
) -> Dict[str, Any]:
    """Storage에서 JSON 파일을 다운로드하고 내용을 반환한다."""
    
    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not document_id:
        raise ValueError("document_id 값이 필요합니다.")
    
    bucket_instance = _resolve_bucket(bucket=bucket)
    blob_path = f"users/{user_id}/json/{document_id}.json"
    blob = bucket_instance.blob(blob_path)
    
    try:
        # 파일 존재 여부 확인
        if not blob.exists():
            logger.warning(f"JSON 파일을 찾을 수 없음: {blob_path}")
            return {
                "exists": False,
                "path": blob_path,
                "content": None,
                "size": 0,
                "content_type": None,
            }
        
        # 파일 내용 다운로드
        json_content = blob.download_as_text()
        
        logger.info(f"JSON 파일 다운로드 성공: {blob_path}")
        
        return {
            "exists": True,
            "path": blob_path,
            "content": json_content,
            "size": blob.size,
            "content_type": blob.content_type,
        }
        
    except (gcloud_exceptions.GoogleCloudError, Exception) as exc:
        logger.exception("Firebase Storage JSON 다운로드 실패", extra={"user_id": user_id, "document_id": document_id})
        raise PersonaJsonDownloadError(str(exc)) from exc


def list_user_persona_files(
    *,
    user_id: str,
    bucket=None,
) -> Dict[str, Any]:
    """사용자의 모든 페르소나 파일 목록을 반환한다."""
    
    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    
    bucket_instance = _resolve_bucket(bucket=bucket)
    
    try:
        # HTML 파일 목록
        html_prefix = f"users/{user_id}/html/"
        html_blobs = list(bucket_instance.list_blobs(prefix=html_prefix))
        
        # JSON 파일 목록
        json_prefix = f"users/{user_id}/json/"
        json_blobs = list(bucket_instance.list_blobs(prefix=json_prefix))
        
        html_files = []
        for blob in html_blobs:
            html_files.append({
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created,
                "updated": blob.updated,
            })
        
        json_files = []
        for blob in json_blobs:
            json_files.append({
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created,
                "updated": blob.updated,
            })
        
        logger.info(f"사용자 파일 목록 조회 성공: user_id={user_id}, HTML={len(html_files)}개, JSON={len(json_files)}개")
        
        return {
            "user_id": user_id,
            "html_files": html_files,
            "json_files": json_files,
            "total_html_files": len(html_files),
            "total_json_files": len(json_files),
        }
        
    except (gcloud_exceptions.GoogleCloudError, Exception) as exc:
        logger.exception("Firebase Storage 파일 목록 조회 실패", extra={"user_id": user_id})
        raise PersonaFileListError(str(exc)) from exc

