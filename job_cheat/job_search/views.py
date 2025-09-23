from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from .services.job_posting import add_job_to_firestore, get_all_jobs_from_firestore, vectorize_and_upsert_to_pinecone


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


