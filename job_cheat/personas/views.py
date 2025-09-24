import logging
import signal
from uuid import uuid4

from django.http import HttpResponse
from rest_framework import exceptions, status
from rest_framework.decorators import api_view
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView



from core.authentication import FirebaseAuthentication
from core.services.firebase_personas import (
    PersonaInputSaveError,
    save_user_persona_input,
)
from core.services.firebase_storage import (
    PersonaHtmlUploadError,
    upload_persona_html,
)
from core.services.persona_html_processor import (
    PersonaHtmlProcessingError,
    process_persona_html_to_json,
)
from personas.api.serializers import PersonaInputSerializer

logger = logging.getLogger(__name__)


def handle_broken_pipe(func):
    """Broken pipe 오류를 처리하는 데코레이터"""
    def wrapper(self, request, *args, **kwargs):
        try:
            return func(self, request, *args, **kwargs)
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.warning(f"클라이언트 연결이 끊어졌습니다: {e}")
            # 클라이언트가 연결을 끊었으므로 응답을 보내지 않음
            return None
        except AttributeError as e:
            if "'Empty' object has no attribute 'closed'" in str(e):
                logger.debug(f"연결 상태 확인 중 예상된 오류 (무시): {e}")
                # 이 오류는 무시하고 원래 함수를 다시 실행
                return func(self, request, *args, **kwargs)
            else:
                logger.error(f"속성 접근 오류: {e}")
                raise
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            raise
    return wrapper


@api_view(["GET"])
def health(request):
    user = getattr(request, "user", None)
    uid = getattr(user, "uid", None)
    return Response({"ok": True, "feature": "personas", "uid": uid})


