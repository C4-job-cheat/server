import asyncio
import logging
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    InterviewHistoryRequestSerializer,
    InterviewHistoryResponseSerializer,
    InterviewPreparationRequestSerializer,
    InterviewPreparationResponseSerializer,
    InterviewQuestionGenerationRequestSerializer,
    InterviewQuestionGenerationResponseSerializer,
    AnswerSubmissionRequestSerializer,
    VoiceAnswerSubmissionRequestSerializer,
    NextQuestionResponseSerializer,
    InterviewSessionResultSerializer,
    QuestionDetailResponseSerializer,
)
from .services import (
    get_interview_record,
    get_interview_preparation_data,
    generate_interview_questions,
    submit_answer_async,
    get_interview_session_result,
    get_question_detail,
    get_next_question,
    InterviewServiceError,
)

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health(request):
    """면접 서비스 상태 확인."""
    logger.info("🏥 면접 서비스 헬스체크 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 쿼리 파라미터: {dict(request.GET)}")
    
    response_data = {"ok": True, "feature": "interviews"}
    logger.info(f"✅ 면접 서비스 헬스체크 성공, 응답: {response_data}")
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_interview_history(request):
    """면접 기록을 조회합니다."""
    logger.info("📋 면접 기록 조회 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 쿼리 파라미터: {dict(request.GET)}")
    
    try:
        user = getattr(request, 'user', None)
        logger.info(f"👤 인증된 사용자 확인: {user}")
        logger.info(f"🔑 사용자 UID: {getattr(user, 'uid', None) if user else None}")
        
        if not user or not getattr(user, 'uid', None):
            error_response = {"error": "인증된 사용자만 접근할 수 있습니다."}
            logger.warning(f"❌ 인증 실패")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = user.uid
        persona_id = request.GET.get('persona_id')
        
        logger.info(f"📋 파라미터 추출 완료")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        
        # 파라미터 검증
        logger.info(f"🔍 파라미터 검증 시작")
        
        if not persona_id:
            error_response = {"error": "persona_id 파라미터가 필요합니다."}
            logger.warning(f"❌ persona_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"✅ 파라미터 검증 완료")
        
        # 비동기 함수 호출
        logger.info(f"📤 면접 기록 조회 서비스 호출 시작")
        logger.info(f"   🔗 get_interview_record(user_id={user_id}, persona_id={persona_id})")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_interview_record(user_id, persona_id))
        
        logger.info(f"📥 면접 기록 조회 서비스 응답 수신")
        logger.info(f"   📊 결과: {result}")
        
        response_serializer = InterviewHistoryResponseSerializer(result)
        logger.info(f"✅ 면접 기록 조회 성공, 응답: {response_serializer.data}")
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except InterviewServiceError as exc:
        error_response = {"error": "면접 기록 조회에 실패했습니다.", "details": str(exc)}
        logger.error(f"❌ 면접 기록 조회 서비스 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as exc:
        error_response = {"error": "서버 오류가 발생했습니다."}
        logger.error(f"❌ 면접 기록 조회 중 예상치 못한 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(["GET"])
def get_interview_preparation(request):
    """면접 준비 데이터를 조회합니다."""
    logger.info("🎯 면접 준비 데이터 조회 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 쿼리 파라미터: {dict(request.GET)}")
    
    try:
        user = getattr(request, 'user', None)
        logger.info(f"👤 인증된 사용자 확인: {user}")
        logger.info(f"🔑 사용자 UID: {getattr(user, 'uid', None) if user else None}")
        
        if not user or not getattr(user, 'uid', None):
            error_response = {"error": "인증된 사용자만 접근할 수 있습니다."}
            logger.warning(f"❌ 인증 실패")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = user.uid
        persona_id = request.GET.get('persona_id')
        
        logger.info(f"📋 파라미터 추출 완료")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        
        # 파라미터 검증
        logger.info(f"🔍 파라미터 검증 시작")
        
        if not persona_id:
            error_response = {"error": "persona_id 파라미터가 필요합니다."}
            logger.warning(f"❌ persona_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"✅ 파라미터 검증 완료")
        
        # 비동기 함수 호출
        logger.info(f"📤 면접 준비 데이터 조회 서비스 호출 시작")
        logger.info(f"   🔗 get_interview_preparation_data(user_id={user_id}, persona_id={persona_id})")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_interview_preparation_data(user_id, persona_id))
        
        logger.info(f"📥 면접 준비 데이터 조회 서비스 응답 수신")
        logger.info(f"   📊 결과: {result}")
        
        response_serializer = InterviewPreparationResponseSerializer(result)
        logger.info(f"✅ 면접 준비 데이터 조회 성공, 응답: {response_serializer.data}")
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except InterviewServiceError as exc:
        error_response = {"error": "면접 준비 데이터 조회에 실패했습니다.", "details": str(exc)}
        logger.error(f"❌ 면접 준비 데이터 조회 서비스 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as exc:
        error_response = {"error": "서버 오류가 발생했습니다."}
        logger.error(f"❌ 면접 준비 데이터 조회 중 예상치 못한 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def generate_interview_questions_view(request):
    """면접 질문을 생성합니다."""
    logger.info("❓ 면접 질문 생성 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 요청 데이터: {request.data}")
    
    try:
        user = getattr(request, 'user', None)
        logger.info(f"👤 인증된 사용자 확인: {user}")
        logger.info(f"🔑 사용자 UID: {getattr(user, 'uid', None) if user else None}")
        
        if not user or not getattr(user, 'uid', None):
            error_response = {"error": "인증된 사용자만 접근할 수 있습니다."}
            logger.warning(f"❌ 인증 실패")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_401_UNAUTHORIZED)
        
        # 요청 데이터 검증
        logger.info(f"🔍 요청 데이터 검증 시작")
        request_serializer = InterviewQuestionGenerationRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            error_response = {"error": "입력 데이터가 유효하지 않습니다.", "details": request_serializer.errors}
            logger.warning(f"❌ 요청 데이터 검증 실패")
            logger.warning(f"   📋 검증 오류: {request_serializer.errors}")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = request_serializer.validated_data
        user_id = user.uid
        persona_id = validated_data['persona_id']
        cover_letter_id = validated_data.get('cover_letter_id')
        use_voice = validated_data.get('use_voice', False)
        
        logger.info(f"📋 파라미터 추출 완료")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        logger.info(f"   📄 cover_letter_id: {cover_letter_id}")
        logger.info(f"   🎤 use_voice: {use_voice}")
        logger.info(f"✅ 파라미터 검증 완료")
        
        # 비동기 함수 호출
        logger.info(f"📤 면접 질문 생성 서비스 호출 시작")
        logger.info(f"   🔗 generate_interview_questions(user_id={user_id}, persona_id={persona_id}, cover_letter_id={cover_letter_id}, use_voice={use_voice})")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_interview_questions(
            user_id, persona_id, cover_letter_id, use_voice
        ))
        
        logger.info(f"📥 면접 질문 생성 서비스 응답 수신")
        logger.info(f"   📊 결과: {result}")
        
        response_serializer = InterviewQuestionGenerationResponseSerializer(result)
        logger.info(f"✅ 면접 질문 생성 성공, 응답: {response_serializer.data}")
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except InterviewServiceError as exc:
        error_response = {"error": "면접 질문 생성에 실패했습니다.", "details": str(exc)}
        logger.error(f"❌ 면접 질문 생성 서비스 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as exc:
        error_response = {"error": "서버 오류가 발생했습니다."}
        logger.error(f"❌ 면접 질문 생성 중 예상치 못한 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def submit_answer_and_get_next_view(request):
    """답변을 제출하고 다음 질문을 반환합니다. (텍스트/음성 모두 지원)"""
    logger.info("💬 답변 제출 및 다음 질문 조회 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 요청 데이터: {request.data}")
    logger.info(f"🔍 요청 파일: {list(request.FILES.keys()) if hasattr(request, 'FILES') else 'None'}")
    
    try:
        user = getattr(request, 'user', None)
        logger.info(f"👤 인증된 사용자 확인: {user}")
        logger.info(f"🔑 사용자 UID: {getattr(user, 'uid', None) if user else None}")
        
        if not user or not getattr(user, 'uid', None):
            error_response = {"error": "인증된 사용자만 접근할 수 있습니다."}
            logger.warning(f"❌ 인증 실패")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_401_UNAUTHORIZED)
        
        # 음성 파일이 있는지 확인
        has_audio_file = 'audio_file' in request.FILES
        logger.info(f"🎤 음성 파일 존재 여부: {has_audio_file}")
        
        if has_audio_file:
            # 음성 답변 처리
            logger.info(f"🎤 음성 답변 처리 시작")
            logger.info(f"🔍 음성 답변 데이터 검증 시작")
            
            request_serializer = VoiceAnswerSubmissionRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                error_response = {"error": "입력 데이터가 유효하지 않습니다.", "details": request_serializer.errors}
                logger.warning(f"❌ 음성 답변 데이터 검증 실패")
                logger.warning(f"   📋 검증 오류: {request_serializer.errors}")
                logger.warning(f"📤 오류 응답: {error_response}")
                return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
            
            validated_data = request_serializer.validated_data
            user_id = user.uid
            persona_id = validated_data['persona_id']
            interview_session_id = validated_data['interview_session_id']
            question_id = validated_data['question_id']
            question_number = validated_data['question_number']
            audio_file = validated_data['audio_file']
            time_taken = validated_data['time_taken']
            
            logger.info(f"📋 음성 답변 파라미터 추출 완료")
            logger.info(f"   👤 user_id: {user_id}")
            logger.info(f"   🎭 persona_id: {persona_id}")
            logger.info(f"   🆔 interview_session_id: {interview_session_id}")
            logger.info(f"   ❓ question_id: {question_id}")
            logger.info(f"   🔢 question_number: {question_number}")
            logger.info(f"   🎵 audio_file: {audio_file.name if audio_file else None}")
            logger.info(f"   ⏱️ time_taken: {time_taken}")
            logger.info(f"✅ 음성 답변 파라미터 검증 완료")
            
            # 음성을 텍스트로 변환 후 답변 제출
            logger.info(f"📤 음성 답변 처리 서비스 호출 시작")
            logger.info(f"   🔗 submit_voice_answer_async(user_id={user_id}, persona_id={persona_id}, interview_session_id={interview_session_id}, question_id={question_id}, question_number={question_number}, audio_file={audio_file.name if audio_file else None}, time_taken={time_taken})")
            
            from .services import submit_voice_answer_async
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.create_task(submit_voice_answer_async(
                user_id, persona_id, interview_session_id, question_id, 
                question_number, audio_file, time_taken
            ))
        else:
            # 텍스트 답변 처리
            logger.info(f"📝 텍스트 답변 처리 시작")
            logger.info(f"🔍 텍스트 답변 데이터 검증 시작")
            
            request_serializer = AnswerSubmissionRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                error_response = {"error": "입력 데이터가 유효하지 않습니다.", "details": request_serializer.errors}
                logger.warning(f"❌ 텍스트 답변 데이터 검증 실패")
                logger.warning(f"   📋 검증 오류: {request_serializer.errors}")
                logger.warning(f"📤 오류 응답: {error_response}")
                return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
            
            validated_data = request_serializer.validated_data
            user_id = user.uid
            persona_id = validated_data['persona_id']
            interview_session_id = validated_data['interview_session_id']
            question_id = validated_data['question_id']
            question_number = validated_data['question_number']
            answer_text = validated_data['answer_text']
            time_taken = validated_data['time_taken']
            
            logger.info(f"📋 텍스트 답변 파라미터 추출 완료")
            logger.info(f"   👤 user_id: {user_id}")
            logger.info(f"   🎭 persona_id: {persona_id}")
            logger.info(f"   🆔 interview_session_id: {interview_session_id}")
            logger.info(f"   ❓ question_id: {question_id}")
            logger.info(f"   🔢 question_number: {question_number}")
            logger.info(f"   📝 answer_text: {answer_text[:100] + '...' if len(answer_text) > 100 else answer_text}")
            logger.info(f"   ⏱️ time_taken: {time_taken}")
            logger.info(f"✅ 텍스트 답변 파라미터 검증 완료")
            
            # 비동기로 답변 제출 (백그라운드에서 처리)
            logger.info(f"📤 텍스트 답변 처리 서비스 호출 시작")
            logger.info(f"   🔗 submit_answer_async(user_id={user_id}, persona_id={persona_id}, interview_session_id={interview_session_id}, question_id={question_id}, question_number={question_number}, answer_text={answer_text[:50] + '...' if len(answer_text) > 50 else answer_text}, time_taken={time_taken})")
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            # submit_answer_async 함수를 직접 import하여 사용
            from .services import submit_answer_async
            loop.create_task(submit_answer_async(
                user_id, persona_id, interview_session_id, question_id, 
                question_number, answer_text, time_taken
            ))
        
        # 마지막 질문인지 확인 (질문 번호가 10이면 면접 완료)
        logger.info(f"🔍 질문 번호 확인: {question_number}")
        if question_number == 10:
            logger.info(f"🏁 마지막 질문 (10번) - 면접 완료 처리 시작")
            # 마지막 질문의 답변도 먼저 제출하고 결과 반환
            if has_audio_file:
                logger.info(f"🎤 마지막 질문 음성 답변 동기 처리 시작")
                # 음성 답변을 동기적으로 처리 (마지막 질문이므로)
                from .services import submit_voice_answer_async
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(submit_voice_answer_async(
                    user_id, persona_id, interview_session_id, question_id, 
                    question_number, audio_file, time_taken
                ))
                logger.info(f"✅ 마지막 질문 음성 답변 처리 완료")
            else:
                logger.info(f"📝 마지막 질문 텍스트 답변 동기 처리 시작")
                # 텍스트 답변을 동기적으로 처리 (마지막 질문이므로)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(submit_answer_async(
                    user_id, persona_id, interview_session_id, question_id, 
                    question_number, answer_text, time_taken
                ))
                logger.info(f"✅ 마지막 질문 텍스트 답변 처리 완료")
            
            # 면접 세션 결과 반환
            logger.info(f"📤 면접 세션 결과 조회 시작")
            logger.info(f"   🔗 get_interview_session_result(user_id={user_id}, persona_id={persona_id}, interview_session_id={interview_session_id})")
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            result = loop.run_until_complete(get_interview_session_result(
                user_id, persona_id, interview_session_id
            ))
            
            logger.info(f"📥 면접 세션 결과 수신")
            logger.info(f"   📊 결과: {result}")
            
            response_serializer = InterviewSessionResultSerializer(result)
            logger.info(f"✅ 면접 완료 - 세션 결과 반환: {response_serializer.data}")
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            # 다음 질문 반환
            logger.info(f"➡️ 다음 질문 조회 시작 (현재 질문: {question_number}, 다음 질문: {question_number + 1})")
            logger.info(f"   🔗 get_next_question(user_id={user_id}, persona_id={persona_id}, interview_session_id={interview_session_id}, question_number={question_number + 1})")
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            next_question = loop.run_until_complete(get_next_question(
                user_id, persona_id, interview_session_id, question_number + 1
            ))
            
            logger.info(f"📥 다음 질문 수신")
            logger.info(f"   📊 다음 질문: {next_question}")
            response_serializer = NextQuestionResponseSerializer(next_question)
            logger.info(f"✅ 다음 질문 반환 성공: {response_serializer.data}")
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except InterviewServiceError as exc:
        error_response = {"error": "답변 제출 및 다음 질문 조회에 실패했습니다.", "details": str(exc)}
        logger.error(f"❌ 답변 제출 및 다음 질문 조회 서비스 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as exc:
        error_response = {"error": "서버 오류가 발생했습니다."}
        logger.error(f"❌ 답변 제출 및 다음 질문 조회 중 예상치 못한 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_question_detail_view(request, interview_session_id, question_id):
    """특정 질문의 상세 정보를 조회합니다."""
    logger.info("❓ 질문 상세 정보 조회 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 쿼리 파라미터: {dict(request.GET)}")
    logger.info(f"🔍 URL 파라미터 - interview_session_id: {interview_session_id}, question_id: {question_id}")
    
    try:
        user = getattr(request, 'user', None)
        logger.info(f"👤 인증된 사용자 확인: {user}")
        logger.info(f"🔑 사용자 UID: {getattr(user, 'uid', None) if user else None}")
        
        if not user or not getattr(user, 'uid', None):
            error_response = {"error": "인증된 사용자만 접근할 수 있습니다."}
            logger.warning(f"❌ 인증 실패")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = user.uid
        persona_id = request.GET.get('persona_id')
        
        logger.info(f"📋 파라미터 추출 완료")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        logger.info(f"   🆔 interview_session_id: {interview_session_id}")
        logger.info(f"   ❓ question_id: {question_id}")
        
        # 파라미터 검증
        logger.info(f"🔍 파라미터 검증 시작")
        
        if not persona_id:
            error_response = {"error": "persona_id 파라미터가 필요합니다."}
            logger.warning(f"❌ persona_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"✅ 파라미터 검증 완료")
        
        # 비동기 함수 호출
        logger.info(f"📤 질문 상세 조회 서비스 호출 시작")
        logger.info(f"   🔗 get_question_detail(user_id={user_id}, persona_id={persona_id}, interview_session_id={interview_session_id}, question_id={question_id})")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_question_detail(
            user_id, persona_id, interview_session_id, question_id
        ))
        
        logger.info(f"📥 질문 상세 조회 서비스 응답 수신")
        logger.info(f"   📊 결과: {result}")
        
        response_serializer = QuestionDetailResponseSerializer(result)
        logger.info(f"✅ 질문 상세 조회 성공, 응답: {response_serializer.data}")
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except InterviewServiceError as exc:
        error_response = {"error": "질문 상세 조회에 실패했습니다.", "details": str(exc)}
        logger.error(f"❌ 질문 상세 조회 서비스 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as exc:
        error_response = {"error": "서버 오류가 발생했습니다."}
        logger.error(f"❌ 질문 상세 조회 중 예상치 못한 오류: {exc}")
        logger.error(f"📤 오류 응답: {error_response}")
        return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




