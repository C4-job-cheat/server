from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from .services.job_posting import add_job_to_firestore, get_all_jobs_from_firestore, vectorize_and_upsert_to_pinecone
from .services.job_matching import get_persona_and_match_jobs, find_matching_jobs


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


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def match_jobs_by_persona(request):
    """
    사용자 ID와 페르소나 ID로 페르소나를 가져와서 매칭된 공고를 반환합니다.
    request body에서 user_id, persona_id와 top_k(선택사항)를 받습니다.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        user_id = request.data.get('user_id')
        persona_id = request.data.get('persona_id')
        top_k = request.data.get('top_k', 5)  # 기본값 5
        
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
        
        # 페르소나 기반 공고 매칭 실행
        result = get_persona_and_match_jobs(user_id, persona_id, top_k)
        
        if result['success']:
            return Response({
                "success": True,
                "message": f"{result['total_matches']}개의 매칭된 공고를 찾았습니다.",
                "persona_data": result['persona_data'],
                "matching_jobs": result['matching_jobs'],
                "total_matches": result['total_matches']
            })
        else:
            return Response({
                "success": False,
                "message": f"공고 매칭 중 오류가 발생했습니다: {result['error']}"
            }, status=500)
            
    except Exception as e:
        return Response({
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }, status=500)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def match_jobs_by_persona_data(request):
    """
    페르소나 데이터를 직접 받아서 매칭된 공고를 반환합니다.
    request body에서 persona_data와 top_k(선택사항)를 받습니다.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        persona_data = request.data.get('persona_data')
        top_k = request.data.get('top_k', 5)  # 기본값 5
        
        if not persona_data:
            return Response({
                "success": False,
                "message": "persona_data가 필요합니다."
            }, status=400)
        
        # 페르소나 데이터로 직접 매칭 실행
        matching_jobs = find_matching_jobs(persona_data, top_k)
        
        return Response({
            "success": True,
            "message": f"{len(matching_jobs)}개의 매칭된 공고를 찾았습니다.",
            "persona_data": {
                'job_category': persona_data.get('job_category'),
                'job_title': persona_data.get('job_title'),
                'skills': persona_data.get('skills', [])
            },
            "matching_jobs": matching_jobs,
            "total_matches": len(matching_jobs)
        })
            
    except Exception as e:
        return Response({
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }, status=500)