class PersonaInputCreateView(APIView):
    """사용자 페르소나 정보를 HTML 파일과 함께 저장한다."""

    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_parsers(self):
        """대용량 파일 처리를 위한 커스텀 파서 설정"""
        parsers = super().get_parsers()
        # MultiPartParser를 먼저 사용하여 대용량 파일을 임시 파일로 저장
        return [parser for parser in parsers if isinstance(parser, MultiPartParser)] + \
               [parser for parser in parsers if not isinstance(parser, MultiPartParser)]

    def options(self, request, *args, **kwargs):
        """CORS preflight 요청을 처리한다."""
        response = Response()
        response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
        response['Access-Control-Max-Age'] = '86400'
        return response

    @handle_broken_pipe
    def post(self, request):
        """
        사용자의 페르소나 데이터와 HTML 파일을 받아서 처리합니다.
        
        처리 과정:
        1. HTML 파일을 Firebase Storage에 업로드 (users/{uid}/html/{uid}.html)
        2. ChatGPT 변환기를 사용하여 HTML을 JSON으로 변환
        3. JSON 파일을 Firebase Storage에 저장 (users/{uid}/json/{uid}.json)
        4. 원본 HTML 파일 삭제
        5. Firestore에 메타데이터 저장 (users/{uid}/personas/{personaId})
        """
        # 클라이언트 연결 상태 확인 (안전한 방식)
        try:
            if hasattr(request, '_stream') and hasattr(request._stream, 'closed') and request._stream.closed:
                logger.warning("클라이언트 연결이 이미 끊어져 있습니다.")
                return None
        except (AttributeError, TypeError) as e:
            # _stream이 Empty 타입이거나 closed 속성이 없는 경우 무시
            logger.debug(f"연결 상태 확인 중 예상된 오류 (무시): {e}")
            pass
        serializer = PersonaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = getattr(request, "user", None)
        user_id = getattr(user, "uid", None)
        if not user_id:
            raise exceptions.NotAuthenticated("Firebase 사용자 인증이 필요합니다.")

        document_id = str(uuid4())
        html_file = serializer.uploaded_html_file

        logger.info(f"페르소나 입력 처리 시작: user_id={user_id}, document_id={document_id}")

        try:
            # 1. HTML 파일을 Storage에 업로드 (users/{uid}/html/{uid}.html)
            logger.info(f"HTML 파일 업로드 시작: user_id={user_id}")
            
            # 연결 상태 재확인 (안전한 방식)
            try:
                if hasattr(request, '_stream') and hasattr(request._stream, 'closed') and request._stream.closed:
                    logger.warning("업로드 시작 전 클라이언트 연결이 끊어졌습니다.")
                    return None
            except (AttributeError, TypeError) as e:
                # _stream이 Empty 타입이거나 closed 속성이 없는 경우 무시
                logger.debug(f"업로드 전 연결 상태 확인 중 예상된 오류 (무시): {e}")
                pass
            
            # HTML 파일을 복사하여 업로드용과 읽기용으로 분리
            html_file_copy = serializer.uploaded_html_file
            logger.info(f"업로드할 HTML 파일 정보: 크기={html_file_copy.size} bytes, 타입={html_file_copy.content_type}")
            
            upload_result = upload_persona_html(
                user_id=user_id,
                document_id=document_id,
                file_obj=html_file_copy,
            )
            logger.info(f"HTML 파일 업로드 완료: 경로={upload_result['path']}, 크기={upload_result['size']} bytes, 타입={upload_result['content_type']}")
        except PersonaHtmlUploadError as exc:
            logger.error(f"HTML 파일 업로드 실패: {exc}")
            raise exceptions.APIException(f"HTML 파일 업로드에 실패했습니다: {exc}") from exc

        # 2. HTML 파일을 읽어서 JSON으로 변환하고 Storage에 저장
        # 원본 파일을 다시 가져와서 읽기 (업로드 후 포인터 위치가 변경될 수 있음)
        html_file_for_reading = serializer.validated_data["html_file"]
        
        # 대용량 파일 처리를 위한 streaming 읽기
        try:
            logger.info(f"HTML 파일 읽기 시작: user_id={user_id}, 파일 크기={html_file_for_reading.size} bytes")
            
            # 파일 포인터를 처음으로 이동
            html_file_for_reading.seek(0)
            
            # 임시 파일인지 확인 (streaming 업로드인 경우)
            if hasattr(html_file_for_reading, 'temporary_file_path'):
                # 임시 파일에서 직접 읽기 (메모리 효율적)
                with open(html_file_for_reading.temporary_file_path(), 'r', encoding='utf-8') as f:
                    html_content = f.read()
                logger.info(f"임시 파일에서 HTML 읽기 완료: {len(html_content):,} 문자")
            else:
                # 메모리에서 읽기 (작은 파일의 경우)
                html_content = html_file_for_reading.read().decode('utf-8')
                logger.info(f"메모리에서 HTML 읽기 완료: {len(html_content):,} 문자")
                
        except UnicodeDecodeError as exc:
            logger.error(f"HTML 파일 인코딩 오류: {exc}")
            raise exceptions.APIException("HTML 파일 인코딩이 올바르지 않습니다. UTF-8 인코딩을 사용해주세요.") from exc
        except MemoryError as exc:
            logger.error(f"HTML 파일이 너무 큽니다: {exc}")
            raise exceptions.APIException("HTML 파일이 너무 큽니다. 파일 크기를 줄여주세요.") from exc
        except Exception as exc:
            logger.error(f"HTML 파일 읽기 실패: {exc}")
            raise exceptions.APIException("HTML 파일을 읽을 수 없습니다.") from exc
        
        try:
            logger.info(f"HTML을 JSON으로 변환 시작: user_id={user_id}, HTML 크기={len(html_content):,} 문자")
            processing_result = process_persona_html_to_json(
                user_id=user_id,
                document_id=document_id,
                html_content=html_content,
                html_file_path=upload_result["path"],
            )
            logger.info(f"HTML 처리 완료: JSON 파일={processing_result['json_file_path']}, JSON 크기={processing_result['json_file_size']} bytes, 대화 수={processing_result['conversations_count']}, HTML 삭제됨={processing_result['html_file_deleted']}")
        except PersonaHtmlProcessingError as exc:
            logger.error(f"HTML 파일 처리 실패: {exc}")
            raise exceptions.APIException(f"HTML 파일 처리에 실패했습니다: {exc}") from exc

        # 3. Firestore에 메타데이터 저장 (users/{uid}/personas/{personaId})
        payload = serializer.to_firestore_payload(
            html_file_path=upload_result["path"],
            html_content_type=upload_result["content_type"],
            html_file_size=upload_result["size"],
        )
        
        # JSON 파일 정보 추가
        payload.update({
            "json_file_path": processing_result["json_file_path"],
            "json_content_type": processing_result["json_content_type"],
            "json_file_size": processing_result["json_file_size"],
            "conversations_count": processing_result["conversations_count"],
            "html_file_deleted": processing_result["html_file_deleted"],
        })

        logger.info(f"Firestore 저장할 페이로드: {payload}")

        try:
            logger.info(f"Firestore에 페르소나 데이터 저장 시작: user_id={user_id}, document_id={document_id}")
            firestore_result = save_user_persona_input(
                user_id=user_id,
                payload=payload,
                document_id=document_id,
            )
            logger.info(f"Firestore 저장 완료: document_id={document_id}, 저장된 데이터={firestore_result}")
        except PersonaInputSaveError as exc:
            logger.error(f"페르소나 입력 저장 실패: {exc}")
            raise exceptions.APIException(f"페르소나 입력을 저장할 수 없습니다: {exc}") from exc

        response_serializer = PersonaInputSerializer(instance=firestore_result)
        headers = {}
        if firestore_result.get("id"):
            headers["Location"] = f"/api/personas/inputs/{firestore_result['id']}"

        logger.info(f"페르소나 입력 처리 완료: user_id={user_id}, document_id={document_id}")
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
