"""
Google Cloud Text-to-Speech API 연동 서비스
"""

import os
import logging
import tempfile
from typing import Optional
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

    async def synthesize_speech_to_file(
        self,
        text: str,
        output_path: str,
        language_code: str = "ko-KR",
        voice_name: str = "ko-KR-Wavenet-A",
        ssml_gender: str = "NEUTRAL"
    ) -> str:
        """
        텍스트를 음성으로 변환하여 파일로 저장합니다.
        
        Args:
            text: 변환할 텍스트
            output_path: 출력 파일 경로
            language_code: 언어 코드
            voice_name: 음성 이름
            ssml_gender: 음성 성별
            
        Returns:
            str: 저장된 파일 경로
        """
        try:
            # 음성 변환
            audio_data = await self.synthesize_speech(
                text=text,
                language_code=language_code,
                voice_name=voice_name,
                ssml_gender=ssml_gender
            )
            
            # 파일로 저장
            with open(output_path, "wb") as out_file:
                out_file.write(audio_data)
            
            logger.info(f"📁 TTS 음성 파일 저장 완료: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ TTS 음성 파일 저장 실패: {e}")
            raise TTSServiceError(f"TTS 음성 파일 저장 실패: {e}") from e

    async def synthesize_speech_to_temp_file(
        self,
        text: str,
        language_code: str = "ko-KR",
        voice_name: str = "ko-KR-Wavenet-A",
        ssml_gender: str = "NEUTRAL"
    ) -> str:
        """
        텍스트를 음성으로 변환하여 임시 파일로 저장합니다.
        
        Args:
            text: 변환할 텍스트
            language_code: 언어 코드
            voice_name: 음성 이름
            ssml_gender: 음성 성별
            
        Returns:
            str: 임시 파일 경로
        """
        try:
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            # 음성 변환 및 저장
            await self.synthesize_speech_to_file(
                text=text,
                output_path=temp_file_path,
                language_code=language_code,
                voice_name=voice_name,
                ssml_gender=ssml_gender
            )
            
            return temp_file_path
            
        except Exception as e:
            logger.error(f"❌ TTS 임시 파일 생성 실패: {e}")
            raise TTSServiceError(f"TTS 임시 파일 생성 실패: {e}") from e


# 전역 인스턴스
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """TTS 서비스 인스턴스를 반환합니다."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
