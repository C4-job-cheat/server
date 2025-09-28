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
    return Response({"ok": True, "feature": "interviews"}, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_interview_history(request):
    """면접 기록을 조회합니다."""
    try:
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'uid', None):
            return Response(
                {"error": "인증된 사용자만 접근할 수 있습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_id = user.uid
        persona_id = request.GET.get('persona_id')
        
        if not persona_id:
            return Response(
                {"error": "persona_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 비동기 함수 호출
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_interview_record(user_id, persona_id))
        
        response_serializer = InterviewHistoryResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except InterviewServiceError as exc:
        logger.error(f"면접 기록 조회 실패: {exc}")
        return Response(
            {"error": "면접 기록 조회에 실패했습니다.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        logger.error(f"면접 기록 조회 중 예상치 못한 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(["GET"])
def get_interview_preparation(request):
    """면접 준비 데이터를 조회합니다."""
    try:
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'uid', None):
            return Response(
                {"error": "인증된 사용자만 접근할 수 있습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_id = user.uid
        persona_id = request.GET.get('persona_id')
        
        if not persona_id:
            return Response(
                {"error": "persona_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 비동기 함수 호출
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_interview_preparation_data(user_id, persona_id))
        
        response_serializer = InterviewPreparationResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except InterviewServiceError as exc:
        logger.error(f"면접 준비 데이터 조회 실패: {exc}")
        return Response(
            {"error": "면접 준비 데이터 조회에 실패했습니다.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        logger.error(f"면접 준비 데이터 조회 중 예상치 못한 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def generate_interview_questions_view(request):
    """면접 질문을 생성합니다."""
    try:
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'uid', None):
            return Response(
                {"error": "인증된 사용자만 접근할 수 있습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 요청 데이터 검증
        request_serializer = InterviewQuestionGenerationRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                {"error": "입력 데이터가 유효하지 않습니다.", "details": request_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = request_serializer.validated_data
        user_id = user.uid
        persona_id = validated_data['persona_id']
        cover_letter_id = validated_data.get('cover_letter_id')
        use_voice = validated_data.get('use_voice', False)
        
        # 비동기 함수 호출
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_interview_questions(
            user_id, persona_id, cover_letter_id, use_voice
        ))
        
        response_serializer = InterviewQuestionGenerationResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except InterviewServiceError as exc:
        logger.error(f"면접 질문 생성 실패: {exc}")
        return Response(
            {"error": "면접 질문 생성에 실패했습니다.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        logger.error(f"면접 질문 생성 중 예상치 못한 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def submit_answer_and_get_next_view(request):
    """답변을 제출하고 다음 질문을 반환합니다. (텍스트/음성 모두 지원)"""
    try:
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'uid', None):
            return Response(
                {"error": "인증된 사용자만 접근할 수 있습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 음성 파일이 있는지 확인
        has_audio_file = 'audio_file' in request.FILES
        
        if has_audio_file:
            # 음성 답변 처리
            request_serializer = VoiceAnswerSubmissionRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                return Response(
                    {"error": "입력 데이터가 유효하지 않습니다.", "details": request_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = request_serializer.validated_data
            user_id = user.uid
            persona_id = validated_data['persona_id']
            interview_session_id = validated_data['interview_session_id']
            question_id = validated_data['question_id']
            question_number = validated_data['question_number']
            audio_file = validated_data['audio_file']
            time_taken = validated_data['time_taken']
            
            # 음성을 텍스트로 변환 후 답변 제출
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
            request_serializer = AnswerSubmissionRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                return Response(
                    {"error": "입력 데이터가 유효하지 않습니다.", "details": request_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = request_serializer.validated_data
            user_id = user.uid
            persona_id = validated_data['persona_id']
            interview_session_id = validated_data['interview_session_id']
            question_id = validated_data['question_id']
            question_number = validated_data['question_number']
            answer_text = validated_data['answer_text']
            time_taken = validated_data['time_taken']
            
            # 비동기로 답변 제출 (백그라운드에서 처리)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.create_task(submit_answer_async(
                user_id, persona_id, interview_session_id, question_id, 
                question_number, answer_text, time_taken
            ))
        
        # 마지막 질문인지 확인 (질문 번호가 10이면 면접 완료)
        if question_number == 10:
            # 마지막 질문의 답변도 먼저 제출하고 결과 반환
            if has_audio_file:
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
            else:
                # 텍스트 답변을 동기적으로 처리 (마지막 질문이므로)
                from .services import submit_answer_async
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(submit_answer_async(
                    user_id, persona_id, interview_session_id, question_id, 
                    question_number, answer_text, time_taken
                ))
            
            # 면접 세션 결과 반환
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            result = loop.run_until_complete(get_interview_session_result(
                user_id, persona_id, interview_session_id
            ))
            response_serializer = InterviewSessionResultSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            # 다음 질문 반환
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            next_question = loop.run_until_complete(get_next_question(
                user_id, persona_id, interview_session_id, question_number + 1
            ))
            response_serializer = NextQuestionResponseSerializer(next_question)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except InterviewServiceError as exc:
        logger.error(f"답변 제출 및 다음 질문 조회 실패: {exc}")
        return Response(
            {"error": "답변 제출 및 다음 질문 조회에 실패했습니다.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        logger.error(f"답변 제출 및 다음 질문 조회 중 예상치 못한 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def get_question_detail_view(request, interview_session_id, question_id):
    """특정 질문의 상세 정보를 조회합니다."""
    try:
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'uid', None):
            return Response(
                {"error": "인증된 사용자만 접근할 수 있습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user_id = user.uid
        persona_id = request.GET.get('persona_id')
        
        if not persona_id:
            return Response(
                {"error": "persona_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 비동기 함수 호출
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_question_detail(
            user_id, persona_id, interview_session_id, question_id
        ))
        
        response_serializer = QuestionDetailResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except InterviewServiceError as exc:
        logger.error(f"질문 상세 조회 실패: {exc}")
        return Response(
            {"error": "질문 상세 조회에 실패했습니다.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        logger.error(f"질문 상세 조회 중 예상치 못한 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




