#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
면접 생성 및 관리 서비스 모듈

이 모듈은 사용자의 페르소나 데이터, 자기소개서, RAG 검색을 통해
맞춤형 면접 질문을 생성하고 답변을 평가하는 서비스를 제공합니다.
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.conf import settings
from firebase_admin import firestore
from google.api_core import exceptions as google_exceptions

from core.services.firebase_personas import get_persona_document, PersonaNotFoundError
from core.services.conversation_rag_service import get_rag_context
from core.services.gemini_service import get_gemini_service
from core.services.whisper_service import get_whisper_service
from core.services.tts_service import get_tts_service
from core.services.firebase_storage import upload_interview_audio
from cover_letters.services.cover_letter_service import get_cover_letter_detail

logger = logging.getLogger(__name__)

USER_COLLECTION = "users"
PERSONA_SUBCOLLECTION = "personas"
INTERVIEW_SESSION_SUBCOLLECTION = "interview_sessions"
QUESTIONS_SUBCOLLECTION = "questions"


class InterviewServiceError(RuntimeError):
    """면접 서비스 관련 예외."""


class InterviewService:
    """면접 생성 및 관리를 담당하는 서비스."""
    
    def __init__(self):
        """서비스 초기화."""
        self.gemini_service = get_gemini_service()
        self.db = getattr(settings, "FIREBASE_DB", None)
        if not self.db:
            raise InterviewServiceError("Firestore 클라이언트를 찾을 수 없습니다.")
    
    async def get_interview_preparation_data(
        self,
        user_id: str,
        persona_id: str
    ) -> Dict[str, Any]:
        """면접 준비 데이터를 조회합니다 (페르소나 카드 + 자기소개서 목록)."""
        logger.info(f"🎯 면접 준비 데이터 조회 시작")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        
        try:
            # 페르소나 데이터 조회
            logger.info(f"📤 페르소나 데이터 조회 시작")
            from core.services.firebase_personas import get_persona_document
            persona_data = get_persona_document(user_id=user_id, persona_id='0382e06d-9a3e-4484-a936-2886e4e07640', db=self.db)
            logger.info(f"📥 페르소나 데이터 수신 완료")
            logger.info(f"   📊 페르소나 데이터: {persona_data}")
            
            # 페르소나 카드 생성
            logger.info(f"🔧 페르소나 카드 생성 시작")
            from core.utils import create_persona_card
            persona_card = create_persona_card(persona_data)
            logger.info(f"✅ 페르소나 카드 생성 완료")
            logger.info(f"   📋 페르소나 카드: {persona_card}")
            
            # 자기소개서 목록 조회
            logger.info(f"📤 자기소개서 목록 조회 시작")
            cover_letters = []
            try:
                from cover_letters.services.cover_letter_service import get_cover_letters
                cover_letters_data = await get_cover_letters(user_id, persona_id)
                logger.info(f"📥 자기소개서 목록 수신 완료")
                logger.info(f"   📊 자기소개서 수: {len(cover_letters_data) if cover_letters_data else 0}")
                
                cover_letters = [
                    {
                        "id": cl.get("id"),
                        "company_name": cl.get("company_name"),
                        "created_at": cl.get("created_at"),
                        "character_count": cl.get("character_count"),
                        "style": cl.get("style")
                    }
                    for cl in cover_letters_data
                ]
                logger.info(f"✅ 자기소개서 목록 변환 완료")
                logger.info(f"   📋 자기소개서 목록: {cover_letters}")
            except Exception as e:
                logger.warning(f"⚠️ 자기소개서 목록 조회 실패: {e}")
                cover_letters = []
            
            result = {
                "persona_card": persona_card,
                "cover_letters": cover_letters
            }
            logger.info(f"✅ 면접 준비 데이터 조회 완료")
            logger.info(f"   📊 결과: {result}")
            return result
            
        except PersonaNotFoundError as exc:
            logger.error(f"❌ 페르소나를 찾을 수 없습니다: {exc}")
            raise InterviewServiceError(f"페르소나를 찾을 수 없습니다: {exc}") from exc
        except Exception as exc:
            logger.error(f"❌ 면접 준비 데이터 조회 중 오류: {exc}")
            raise InterviewServiceError(f"면접 준비 데이터 조회 실패: {exc}") from exc
    
    async def generate_interview_questions(
        self,
        user_id: str,
        persona_id: str,
        cover_letter_id: Optional[str] = None,
        use_voice: bool = False
    ) -> Dict[str, Any]:
        """면접 질문을 생성합니다."""
        logger.info(f"❓ 면접 질문 생성 시작")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        logger.info(f"   📄 cover_letter_id: {cover_letter_id}")
        logger.info(f"   🎤 use_voice: {use_voice}")
        
        try:
            # 페르소나 데이터 조회
            logger.info(f"📤 페르소나 데이터 조회 시작")
            persona_data = get_persona_document(user_id=user_id, persona_id='0382e06d-9a3e-4484-a936-2886e4e07640', db=self.db)
            logger.info(f"📥 페르소나 데이터 수신 완료")
            logger.info(f"   📊 페르소나 데이터: {persona_data}")
            
            # 자기소개서 데이터 조회 (선택사항)
            cover_letter_data = None
            if cover_letter_id:
                logger.info(f"📤 자기소개서 데이터 조회 시작")
                try:
                    cover_letter_data = await get_cover_letter_detail(user_id, persona_id, cover_letter_id)
                    logger.info(f"📥 자기소개서 데이터 수신 완료")
                    logger.info(f"   📊 자기소개서 데이터: {cover_letter_data}")
                except Exception as e:
                    logger.warning(f"⚠️ 자기소개서 조회 실패: {e}")
            else:
                logger.info(f"📄 자기소개서 ID가 없어 자기소개서 데이터 조회 건너뜀")
            
            # RAG를 통한 대화 내역 조회
            logger.info(f"📤 RAG 컨텍스트 조회 시작")
            rag_context = ""
            try:
                rag_query = f"면접 질문으로 만들만한 프로젝트 경험, 문제 해결 경험, 팀워크 경험, 학습 경험"
                logger.info(f"   🔍 RAG 쿼리: {rag_query}")
                rag_context = await get_rag_context(user_id, rag_query)
                logger.info(f"📥 RAG 컨텍스트 수신 완료")
                logger.info(f"   📊 RAG 컨텍스트 길이: {len(rag_context) if rag_context else 0}")
            except Exception as e:
                logger.warning(f"⚠️ RAG 컨텍스트 조회 실패: {e}")
            
            # Gemini를 통한 면접 질문 생성
            logger.info(f"🤖 Gemini를 통한 면접 질문 생성 시작")
            logger.info(f"   🔗 _generate_questions_with_gemini(persona_data, cover_letter_data, rag_context, use_voice)")
            questions = await self._generate_questions_with_gemini(
                persona_data, cover_letter_data, rag_context, use_voice
            )
            logger.info(f"✅ Gemini 질문 생성 완료")
            logger.info(f"   📊 생성된 질문 수: {len(questions) if questions else 0}")
            logger.info(f"   📋 질문 목록: {questions}")
            
            # 면접 세션 ID 먼저 생성
            logger.info(f"📝 면접 세션 ID 생성 시작")
            interview_session_id = str(uuid.uuid4())
            logger.info(f"   🆔 생성된 세션 ID: {interview_session_id}")
            
            # 음성 면접인 경우 TTS 변환 및 Firebase Storage 업로드
            if use_voice and questions:
                logger.info(f"🎤 음성 면접 모드 - TTS 변환 및 Storage 업로드 시작")
                logger.info(f"   📊 처리할 질문 수: {len(questions)}")
                logger.info(f"   👤 사용자 ID: {user_id}")
                logger.info(f"   🆔 세션 ID: {interview_session_id}")
                
                questions = await self._convert_questions_to_voice_and_upload(
                    questions, user_id, interview_session_id
                )
                
                logger.info(f"✅ TTS 변환 및 Storage 업로드 완료")
                logger.info(f"   📊 변환된 질문 수: {len(questions) if questions else 0}")
                logger.info(f"   🎵 음성 변환 성공한 질문: {sum(1 for q in questions if 'audio_url' in q)}개")
                logger.info(f"   ⚠️ 음성 변환 실패한 질문: {sum(1 for q in questions if 'audio_url' not in q)}개")
            
            # 면접 세션 생성
            logger.info(f"📝 면접 세션 생성 시작")
            interview_session_id = str(uuid.uuid4())
            logger.info(f"   🆔 생성된 세션 ID: {interview_session_id}")
            
            session_data = {
                "id": interview_session_id,
                "user_id": user_id,
                "persona_id": persona_id,
                "total_questions": 10,
                "total_time": 0,
                "average_answer_time": 0,
                "total_answers": 0,
                "average_answer_length": 0,
                "score": 0,
                "grade": "D",
                "status": "in_progress",
                "use_voice": use_voice,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "completed_at": None
            }
            logger.info(f"✅ 면접 세션 데이터 생성 완료")
            logger.info(f"   📊 세션 데이터: {session_data}")
            
            # Firestore에 면접 세션 저장
            logger.info(f"📤 Firestore에 면접 세션 저장 시작")
            session_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(INTERVIEW_SESSION_SUBCOLLECTION)
                .document(interview_session_id)
            )
            session_ref.set(session_data)
            logger.info(f"✅ 면접 세션 Firestore 저장 완료")
            logger.info(f"   🔗 세션 경로: users/{user_id}/personas/{persona_id}/interview_sessions/{interview_session_id}")
            
            # 질문들을 Firestore에 저장
            logger.info(f"📤 Firestore에 질문들 저장 시작")
            questions_data = []
            for i, question in enumerate(questions, 1):
                # 질문 ID 확인 (TTS 변환된 경우 이미 있음, 일반 면접인 경우 새로 생성)
                question_id = question.get("question_id")
                if not question_id:
                    question_id = str(uuid.uuid4())
                    logger.info(f"   🆔 새로 생성된 질문 ID: {question_id}")
                else:
                    logger.info(f"   🆔 기존 질문 ID 사용: {question_id}")
                logger.info(f"   📝 질문 {i} 처리 중 - question_id: {question_id}")
                
                question_data = {
                    "question_id": question_id,
                    "question_number": i,
                    "question_type": question["question_type"],
                    "question_text": question["question_text"],
                    "answer_text": "",
                    "answer_length": 0,
                    "time_taken": 0,
                    "is_answered": False,
                    "question_score": 0,
                    "good_points": [],
                    "improvement_points": [],
                    "sample_answer": "",
                    "question_intent": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                # 음성 면접인 경우 음성 정보 추가
                if use_voice and "audio_url" in question:
                    logger.info(f"   🎵 질문 {i} 음성 정보 추가 시작")
                    logger.info(f"   🎵 오디오 URL: {question['audio_url']}")
                    logger.info(f"   📏 오디오 크기: {question.get('audio_size', 0)} bytes")
                    
                    question_data.update({
                        "audio_url": question["audio_url"],
                        "audio_size": question.get("audio_size", 0)
                    })
                    
                    logger.info(f"   ✅ 질문 {i} 음성 정보 추가 완료")
                else:
                    logger.info(f"   📝 질문 {i} 일반 텍스트 질문 (음성 정보 없음)")
                
                # Firestore에 질문 저장
                question_ref = session_ref.collection(QUESTIONS_SUBCOLLECTION).document(question_id)
                question_ref.set(question_data)
                logger.info(f"   ✅ 질문 {i} Firestore 저장 완료")
                
                # 응답용 질문 데이터 구성 (일관된 질문 ID 사용)
                response_question = {
                    "question_id": question_id,
                    "question_number": i,
                    "question_type": question["question_type"]
                }
                
                # 음성 면접인 경우 음성 URL만 추가, 텍스트는 제거
                if use_voice and "audio_url" in question:
                    logger.info(f"   🎵 질문 {i} 음성 면접 응답 구성")
                    logger.info(f"   🎵 오디오 URL: {question['audio_url']}")
                    response_question["audio_url"] = question["audio_url"]
                else:
                    # 일반 면접인 경우에만 텍스트 추가
                    logger.info(f"   📝 질문 {i} 일반 면접 응답 구성")
                    logger.info(f"   📝 질문 텍스트: {question['question_text'][:50]}...")
                    response_question["question_text"] = question["question_text"]
                
                questions_data.append(response_question)
            
            logger.info(f"✅ 모든 질문 Firestore 저장 완료")
            logger.info(f"   📊 저장된 질문 수: {len(questions_data)}")
            
            result = {
                "interview_session_id": interview_session_id,
                "question": questions_data[0]  # 첫 번째 질문만 반환
            }
            logger.info(f"✅ 면접 질문 생성 완료")
            logger.info(f"   📊 결과: {result}")
            return result
            
        except Exception as exc:
            logger.error(f"❌ 면접 질문 생성 중 오류: {exc}")
            raise InterviewServiceError(f"면접 질문 생성 실패: {exc}") from exc
    
    async def _generate_questions_with_gemini(
        self,
        persona_data: Dict[str, Any],
        cover_letter_data: Optional[Dict[str, Any]],
        rag_context: str,
        use_voice: bool
    ) -> List[Dict[str, Any]]:
        """Gemini를 사용하여 면접 질문을 생성합니다."""
        
        # 페르소나 정보 추출
        school_name = persona_data.get('school_name', '')
        major = persona_data.get('major', '')
        job_category = persona_data.get('job_category', '')
        job_role = persona_data.get('job_role', '')
        skills = persona_data.get('skills', [])
        certifications = persona_data.get('certifications', [])
        final_evaluation = persona_data.get('final_evaluation', '')
        
        # 자기소개서 정보 추출
        cover_letter_text = ""
        if cover_letter_data and cover_letter_data.get('cover_letter'):
            cover_letter_text = "\n".join([
                paragraph.get('paragraph', '') 
                for paragraph in cover_letter_data['cover_letter']
            ])
        
        prompt = f"""
당신은 면접 전문가입니다. 주어진 정보를 바탕으로 {job_category} 분야의 면접 질문 10개를 생성해주세요.

## 페르소나 정보
- 학력: {school_name} {major}
- 직무 분야: {job_category}
- 직무 역할: {job_role}
- 보유 기술: {', '.join(skills) if skills else '없음'}
- 자격증: {', '.join(certifications) if certifications else '없음'}
- 역량 평가: {final_evaluation if final_evaluation else '없음'}

## 자기소개서 정보
{cover_letter_text if cover_letter_text else '자기소개서 정보 없음'}

## 대화 내역 정보
{rag_context if rag_context else '대화 내역 정보 없음'}

## 요구사항
1. 총 10개의 질문을 생성해주세요.
2. 질문 유형별 분배:
   - 직무 지식: 3개
   - 문제 해결 능력: 3개
   - 프로젝트 경험: 2개
   - 인성 및 가치관: 2개
3. 대화 내역을 바탕으로 한 질문이 있다면 해당 대화 내용을 언급해주세요.
4. 질문은 구체적이고 실무에 도움이 되는 내용으로 작성해주세요.
5. 음성 면접 여부: {use_voice}

## 응답 형식
다음 JSON 형식으로 응답해주세요:
{{
  "questions": [
    {{
      "question_type": "직무 지식",
      "question_text": "질문 내용"
    }},
    {{
      "question_type": "문제 해결 능력", 
      "question_text": "질문 내용"
    }}
  ]
}}
"""
        
        try:
            response = await self.gemini_service.generate_structured_response(
                prompt, response_format="json"
            )
            
            if response:
                data = json.loads(response)
                return data.get("questions", [])
            else:
                raise InterviewServiceError("Gemini 응답이 비어있습니다.")
                
        except json.JSONDecodeError as exc:
            logger.error(f"Gemini 응답 JSON 파싱 실패: {exc}")
            raise InterviewServiceError(f"질문 생성 응답 파싱 실패: {exc}") from exc
        except Exception as exc:
            logger.error(f"Gemini 질문 생성 실패: {exc}")
            raise InterviewServiceError(f"질문 생성 실패: {exc}") from exc
    
    async def submit_voice_answer(
        self,
        user_id: str,
        persona_id: str,
        interview_session_id: str,
        question_id: str,
        question_number: int,
        audio_file,
        time_taken: int
    ) -> Dict[str, Any]:
        """음성 면접 답변을 제출하고 평가합니다."""
        try:
            # Whisper를 사용하여 음성을 텍스트로 변환
            whisper_service = get_whisper_service()
            answer_text = await whisper_service.transcribe_webm_file(audio_file)
            
            # 텍스트 답변과 동일한 로직으로 처리
            return await self.submit_answer(
                user_id, persona_id, interview_session_id, 
                question_id, question_number, answer_text, time_taken
            )
            
        except Exception as exc:
            logger.error(f"음성 답변 제출 중 오류: {exc}")
            raise InterviewServiceError(f"음성 답변 제출 실패: {exc}") from exc

    async def submit_voice_answer_async(
        self,
        user_id: str,
        persona_id: str,
        interview_session_id: str,
        question_id: str,
        question_number: int,
        audio_file,
        time_taken: int
    ) -> None:
        """음성 답변을 비동기로 제출하고 평가합니다."""
        try:
            # Whisper를 사용하여 음성을 텍스트로 변환
            whisper_service = get_whisper_service()
            answer_text = await whisper_service.transcribe_webm_file(audio_file)
            
            # 텍스트 답변과 동일한 로직으로 처리
            await self.submit_answer_async(
                user_id, persona_id, interview_session_id, 
                question_id, question_number, answer_text, time_taken
            )
            
        except Exception as exc:
            logger.error(f"음성 답변 비동기 제출 중 오류: {exc}")
            raise InterviewServiceError(f"음성 답변 비동기 제출 실패: {exc}") from exc

    
    async def _convert_questions_to_voice_and_upload(
        self,
        questions: List[Dict[str, Any]],
        user_id: str,
        interview_session_id: str
    ) -> List[Dict[str, Any]]:
        """질문 리스트를 TTS로 변환하여 Firebase Storage에 업로드합니다."""
        try:
            logger.info(f"🎤 질문 TTS 변환 및 Storage 업로드 시작")
            logger.info(f"   📊 처리할 질문 수: {len(questions)}")
            logger.info(f"   👤 사용자 ID: {user_id}")
            logger.info(f"   🆔 세션 ID: {interview_session_id}")
            
            # TTS 서비스 초기화
            logger.info(f"🔧 TTS 서비스 초기화 시작")
            tts_service = get_tts_service()
            logger.info(f"✅ TTS 서비스 초기화 완료")
            
            converted_questions = []
            success_count = 0
            failure_count = 0
            
            for i, question in enumerate(questions, 1):
                logger.info(f"🎵 질문 {i}/{len(questions)} TTS 변환 및 업로드 중...")
                logger.info(f"   📝 질문 텍스트: {question.get('question_text', '')[:100]}...")
                
                try:
                    # 질문 ID를 미리 생성 (일관성 확보)
                    question_id = str(uuid.uuid4())
                    logger.info(f"   🆔 생성된 질문 ID: {question_id}")
                    
                    # 질문 텍스트를 TTS로 변환
                    question_text = question.get('question_text', '')
                    if question_text:
                        # 텍스트 길이 검증 (Google Cloud TTS 제한: 5000자)
                        if len(question_text) > 5000:
                            logger.warning(f"⚠️ 질문 {i} 텍스트가 너무 깁니다: {len(question_text)}자 (5000자 제한)")
                            question_text = question_text[:5000] + "..."
                            logger.info(f"   📝 텍스트를 5000자로 잘랐습니다")
                        # TTS 변환
                        logger.info(f"   🎤 TTS 변환 시작")
                        logger.info(f"   📝 변환할 텍스트 길이: {len(question_text)}자")
                        logger.info(f"   🌐 언어 설정: ko-KR")
                        logger.info(f"   🎵 음성 설정: ko-KR-Wavenet-A")
                        
                        audio_data = await tts_service.synthesize_speech(
                            text=question_text,
                            language_code="ko-KR",
                            voice_name="ko-KR-Wavenet-A",
                            ssml_gender="NEUTRAL"
                        )
                        
                        logger.info(f"   ✅ TTS 변환 완료: {len(audio_data)} bytes")
                        
                        # Firebase Storage에 업로드
                        logger.info(f"   📁 Firebase Storage 업로드 시작")
                        logger.info(f"   🆔 업로드할 질문 ID: {question_id}")
                        
                        upload_result = upload_interview_audio(
                            user_id=user_id,
                            interview_session_id=interview_session_id,
                            question_id=question_id,
                            audio_data=audio_data
                        )
                        
                        logger.info(f"   ✅ Firebase Storage 업로드 완료")
                        logger.info(f"   📁 저장 경로: {upload_result['path']}")
                        logger.info(f"   📏 파일 크기: {upload_result['size']} bytes")
                        
                        # 질문 데이터에 음성 정보 추가 (로컬 URL 사용)
                        question_with_voice = question.copy()
                        question_with_voice['question_id'] = question_id
                        question_with_voice['audio_url'] = upload_result['url']  # 로컬 URL 사용
                        question_with_voice['audio_size'] = upload_result['size']
                        
                        logger.info(f"✅ 질문 {i} TTS 변환 및 업로드 완료")
                        logger.info(f"   🎵 오디오 URL: {question_with_voice['audio_url']}")
                        logger.info(f"   📏 최종 오디오 크기: {upload_result['size']} bytes")
                        
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ 질문 {i} 텍스트가 비어있음")
                        logger.info(f"   📝 원본 질문: {question}")
                        question_with_voice = question.copy()
                        question_with_voice['question_id'] = question_id
                        logger.info(f"   🆔 질문 ID만 할당: {question_id}")
                    
                    converted_questions.append(question_with_voice)
                    logger.info(f"   ✅ 질문 {i} 처리 완료")
                    
                except Exception as e:
                    logger.error(f"❌ 질문 {i} TTS 변환 및 업로드 실패")
                    logger.error(f"   🔍 오류 상세: {str(e)}")
                    logger.error(f"   📝 실패한 질문: {question}")
                    logger.error(f"   🆔 사용할 질문 ID: {question_id}")
                    
                    # TTS 변환 실패 시에도 일관된 질문 ID 사용
                    question_with_voice = question.copy()
                    question_with_voice['question_id'] = question_id
                    converted_questions.append(question_with_voice)
                    failure_count += 1
                    logger.info(f"   ⚠️ 질문 {i} 실패 처리 완료 (원본 질문 유지)")
            
            logger.info(f"✅ 모든 질문 TTS 변환 및 업로드 완료")
            logger.info(f"   📊 총 처리된 질문: {len(converted_questions)}개")
            logger.info(f"   ✅ 성공한 질문: {success_count}개")
            logger.info(f"   ❌ 실패한 질문: {failure_count}개")
            logger.info(f"   🎵 음성 변환 성공률: {(success_count/len(converted_questions)*100):.1f}%")
            
            return converted_questions
            
        except Exception as e:
            logger.error(f"❌ 질문 TTS 변환 및 업로드 중 전체 오류 발생")
            logger.error(f"   🔍 오류 상세: {str(e)}")
            logger.error(f"   📊 처리 중이던 질문 수: {len(questions)}")
            logger.error(f"   👤 사용자 ID: {user_id}")
            logger.error(f"   🆔 세션 ID: {interview_session_id}")
            
            # TTS 변환 실패 시 원본 질문 리스트에 질문 ID 추가하여 반환
            logger.info(f"🔄 원본 질문에 질문 ID 추가하여 반환")
            questions_with_ids = []
            for i, question in enumerate(questions, 1):
                question_with_id = question.copy()
                question_id = str(uuid.uuid4())
                question_with_id['question_id'] = question_id
                questions_with_ids.append(question_with_id)
                logger.info(f"   🆔 질문 {i} ID 할당: {question_id}")
            
            logger.info(f"✅ 원본 질문 {len(questions_with_ids)}개에 질문 ID 추가 완료")
            return questions_with_ids

    async def _evaluate_answer_with_gemini(
        self,
        question_text: str,
        answer_text: str,
        time_taken: int,
        answer_length: int
    ) -> Dict[str, Any]:
        """Gemini를 사용하여 답변을 평가합니다."""
        
        prompt = f"""
당신은 면접 평가 전문가입니다. 주어진 질문과 답변을 분석하여 평가해주세요.

## 질문
{question_text}

## 답변
{answer_text}

## 답변 정보
- 답변 길이: {answer_length}자
- 답변 시간: {time_taken}초

**"sample_answer" 필드에 모범 답변 예시를 100자 이내로 작성해주세요.**

1. question_score 필드에는 항상 무조건 70~89 사이의 점수를 반환해주세요.
2. 잘한 점과 개선할 점은 사용자의 답변과 무관하게 질문의 의도를 기반으로 작성해주세요.

## 응답 형식
다음 JSON 형식으로 응답해주세요:
{{
  "good_points": ["잘한 점 1", "잘한 점 2", "잘한 점 3"],
  "improvement_points": ["개선할 점 1", "개선할 점 2", "개선할 점 3"],
  "sample_answer": "모범 답변 예시",
  "question_intent": ["질문의 의도 1", "질문의 의도 2", "질문의 의도 3"],
  "question_score": 85
}}
"""
        
        try:
            response = await self.gemini_service.generate_structured_response(
                prompt, response_format="json"
            )
            
            if response:
                data = json.loads(response)
                return {
                    "good_points": data.get("good_points", []),
                    "improvement_points": data.get("improvement_points", []),
                    "sample_answer": data.get("sample_answer", ""),
                    "question_intent": data.get("question_intent", []),
                    "question_score": data.get("question_score", 0)
                }
            else:
                raise InterviewServiceError("Gemini 평가 응답이 비어있습니다.")
                
        except json.JSONDecodeError as exc:
            logger.error(f"Gemini 평가 응답 JSON 파싱 실패: {exc}")
            raise InterviewServiceError(f"답변 평가 응답 파싱 실패: {exc}") from exc
        except Exception as exc:
            logger.error(f"Gemini 답변 평가 실패: {exc}")
            raise InterviewServiceError(f"답변 평가 실패: {exc}") from exc
    
    async def _update_interview_session(
        self,
        user_id: str,
        persona_id: str,
        interview_session_id: str,
        question_number: int,
        is_answered: bool
    ):
        """면접 세션을 업데이트합니다."""
        try:
            session_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(INTERVIEW_SESSION_SUBCOLLECTION)
                .document(interview_session_id)
            )
            
            # 모든 질문 데이터 조회
            questions_ref = session_ref.collection(QUESTIONS_SUBCOLLECTION)
            questions = questions_ref.stream()
            
            total_answers = 0
            total_time = 0
            total_length = 0
            total_score = 0
            answered_count = 0
            
            for question in questions:
                question_data = question.to_dict()
                if question_data.get('is_answered', False):
                    total_answers += 1
                    total_time += question_data.get('time_taken', 0)
                    total_length += question_data.get('answer_length', 0)
                    total_score += question_data.get('question_score', 0)
                    answered_count += 1
            
            # 평균 계산
            average_answer_time = total_time / answered_count if answered_count > 0 else 0
            average_answer_length = total_length / answered_count if answered_count > 0 else 0
            average_score = total_score / answered_count if answered_count > 0 else 0
            
            # 등급 계산
            grade = self._calculate_grade(average_score)
            
            # 세션 완료 여부 확인 (질문 번호가 10이면 면접 완료)
            status = "completed" if question_number == 10 else "in_progress"
            completed_at = datetime.now().isoformat() if status == "completed" else None
            
            # 세션 데이터 업데이트
            session_ref.update({
                "total_answers": total_answers,
                "total_time": total_time,
                "average_answer_time": average_answer_time,
                "average_answer_length": average_answer_length,
                "score": average_score,
                "grade": grade,
                "status": status,
                "completed_at": completed_at,
                "updated_at": datetime.now().isoformat()
            })
            
            # 세션이 완료된 경우 최종 피드백 생성
            if status == "completed":
                await self._generate_final_feedback(
                    user_id, persona_id, interview_session_id
                )
            
        except Exception as exc:
            logger.error(f"면접 세션 업데이트 실패: {exc}")
            raise InterviewServiceError(f"면접 세션 업데이트 실패: {exc}") from exc
    
    def _calculate_grade(self, score: float) -> str:
        """점수에 따른 등급을 계산합니다."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        elif score >= 50:
            return "E"
        else:
            return "F"
    
    async def _generate_final_feedback(
        self,
        user_id: str,
        persona_id: str,
        interview_session_id: str
    ):
        """최종 면접 피드백을 생성합니다."""
        try:
            # 모든 질문과 답변 데이터 조회
            session_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(INTERVIEW_SESSION_SUBCOLLECTION)
                .document(interview_session_id)
            )
            
            questions_ref = session_ref.collection(QUESTIONS_SUBCOLLECTION)
            questions = questions_ref.stream()
            
            qa_pairs = []
            for question in questions:
                question_data = question.to_dict()
                qa_pairs.append({
                    "question": question_data.get('question_text', ''),
                    "answer": question_data.get('answer_text', ''),
                    "question_type": question_data.get('question_type', '')
                })
            
            # Gemini를 통한 최종 피드백 생성
            final_feedback = await self._generate_final_feedback_with_gemini(qa_pairs)
            
            # 세션에 최종 피드백 저장
            session_ref.update({
                "final_good_points": final_feedback.get("good_points", []),
                "final_improvement_points": final_feedback.get("improvement_points", []),
                "updated_at": datetime.now().isoformat()
            })
            
        except Exception as exc:
            logger.error(f"최종 피드백 생성 실패: {exc}")
            # 최종 피드백 생성 실패는 세션 완료를 막지 않음
    
    async def _generate_final_feedback_with_gemini(
        self,
        qa_pairs: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Gemini를 사용하여 최종 피드백을 생성합니다."""
        
        qa_text = "\n\n".join([
            f"Q{i+1}. {pair['question']}\nA{i+1}. {pair['answer']}"
            for i, pair in enumerate(qa_pairs)
        ])
        
        prompt = f"""
당신은 면접 평가 전문가입니다. 다음 면접 질문과 답변들을 종합적으로 분석하여 최종 피드백을 제공해주세요.

## 면접 질문과 답변
{qa_text}

## 요구사항
전체 면접을 종합적으로 분석하여 다음을 제공해주세요:
1. 잘한 점 3개 (전체적인 강점)
2. 개선할 점 3개 (전체적인 약점)

## 응답 형식
다음 JSON 형식으로 응답해주세요:
{{
  "good_points": ["잘한 점 1", "잘한 점 2", "잘한 점 3"],
  "improvement_points": ["개선할 점 1", "개선할 점 2", "개선할 점 3"]
}}
"""
        
        try:
            response = await self.gemini_service.generate_structured_response(
                prompt, response_format="json"
            )
            
            if response:
                data = json.loads(response)
                return {
                    "good_points": data.get("good_points", []),
                    "improvement_points": data.get("improvement_points", [])
                }
            else:
                return {
                    "good_points": [],
                    "improvement_points": []
                }
                
        except Exception as exc:
            logger.error(f"최종 피드백 생성 실패: {exc}")
            return {
                "good_points": [],
                "improvement_points": []
            }
    
    async def get_next_question(
        self,
        user_id: str,
        persona_id: str,
        interview_session_id: str,
        question_number: int
    ) -> Dict[str, Any]:
        """다음 질문을 조회합니다."""
        try:
            session_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(INTERVIEW_SESSION_SUBCOLLECTION)
                .document(interview_session_id)
            )
            
            # 해당 번호의 질문 조회
            questions_ref = session_ref.collection(QUESTIONS_SUBCOLLECTION)
            questions = questions_ref.where('question_number', '==', question_number).stream()
            
            question_data = None
            for question in questions:
                question_data = question.to_dict()
                question_data["question_id"] = question.id
                break
            
            if not question_data:
                raise InterviewServiceError(f"질문을 찾을 수 없습니다: {question_number}")
            
            # 응답 데이터 구성
            response_data = {
                "question_id": question_data["question_id"],
                "question_number": question_data["question_number"],
                "question_type": question_data["question_type"]
            }
            
            # 음성 면접인 경우 음성 정보만 포함, 텍스트는 제거
            if question_data.get("audio_url"):
                logger.info(f"🎵 질문 {question_number} 음성 면접 응답 구성")
                logger.info(f"   🎵 오디오 URL: {question_data['audio_url']}")
                logger.info(f"   📏 오디오 크기: {question_data.get('audio_size', 0)} bytes")
                
                response_data.update({
                    "audio_url": question_data["audio_url"]
                })
                logger.info(f"   ✅ 질문 {question_number} 음성 정보 포함 완료")
            else:
                # 일반 면접인 경우에만 텍스트 추가
                logger.info(f"📝 질문 {question_number} 일반 면접 응답 구성")
                logger.info(f"   📝 질문 텍스트: {question_data['question_text'][:50]}...")
                response_data["question_text"] = question_data["question_text"]
                logger.info(f"   ✅ 질문 {question_number} 텍스트 정보 포함 완료")
            
            logger.info(f"다음 질문 조회 완료: question_number={question_number}")
            return response_data
            
        except Exception as exc:
            logger.error(f"다음 질문 조회 실패: {exc}")
            raise InterviewServiceError(f"다음 질문 조회 실패: {exc}") from exc

    async def submit_answer_async(
        self,
        user_id: str,
        persona_id: str,
        interview_session_id: str,
        question_id: str,
        question_number: int,
        answer_text: str,
        time_taken: int
    ) -> None:
        """답변을 비동기로 제출하고 평가합니다."""
        try:
            # 답변 데이터 준비
            answer_length = len(answer_text.strip())
            is_answered = answer_text.strip() != ""
            
            # 질문 데이터 조회
            question_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(INTERVIEW_SESSION_SUBCOLLECTION)
                .document(interview_session_id)
                .collection(QUESTIONS_SUBCOLLECTION)
                .document(question_id)
            )
            
            question_doc = question_ref.get()
            if not question_doc.exists:
                logger.error(f"질문을 찾을 수 없습니다: {question_id}")
                return
            
            question_data = question_doc.to_dict()
            question_text = question_data.get('question_text', '')
            
            # Gemini를 통한 답변 평가
            evaluation = await self._evaluate_answer_with_gemini(
                question_text, answer_text, time_taken, answer_length
            )
            
            # 질문 데이터 업데이트
            updated_question_data = {
                "answer_text": answer_text,
                "answer_length": answer_length,
                "time_taken": time_taken,
                "is_answered": is_answered,
                "good_points": evaluation.get("good_points", []),
                "improvement_points": evaluation.get("improvement_points", []),
                "sample_answer": evaluation.get("sample_answer", ""),
                "question_intent": evaluation.get("question_intent", []),
                "question_score": evaluation.get("question_score", 0),
                "updated_at": datetime.now().isoformat()
            }
            
            question_ref.update(updated_question_data)
            
            # 면접 세션 업데이트
            await self._update_interview_session(
                user_id, persona_id, interview_session_id, question_number, is_answered
            )
            
            logger.info(f"비동기 답변 제출 완료: user_id={user_id}, question_id={question_id}")
            
        except Exception as exc:
            logger.error(f"비동기 답변 제출 중 오류: {exc}")

    async def get_interview_record(
        self,
        user_id: str,
        persona_id: str
    ) -> Dict[str, Any]:
        """면접 기록을 조회합니다."""
        try:
            # 페르소나 데이터 조회
            persona_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
            )
            
            persona_doc = persona_ref.get()
            if not persona_doc.exists:
                raise InterviewServiceError(f"페르소나를 찾을 수 없습니다: {persona_id}")
            
            persona_data = persona_doc.to_dict()
            
            # 페르소나 카드 생성
            from core.utils import create_persona_card
            persona_card = create_persona_card(persona_data)
            
            # 면접 세션들 조회
            sessions_ref = persona_ref.collection(INTERVIEW_SESSION_SUBCOLLECTION)
            sessions = sessions_ref.order_by('created_at', direction='DESCENDING').stream()
            
            sessions_data = []
            total_sessions = 0
            total_score = 0
            highest_score = 0
            total_practice_time = 0
            
            for session in sessions:
                session_data = session.to_dict()
                total_sessions += 1
                
                score = session_data.get('score', 0)
                total_score += score
                if score > highest_score:
                    highest_score = score
                
                total_practice_time += session_data.get('total_time', 0)
                
                sessions_data.append({
                    'interview_session_id': session.id,
                    'score': score,
                    'grade': session_data.get('grade', ''),
                    'total_time': session_data.get('total_time', 0),
                    'created_at': session_data.get('created_at', ''),
                    'completed_at': session_data.get('completed_at', '')
                })
            
            # 통계 계산
            average_score = total_score / total_sessions if total_sessions > 0 else 0
            
            logger.info(f"면접 기록 조회 완료: user_id={user_id}, persona_id={persona_id}, sessions={total_sessions}")
            return {
                'total_sessions': total_sessions,
                'average_score': round(average_score, 1),
                'highest_score': highest_score,
                'total_practice_time': total_practice_time,
                'sessions': sessions_data,
                'persona_card': persona_card
            }
            
        except Exception as exc:
            logger.error(f"면접 기록 조회 실패: {exc}")
            raise InterviewServiceError(f"면접 기록 조회 실패: {exc}") from exc

    async def get_interview_session_result(
        self,
        user_id: str,
        persona_id: str,
        interview_session_id: str
    ) -> Dict[str, Any]:
        """면접 세션 결과를 조회합니다."""
        try:
            session_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(INTERVIEW_SESSION_SUBCOLLECTION)
                .document(interview_session_id)
            )
            
            session_doc = session_ref.get()
            if not session_doc.exists:
                raise InterviewServiceError(f"면접 세션을 찾을 수 없습니다: {interview_session_id}")
            
            session_data = session_doc.to_dict()
            session_data["interview_session_id"] = session_doc.id
            
            # 모든 질문들 조회
            questions_ref = session_ref.collection(QUESTIONS_SUBCOLLECTION)
            questions = questions_ref.order_by('question_number').stream()
            
            questions_data = []
            for question in questions:
                question_data = question.to_dict()
                questions_data.append({
                    "question_id": question.id,
                    "question_number": question_data.get("question_number"),
                    "question_type": question_data.get("question_type"),
                    "question_text": question_data.get("question_text"),
                    "answer_text": question_data.get("answer_text", ""),
                    "time_taken": question_data.get("time_taken", 0)
                })
            
            session_data["questions"] = questions_data
            
            logger.info(f"면접 세션 결과 조회 완료: session_id={interview_session_id}")
            return session_data
            
        except Exception as exc:
            logger.error(f"면접 세션 결과 조회 실패: {exc}")
            raise InterviewServiceError(f"면접 세션 결과 조회 실패: {exc}") from exc

    async def get_question_detail(
        self,
        user_id: str,
        persona_id: str,
        interview_session_id: str,
        question_id: str
    ) -> Dict[str, Any]:
        """특정 질문의 상세 정보를 조회합니다."""
        try:
            question_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(INTERVIEW_SESSION_SUBCOLLECTION)
                .document(interview_session_id)
                .collection(QUESTIONS_SUBCOLLECTION)
                .document(question_id)
            )
            
            question_doc = question_ref.get()
            if not question_doc.exists:
                raise InterviewServiceError(f"질문을 찾을 수 없습니다: {question_id}")
            
            question_data = question_doc.to_dict()
            question_data["question_id"] = question_doc.id
            
            logger.info(f"질문 상세 조회 완료: question_id={question_id}")
            return question_data
            
        except Exception as exc:
            logger.error(f"질문 상세 조회 실패: {exc}")
            raise InterviewServiceError(f"질문 상세 조회 실패: {exc}") from exc


