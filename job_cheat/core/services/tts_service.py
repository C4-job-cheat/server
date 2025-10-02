"""
Google Cloud Text-to-Speech API 연동 서비스
"""

import os
import logging
import tempfile
from typing import Optional, Dict, Any
from google.cloud import texttospeech
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class TTSServiceError(RuntimeError):
    """TTS 연동 과정에서 발생한 예외."""


class TTSService:
    """Google Cloud Text-to-Speech API 연동 서비스."""

    def __init__(self) -> None:
        load_dotenv()

        # Google Cloud 인증 정보 확인 (Firebase와 동일한 서비스 계정 사용)
        firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
        if not firebase_credentials:
            raise TTSServiceError("FIREBASE_CREDENTIALS 환경 변수가 설정되지 않았습니다.")

        # Google Cloud TTS는 GOOGLE_APPLICATION_CREDENTIALS 환경 변수를 사용
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = firebase_credentials
        logger.info(f"Google Cloud 인증 설정: {firebase_credentials}")

        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("Google Cloud TTS 클라이언트 초기화 완료")
        except Exception as e:
            raise TTSServiceError(f"Google Cloud TTS 클라이언트 초기화 실패: {e}") from e

    async def synthesize_speech(
        self,
        text: str,
        language_code: str = "ko-KR",
        voice_name: str = "ko-KR-Wavenet-A",
        ssml_gender: str = "NEUTRAL"
    ) -> bytes:
        """
        텍스트를 음성으로 변환합니다.
        
        Args:
            text: 변환할 텍스트
            language_code: 언어 코드 (기본값: ko-KR)
            voice_name: 음성 이름 (기본값: ko-KR-Wavenet-A)
            ssml_gender: 음성 성별 (기본값: NEUTRAL)
            
        Returns:
            bytes: 변환된 오디오 데이터
        """
        try:
            logger.info(f"🎤 TTS 음성 변환 시작")
            logger.info(f"   📝 변환할 텍스트: {text[:100] + '...' if len(text) > 100 else text}")
            logger.info(f"   🌐 언어: {language_code}")
            logger.info(f"   🎵 음성: {voice_name}")
            
            # 입력 텍스트 설정
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # 음성 설정
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
                ssml_gender=getattr(texttospeech.SsmlVoiceGender, ssml_gender)
            )
            
            # 오디오 설정 (MP3 형식)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            # TTS 요청 실행
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            audio_data = response.audio_content
            logger.info(f"✅ TTS 음성 변환 완료: {len(audio_data)} bytes")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ TTS 음성 변환 실패: {e}")
            raise TTSServiceError(f"TTS 음성 변환 실패: {e}") from e

    async def synthesize_speech_to_firebase(
        self,
        text: str,
        user_id: str,
        interview_session_id: str,
        question_id: str,
        language_code: str = "ko-KR",
        voice_name: str = "ko-KR-Wavenet-A",
        ssml_gender: str = "NEUTRAL"
    ) -> Dict[str, Any]:
        """
        텍스트를 음성으로 변환하여 Firebase Storage에 직접 업로드합니다.
        
        Args:
            text: 변환할 텍스트
            user_id: 사용자 ID
            interview_session_id: 면접 세션 ID
            question_id: 질문 ID
            language_code: 언어 코드
            voice_name: 음성 이름
            ssml_gender: 음성 성별
            
        Returns:
            Dict[str, Any]: 업로드 결과 (path, url, size 등)
        """
        try:
            logger.info(f"🎤 TTS 음성 변환 및 Firebase Storage 업로드 시작")
            logger.info(f"   📝 변환할 텍스트: {text[:100] + '...' if len(text) > 100 else text}")
            logger.info(f"   👤 사용자 ID: {user_id}")
            logger.info(f"   🆔 세션 ID: {interview_session_id}")
            logger.info(f"   🆔 질문 ID: {question_id}")
            
            # 음성 변환
            audio_data = await self.synthesize_speech(
                text=text,
                language_code=language_code,
                voice_name=voice_name,
                ssml_gender=ssml_gender
            )
            
            logger.info(f"✅ TTS 음성 변환 완료: {len(audio_data)} bytes")
            
            # Firebase Storage에 직접 업로드
            from .firebase_storage import upload_interview_audio
            upload_result = upload_interview_audio(
                user_id=user_id,
                interview_session_id=interview_session_id,
                question_id=question_id,
                audio_data=audio_data
            )
            
            logger.info(f"✅ Firebase Storage 업로드 완료")
            logger.info(f"   📁 저장 경로: {upload_result['path']}")
            logger.info(f"   🔗 URL: {upload_result['url']}")
            logger.info(f"   📏 파일 크기: {upload_result['size']} bytes")
            
            return upload_result
            
        except Exception as e:
            logger.error(f"❌ TTS Firebase Storage 업로드 실패: {e}")
            raise TTSServiceError(f"TTS Firebase Storage 업로드 실패: {e}") from e


# 전역 인스턴스
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """TTS 서비스 인스턴스를 반환합니다."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
