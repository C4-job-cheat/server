from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
import logging

from .serializers import (
    HealthSerializer,
    CoverLetterRequestSerializer,
    CoverLetterResponseSerializer,
    CoverLetterListResponseSerializer,
    CoverLetterSummarySerializer
)
from .services import generate_cover_letter, get_cover_letters, CoverLetterServiceError
from .services.cover_letter_service import get_cover_letter_detail as get_cover_letter_detail_service
from core.services.firebase_personas import get_persona_document, PersonaNotFoundError
from core.utils import create_persona_card
from django.conf import settings

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health(request):
    """Cover Letters 기능 헬스 체크."""
    user = getattr(request, 'user', None)
    uid = getattr(user, 'uid', None)
    return Response({"ok": True, "feature": "cover_letters", "uid": uid})


@api_view(["GET"])
def get_persona_card(request):
    """페르소나 카드 데이터를 반환합니다."""
    try:
        # 인증된 사용자 ID를 가져오는 로직
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

        # 페르소나 데이터 조회
        db = getattr(settings, "FIREBASE_DB", None)
        if not db:
            return Response(
                {"error": "Firestore 클라이언트를 찾을 수 없습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        persona_data = get_persona_document(user_id=user_id, persona_id=persona_id, db=db)
        persona_card = create_persona_card(persona_data)

        return Response({
            "persona_card": persona_card
        }, status=status.HTTP_200_OK)

    except PersonaNotFoundError as exc:
        logger.error(f"페르소나를 찾을 수 없습니다: {exc}")
        return Response(
            {"error": "페르소나를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as exc:
        logger.error(f"페르소나 카드 조회 중 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def create_cover_letter(request):
    """자기소개서를 생성합니다."""
    try:
        # 요청 데이터 검증
        serializer = CoverLetterRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "입력 데이터가 유효하지 않습니다.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        
        # 자기소개서 생성 (동기적으로 실행)
        import asyncio
        cover_letter_data = asyncio.run(generate_cover_letter(
            user_id=validated_data['user_id'],
            persona_id=validated_data['persona_id'],
            company_name=validated_data['company_name'],
            strengths=validated_data['strengths'],
            activities=validated_data['activities'],
            style=validated_data['style']
        ))
        
        # 응답 데이터 직렬화
        response_serializer = CoverLetterResponseSerializer(cover_letter_data)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except CoverLetterServiceError as exc:
        logger.error(f"자기소개서 생성 실패: {exc}")
        return Response(
            {"error": "자기소개서 생성에 실패했습니다.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        logger.error(f"자기소개서 생성 중 예상치 못한 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def list_cover_letters(request):
    """사용자의 자기소개서 목록을 조회합니다."""
    try:
        # 인증된 사용자 ID를 가져오는 로직 (실제 배포 시 사용)
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

        # 페르소나 카드 데이터 조회
        db = getattr(settings, "FIREBASE_DB", None)
        if not db:
            return Response(
                {"error": "Firestore 클라이언트를 찾을 수 없습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        persona_data = get_persona_document(user_id=user_id, persona_id=persona_id, db=db)
        persona_card = create_persona_card(persona_data)

        # 자기소개서 목록 조회 (동기적으로 실행)
        import asyncio
        cover_letters = asyncio.run(get_cover_letters(user_id, persona_id))

        # 필요한 필드만 추출
        cover_letter_summaries = []
        for cover_letter in cover_letters:
            summary = {
                "id": cover_letter.get("id"),
                "company_name": cover_letter.get("company_name"),
                "created_at": cover_letter.get("created_at"),
                "character_count": cover_letter.get("character_count"),
                "style": cover_letter.get("style")
            }
            cover_letter_summaries.append(summary)

        # 응답 데이터 직렬화
        response_data = {
            "cover_letters": cover_letter_summaries,
            "total_count": len(cover_letter_summaries),
            "persona_card": persona_card
        }

        response_serializer = CoverLetterListResponseSerializer(response_data)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except PersonaNotFoundError as exc:
        logger.error(f"페르소나를 찾을 수 없습니다: {exc}")
        return Response(
            {"error": "페르소나를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND
        )
    except CoverLetterServiceError as exc:
        logger.error(f"자기소개서 목록 조회 실패: {exc}")
        return Response(
            {"error": "자기소개서 목록 조회에 실패했습니다.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        logger.error(f"자기소개서 목록 조회 중 예상치 못한 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def get_cover_letter_detail(request, cover_letter_id):
    """특정 자기소개서의 상세 정보를 조회합니다."""
    try:
        # 인증된 사용자 ID를 가져오는 로직
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

        # 자기소개서 상세 조회 (동기적으로 실행)
        import asyncio
        cover_letter_data = asyncio.run(get_cover_letter_detail_service(user_id, persona_id, cover_letter_id))

        # 응답 데이터 직렬화
        response_serializer = CoverLetterResponseSerializer(cover_letter_data)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except CoverLetterServiceError as exc:
        logger.error(f"자기소개서 상세 조회 실패: {exc}")
        return Response(
            {"error": "자기소개서 상세 조회에 실패했습니다.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as exc:
        logger.error(f"자기소개서 상세 조회 중 예상치 못한 오류: {exc}")
        return Response(
            {"error": "서버 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