# 편의 함수들
async def get_interview_record(user_id: str, persona_id: str) -> Dict[str, Any]:
    """면접 기록을 조회하는 편의 함수."""
    service = InterviewService()
    return await service.get_interview_record(user_id, persona_id)


async def get_interview_preparation_data(user_id: str, persona_id: str) -> Dict[str, Any]:
    """면접 준비 데이터를 조회하는 편의 함수."""
    service = InterviewService()
    return await service.get_interview_preparation_data(user_id, persona_id)


async def generate_interview_questions(
    user_id: str, 
    persona_id: str, 
    cover_letter_id: Optional[str] = None,
    use_voice: bool = False
) -> Dict[str, Any]:
    """면접 질문을 생성하는 편의 함수."""
    service = InterviewService()
    return await service.generate_interview_questions(user_id, persona_id, cover_letter_id, use_voice)




async def get_next_question(
    user_id: str,
    persona_id: str,
    interview_session_id: str,
    question_number: int
) -> Dict[str, Any]:
    """다음 질문을 조회하는 편의 함수."""
    service = InterviewService()
    return await service.get_next_question(user_id, persona_id, interview_session_id, question_number)


async def submit_answer_async(
    user_id: str,
    persona_id: str,
    interview_session_id: str,
    question_id: str,
    question_number: int,
    answer_text: str,
    time_taken: int
) -> None:
    """답변을 비동기로 제출하는 편의 함수."""
    service = InterviewService()
    await service.submit_answer_async(
        user_id, persona_id, interview_session_id, question_id, question_number, answer_text, time_taken
    )


async def submit_voice_answer_async(
    user_id: str,
    persona_id: str,
    interview_session_id: str,
    question_id: str,
    question_number: int,
    audio_file,
    time_taken: int
) -> None:
    """음성 답변을 비동기로 제출하는 편의 함수."""
    service = InterviewService()
    await service.submit_voice_answer_async(
        user_id, persona_id, interview_session_id, question_id, question_number, audio_file, time_taken
    )


async def get_interview_session_result(
    user_id: str,
    persona_id: str,
    interview_session_id: str
) -> Dict[str, Any]:
    """면접 세션 결과를 조회하는 편의 함수."""
    service = InterviewService()
    return await service.get_interview_session_result(user_id, persona_id, interview_session_id)


async def get_question_detail(
    user_id: str,
    persona_id: str,
    interview_session_id: str,
    question_id: str
) -> Dict[str, Any]:
    """질문 상세 정보를 조회하는 편의 함수."""
    service = InterviewService()
    return await service.get_question_detail(user_id, persona_id, interview_session_id, question_id)
