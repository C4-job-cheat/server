import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .services.job_posting import add_job_to_firestore, get_all_jobs_from_firestore, vectorize_and_upsert_to_pinecone
from .services.job_matching import save_persona_recommendations_score, calculate_persona_job_scores, calculate_persona_job_scores_from_data
from .services.recommendation import get_user_recommendations, get_job_detail_with_recommendation

logger = logging.getLogger(__name__)


@api_view(["GET"]) 
def health(request):
    user = getattr(request, 'user', None)
    uid = getattr(user, 'uid', None)
    return Response({"ok": True, "feature": "job_search", "uid": uid})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def save_job_posting(request):
    """
    공고 데이터를 Firestore에 저장합니다.
    request body에서 job_data를 받습니다.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        job_data = request.data
        
        # 필수 필드 검증
        required_fields = ['title', 'job_description']
        for field in required_fields:
            if field not in job_data:
                return Response({
                    "success": False,
                    "message": f"필수 필드가 누락되었습니다: {field}"
                }, status=400)
        
        doc_id = add_job_to_firestore(job_data)
        return Response({
            "success": True,
            "message": "공고가 성공적으로 저장되었습니다.",
            "document_id": doc_id
        })
    except Exception as e:
        return Response({
            "success": False,
            "message": f"공고 저장 중 오류가 발생했습니다: {str(e)}"
        }, status=500)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def vectorize_job_postings(request):
    """
    Firestore에서 모든 공고를 불러와서 평문 변환, 벡터화하여 Pinecone에 저장합니다.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        # 1. Firestore에서 모든 공고 불러오기
        job_list = get_all_jobs_from_firestore()
        
        if not job_list:
            return Response({
                "success": False,
                "message": "저장된 공고가 없습니다."
            }, status=404)
        
        # 2. 평문 변환, 벡터화하여 Pinecone에 저장
        vectorize_and_upsert_to_pinecone(job_list)
        
        return Response({
            "success": True,
            "message": f"{len(job_list)}개의 공고가 성공적으로 벡터화되어 Pinecone에 저장되었습니다.",
            "processed_count": len(job_list)
        })
        
    except Exception as e:
        return Response({
            "success": False,
            "message": f"벡터화 과정에서 오류가 발생했습니다: {str(e)}"
        }, status=500)



@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_user_recommendations_view(request):
    """
    사용자의 페르소나에 저장된 추천 공고들을 상세 정보와 함께 반환합니다.
    query parameter에서 user_id, persona_id를 받습니다.
    """
    try:
        user_id = request.GET.get('user_id')
        persona_id = request.GET.get('persona_id')
        
        if not user_id:
            return Response({
                "success": False,
                "message": "user_id가 필요합니다."
            }, status=400)
            
        if not persona_id:
            return Response({
                "success": False,
                "message": "persona_id가 필요합니다."
            }, status=400)
        
        # 추천 공고 정보 가져오기
        result = get_user_recommendations(user_id, persona_id)
        
        if 'error' not in result:
            return Response({
                "persona_card": result['persona_card'],
                "competency": result['competency'],
                "recommendations": result['recommendations'],
                "total_count": result['total_count']
            })
        else:
            return Response({
                "success": False,
                "message": f"추천 공고 조회 중 오류가 발생했습니다: {result['error']}"
            }, status=500)
            
    except Exception as e:
        return Response({
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }, status=500)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_job_detail_with_recommendation_view(request, job_posting_id):
    """
    특정 공고의 상세 정보와 추천 이유를 반환합니다.
    path parameter에서 job_posting_id를, query parameter에서 user_id, persona_id를 받습니다.
    """
    try:
        user_id = request.GET.get('user_id')
        persona_id = request.GET.get('persona_id')
        
        if not user_id:
            return Response({
                "success": False,
                "message": "user_id가 필요합니다."
            }, status=400)
            
        if not persona_id:
            return Response({
                "success": False,
                "message": "persona_id가 필요합니다."
            }, status=400)
            
        
        # 공고 상세 정보와 추천 이유 가져오기
        result = get_job_detail_with_recommendation(user_id, persona_id, job_posting_id)
        
        if result['success']:
            return Response({
                "job_posting": result['job_posting'],
                "recommendation": result['recommendation']
            })
        else:
            return Response({
                "success": False,
                "message": f"공고 상세 정보 조회 중 오류가 발생했습니다: {result['error']}"
            }, status=500)
            
    except Exception as e:
        return Response({
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }, status=500)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def calculate_persona_job_scores_view(request):
    """
    사용자 ID와 페르소나 ID로 페르소나를 가져와서 각 공고의 최종 점수를 계산하여 반환합니다.
    request body에서 user_id, persona_id만 받습니다.
    테스트용으로 모든 공고의 점수를 출력합니다.

    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        user_id = request.data.get('user_id')
        persona_id = request.data.get('persona_id')
        
        if not user_id:
            return Response({
                "success": False,
                "message": "user_id가 필요합니다."
            }, status=400)
            
        if not persona_id:
            return Response({
                "success": False,
                "message": "persona_id가 필요합니다."
            }, status=400)
        
        # 각 공고의 점수 계산
        result = calculate_persona_job_scores(user_id, persona_id)
        
        if result['success']:
            return Response({
                "success": True,
                "message": result['message'],
                "persona_data": result['persona_data'],
                "job_scores": result['job_scores'],
                "total_jobs": result['total_jobs']
            })
        else:
            return Response({
                "success": False,
                "message": f"점수 계산 중 오류가 발생했습니다: {result['error']}"
            }, status=500)
            
    except Exception as e:
        return Response({
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }, status=500)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def calculate_persona_job_scores_from_data_view(request):
    """
    페르소나 데이터를 직접 받아서 각 공고의 최종 점수를 계산하여 반환합니다.
    request body에서 persona_data를 받습니다.
    테스트용으로 모든 공고의 점수를 출력합니다.

    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        persona_data = request.data.get('persona_data')
        
        if not persona_data:
            return Response({
                "success": False,
                "message": "persona_data가 필요합니다."
            }, status=400)
        
        # 각 공고의 점수 계산
        result = calculate_persona_job_scores_from_data(persona_data)
        
        if result['success']:
            return Response({
                "success": True,
                "message": result['message'],
                "persona_data": result['persona_data'],
                "job_scores": result['job_scores'],
                "total_jobs": result['total_jobs']
            })
        else:
            return Response({
                "success": False,
                "message": f"점수 계산 중 오류가 발생했습니다: {result['error']}"
            }, status=500)
            
    except Exception as e:
        return Response({
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }, status=500)