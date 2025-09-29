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
    logger.info("🏥 Cover Letters 헬스 체크 요청")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    
    user = getattr(request, 'user', None)
    uid = getattr(user, 'uid', None)
    
    logger.info(f"👤 사용자 정보: {uid}")
    logger.info(f"✅ 헬스 체크 완료")
    
    response_data = {"ok": True, "feature": "cover_letters", "uid": uid}
    logger.info(f"📤 응답 데이터: {response_data}")
    
    return Response(response_data)


@api_view(["GET"])
def get_persona_card(request):
    """페르소나 카드 데이터를 반환합니다."""
    logger.info("🎭 페르소나 카드 조회 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 쿼리 파라미터: {dict(request.GET)}")
    
    try:
        # 인증된 사용자 ID를 가져오는 로직
        logger.info(f"🔍 사용자 인증 확인 시작")
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'uid', None):
            logger.warning(f"❌ 인증되지 않은 사용자")
            return Response(
                {"error": "인증된 사용자만 접근할 수 있습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user_id = user.uid
        logger.info(f"✅ 사용자 인증 완료: {user_id}")

        persona_id = request.GET.get('persona_id')
        logger.info(f"📋 persona_id 파라미터: {persona_id}")
        
        if not persona_id:
            logger.warning(f"❌ persona_id 파라미터 누락")
            return Response(
                {"error": "persona_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 페르소나 데이터 조회
        logger.info(f"🔗 Firestore 클라이언트 확인 시작")
        db = getattr(settings, "FIREBASE_DB", None)
        if not db:
            logger.error(f"❌ Firestore 클라이언트 없음")
            return Response(
                {"error": "Firestore 클라이언트를 찾을 수 없습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        logger.info(f"✅ Firestore 클라이언트 확인 완료")

        logger.info(f"📤 페르소나 데이터 조회 시작")
        logger.info(f"   🔗 get_persona_document(user_id={user_id}, persona_id={persona_id})")
        persona_data = get_persona_document(user_id=user_id, persona_id=persona_id, db=db)
        logger.info(f"📥 페르소나 데이터 수신 완료")
        logger.info(f"   📊 페르소나 데이터: {persona_data}")

        logger.info(f"🔧 페르소나 카드 생성 시작")
        persona_card = create_persona_card(persona_data)
        logger.info(f"✅ 페르소나 카드 생성 완료")
        logger.info(f"   📋 페르소나 카드: {persona_card}")

        response_data = {
            "persona_card": persona_card
        }
        logger.info(f"🎉 페르소나 카드 조회 성공")
        logger.info(f"📤 응답 데이터 전송: {response_data}")

        return Response(response_data, status=status.HTTP_200_OK)

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
    logger.info("📝 자기소개서 생성 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 요청 데이터: {request.data}")
    
    try:
        # 요청 데이터 검증
        logger.info(f"🔍 요청 데이터 검증 시작")
        serializer = CoverLetterRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"❌ 요청 데이터 검증 실패")
            logger.warning(f"   📋 오류 내용: {serializer.errors}")
            return Response(
                {"error": "입력 데이터가 유효하지 않습니다.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        logger.info(f"✅ 요청 데이터 검증 완료")
        logger.info(f"   📋 검증된 데이터: {validated_data}")
        
        # 자기소개서 생성 (동기적으로 실행)
        logger.info(f"📤 자기소개서 생성 서비스 호출 시작")
        logger.info(f"   🔗 generate_cover_letter 호출")
        logger.info(f"   👤 user_id: {validated_data['user_id']}")
        logger.info(f"   🎭 persona_id: {validated_data['persona_id']}")
        logger.info(f"   🏢 company_name: {validated_data['company_name']}")
        logger.info(f"   💪 strengths: {validated_data['strengths']}")
        logger.info(f"   🎯 activities: {validated_data['activities']}")
        logger.info(f"   🎨 style: {validated_data['style']}")
        
        import asyncio
        cover_letter_data = asyncio.run(generate_cover_letter(
            user_id=validated_data['user_id'],
            persona_id=validated_data['persona_id'],
            company_name=validated_data['company_name'],
            strengths=validated_data['strengths'],
            activities=validated_data['activities'],
            style=validated_data['style']
        ))
        
        logger.info(f"📥 자기소개서 생성 서비스 응답 수신")
        logger.info(f"   📊 생성된 데이터: {cover_letter_data}")
        
        # 응답 데이터 직렬화
        logger.info(f"🔧 응답 데이터 직렬화 시작")
        response_serializer = CoverLetterResponseSerializer(cover_letter_data)
        logger.info(f"✅ 응답 데이터 직렬화 완료")
        
        logger.info(f"🎉 자기소개서 생성 성공")
        logger.info(f"📤 응답 데이터 전송: {response_serializer.data}")
        
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
    logger.info("📋 자기소개서 목록 조회 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 쿼리 파라미터: {dict(request.GET)}")
    
    try:
        # 인증된 사용자 ID를 가져오는 로직 (실제 배포 시 사용)
        logger.info(f"🔍 사용자 인증 확인 시작")
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'uid', None):
            logger.warning(f"❌ 인증되지 않은 사용자")
            return Response(
                {"error": "인증된 사용자만 접근할 수 있습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user_id = user.uid
        logger.info(f"✅ 사용자 인증 완료: {user_id}")

        persona_id = request.GET.get('persona_id')
        logger.info(f"📋 persona_id 파라미터: {persona_id}")

        if not persona_id:
            logger.warning(f"❌ persona_id 파라미터 누락")
            return Response(
                {"error": "persona_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 페르소나 카드 데이터 조회
        logger.info(f"🔗 Firestore 클라이언트 확인 시작")
        db = getattr(settings, "FIREBASE_DB", None)
        if not db:
            logger.error(f"❌ Firestore 클라이언트 없음")
            return Response(
                {"error": "Firestore 클라이언트를 찾을 수 없습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        logger.info(f"✅ Firestore 클라이언트 확인 완료")

        logger.info(f"📤 페르소나 데이터 조회 시작")
        logger.info(f"   🔗 get_persona_document(user_id={user_id}, persona_id={persona_id})")
        persona_data = get_persona_document(user_id=user_id, persona_id=persona_id, db=db)
        logger.info(f"📥 페르소나 데이터 수신 완료")
        logger.info(f"   📊 페르소나 데이터: {persona_data}")

        logger.info(f"🔧 페르소나 카드 생성 시작")
        persona_card = create_persona_card(persona_data)
        logger.info(f"✅ 페르소나 카드 생성 완료")
        logger.info(f"   📋 페르소나 카드: {persona_card}")

        # 자기소개서 목록 조회 (동기적으로 실행)
        logger.info(f"📤 자기소개서 목록 조회 서비스 호출 시작")
        logger.info(f"   🔗 get_cover_letters(user_id={user_id}, persona_id={persona_id})")
        import asyncio
        cover_letters = asyncio.run(get_cover_letters(user_id, persona_id))
        logger.info(f"📥 자기소개서 목록 수신 완료")
        logger.info(f"   📊 자기소개서 수: {len(cover_letters) if cover_letters else 0}")
        logger.info(f"   📋 자기소개서 목록: {cover_letters}")

        # 필요한 필드만 추출
        logger.info(f"🔧 자기소개서 요약 데이터 생성 시작")
        cover_letter_summaries = []
        for i, cover_letter in enumerate(cover_letters):
            summary = {
                "id": cover_letter.get("id"),
                "company_name": cover_letter.get("company_name"),
                "created_at": cover_letter.get("created_at"),
                "character_count": cover_letter.get("character_count"),
                "style": cover_letter.get("style")
            }
            cover_letter_summaries.append(summary)
            logger.info(f"   📝 요약 {i+1}: {summary}")
        logger.info(f"✅ 자기소개서 요약 데이터 생성 완료")

        # 응답 데이터 직렬화
        logger.info(f"🔧 응답 데이터 구성 시작")
        response_data = {
            "cover_letters": cover_letter_summaries,
            "total_count": len(cover_letter_summaries),
            "persona_card": persona_card
        }
        logger.info(f"   📊 응답 데이터: {response_data}")

        logger.info(f"🔧 응답 데이터 직렬화 시작")
        response_serializer = CoverLetterListResponseSerializer(response_data)
        logger.info(f"✅ 응답 데이터 직렬화 완료")

        logger.info(f"🎉 자기소개서 목록 조회 성공")
        logger.info(f"📤 응답 데이터 전송: {response_serializer.data}")

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
    logger.info("📄 자기소개서 상세 조회 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 쿼리 파라미터: {dict(request.GET)}")
    logger.info(f"🔍 경로 파라미터 - cover_letter_id: {cover_letter_id}")
    
    try:
        # 인증된 사용자 ID를 가져오는 로직
        logger.info(f"🔍 사용자 인증 확인 시작")
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'uid', None):
            logger.warning(f"❌ 인증되지 않은 사용자")
            return Response(
                {"error": "인증된 사용자만 접근할 수 있습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user_id = user.uid
        logger.info(f"✅ 사용자 인증 완료: {user_id}")

        persona_id = request.GET.get('persona_id')
        logger.info(f"📋 persona_id 파라미터: {persona_id}")
        
        if not persona_id:
            logger.warning(f"❌ persona_id 파라미터 누락")
            return Response(
                {"error": "persona_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 자기소개서 상세 조회 (동기적으로 실행)
        logger.info(f"📤 자기소개서 상세 조회 서비스 호출 시작")
        logger.info(f"   🔗 get_cover_letter_detail_service(user_id={user_id}, persona_id={persona_id}, cover_letter_id={cover_letter_id})")
        import asyncio
        cover_letter_data = asyncio.run(get_cover_letter_detail_service(user_id, persona_id, cover_letter_id))
        logger.info(f"📥 자기소개서 상세 데이터 수신 완료")
        logger.info(f"   📊 상세 데이터: {cover_letter_data}")

        # 응답 데이터 직렬화
        logger.info(f"🔧 응답 데이터 직렬화 시작")
        response_serializer = CoverLetterResponseSerializer(cover_letter_data)
        logger.info(f"✅ 응답 데이터 직렬화 완료")

        logger.info(f"🎉 자기소개서 상세 조회 성공")
        logger.info(f"📤 응답 데이터 전송: {response_serializer.data}")

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

