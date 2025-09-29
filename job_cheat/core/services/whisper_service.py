"""OpenAI Whisper STT 서비스 모듈."""

import logging
import os
import tempfile
from typing import Optional

import openai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class WhisperServiceError(RuntimeError):
    """Whisper 연동 과정에서 발생한 예외."""


class WhisperService:
    """OpenAI Whisper STT API 연동 서비스."""

    def __init__(self) -> None:
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise WhisperServiceError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

        self.client = openai.OpenAI(api_key=api_key)

    async def transcribe_audio(
        self,
        audio_file_path: str,
        language: str = "ko"
    ) -> str:
        """음성 파일을 텍스트로 변환합니다."""
        try:
            logger.info(f"음성 파일 변환 시작: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            
            text = transcript.text.strip()
            logger.info(f"음성 파일 변환 완료: {len(text)}자")
            logger.info(f"📝 변환된 텍스트 내용: {text[:200] + '...' if len(text) > 200 else text}")
            return text
            
        except Exception as e:
            logger.error(f"음성 파일 변환 실패: {e}")
            raise WhisperServiceError(f"음성 파일 변환 실패: {e}") from e

    async def transcribe_webm_file(
        self,
        webm_file,
        language: str = "ko"
    ) -> str:
        """WebM 파일을 텍스트로 변환합니다."""
        try:
            logger.info(f"🎤 WebM 파일 STT 변환 시작")
            logger.info(f"   📁 파일명: {getattr(webm_file, 'name', 'Unknown')}")
            logger.info(f"   📏 파일 크기: {getattr(webm_file, 'size', 'Unknown')} bytes")
            
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                for chunk in webm_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            logger.info(f"📁 임시 파일 생성 완료: {temp_file_path}")
            
            try:
                # 음성 변환
                text = await self.transcribe_audio(temp_file_path, language)
                logger.info(f"✅ WebM 파일 STT 변환 완료")
                return text
            finally:
                # 임시 파일 삭제
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logger.info(f"🗑️ 임시 파일 삭제 완료: {temp_file_path}")
                    
        except Exception as e:
            logger.error(f"WebM 파일 변환 실패: {e}")
            raise WhisperServiceError(f"WebM 파일 변환 실패: {e}") from e


# 전역 인스턴스
_whisper_service: Optional[WhisperService] = None


def get_whisper_service() -> WhisperService:
    """Whisper 서비스 인스턴스를 반환합니다."""
    global _whisper_service
    if _whisper_service is None:
        _whisper_service = WhisperService()
    return _whisper_service
