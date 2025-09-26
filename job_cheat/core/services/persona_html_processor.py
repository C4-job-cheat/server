"""
페르소나 HTML 파일을 처리하여 JSON으로 변환하고 Storage에 저장하는 서비스 모듈
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from core.services.firebase_storage import (
    PersonaFileDeleteError,
    PersonaJsonUploadError,
    delete_persona_file,
    upload_persona_json,
)
from core.services.chatgpt_converter import ChatGPTConversionError, convert_chatgpt_html_to_json

logger = logging.getLogger(__name__)


class PersonaHtmlProcessingError(RuntimeError):
    """페르소나 HTML 처리 중 발생한 예외."""


def process_persona_html_to_json(
    *,
    user_id: str,
    document_id: str,
    html_content: str,
    html_file_path: str,
) -> Dict[str, Any]:
    """
    HTML 내용을 JSON으로 변환하고 Storage에 저장한 후 원본 HTML 파일을 삭제한다.
    
    Args:
        user_id: 사용자 ID
        document_id: 문서 ID
        html_content: HTML 내용
        html_file_path: 원본 HTML 파일 경로 (삭제용)
    
    Returns:
        JSON 파일의 메타데이터 (path, content_type, size)
    
    Raises:
        PersonaHtmlProcessingError: 처리 중 오류 발생 시
    """
    
    if not user_id:
        raise ValueError("user_id 값이 필요합니다.")
    if not document_id:
        raise ValueError("document_id 값이 필요합니다.")
    if not html_content:
        raise ValueError("html_content 값이 필요합니다.")
    if not html_file_path:
        raise ValueError("html_file_path 값이 필요합니다.")
    
    try:
        # 1. HTML을 JSON으로 변환 (ChatGPT 변환기 사용)
        logger.info(f"HTML을 JSON으로 변환 시작: user_id={user_id}, document_id={document_id}")
        json_content = convert_chatgpt_html_to_json(html_content, verbose=True)
        
        # 2. JSON을 Storage에 업로드
        logger.info(f"JSON 파일 업로드 시작: user_id={user_id}, document_id={document_id}")
        json_upload_result = upload_persona_json(
            user_id=user_id,
            document_id=document_id,
            json_content=json_content,
        )
        
        # 3. 원본 HTML 파일 삭제
        logger.info(f"원본 HTML 파일 삭제 시작: {html_file_path}")
        delete_success = delete_persona_file(file_path=html_file_path)
        
        if not delete_success:
            logger.warning(f"HTML 파일 삭제 실패 (파일이 존재하지 않거나 오류 발생): {html_file_path}")
        
        logger.info(f"HTML 처리 완료: user_id={user_id}, document_id={document_id}")
        
        # JSON 내용에서 대화 수 추출
        json_data = json.loads(json_content)
        conversations_count = json_data.get("total_conversations", 0)
        
        return {
            "json_file_path": json_upload_result["path"],
            "json_content_type": json_upload_result["content_type"],
            "json_file_size": json_upload_result["size"],
            "html_file_deleted": delete_success,
            "conversations_count": conversations_count,
        }
        
    except ChatGPTConversionError as exc:
        logger.error(f"HTML 변환 실패: {exc}")
        raise PersonaHtmlProcessingError(f"HTML 변환 실패: {exc}") from exc
        
    except PersonaJsonUploadError as exc:
        logger.error(f"JSON 업로드 실패: {exc}")
        raise PersonaHtmlProcessingError(f"JSON 업로드 실패: {exc}") from exc
        
    except Exception as exc:
        logger.error(f"HTML 처리 중 예상치 못한 오류 발생: {exc}")
        raise PersonaHtmlProcessingError(f"HTML 처리 실패: {exc}") from exc
