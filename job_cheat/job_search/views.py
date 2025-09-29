import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .services.job_posting import add_job_to_firestore, get_all_jobs_from_firestore, vectorize_and_upsert_to_pinecone
from .services.job_matching import save_persona_recommendations_score, calculate_persona_job_scores, calculate_persona_job_scores_from_data
from .services.recommendation import get_user_recommendations, get_job_detail_with_recommendation
from .services.scrap_service import add_job_to_scrap, remove_job_from_scrap, get_scraped_jobs, ScrapServiceError

logger = logging.getLogger(__name__)


@api_view(["GET"]) 
def health(request):
    logger.info("job_search health check 요청")
    user = getattr(request, 'user', None)
    uid = getattr(user, 'uid', None)
    response_data = {"ok": True, "feature": "job_search", "uid": uid}
    logger.info(f"job_search health check 응답: {response_data}")
    return Response(response_data)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def save_job_posting(request):
    """
    공고 데이터를 Firestore에 저장합니다.
    request body에서 job_data를 받습니다.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    logger.info("공고 저장 요청")
    try:
        job_data = request.data
        logger.info(f"받은 job_data: {job_data}")
        
        # 필수 필드 검증
        required_fields = ['title', 'job_description']
        for field in required_fields:
            if field not in job_data:
                error_response = {
                    "success": False,
                    "message": f"필수 필드가 누락되었습니다: {field}"
                }
                logger.warning(f"필수 필드 누락: {field}, 응답: {error_response}")
                return Response(error_response, status=400)
        
        doc_id = add_job_to_firestore(job_data)
        success_response = {
            "success": True,
            "message": "공고가 성공적으로 저장되었습니다.",
            "document_id": doc_id
        }
        logger.info(f"공고 저장 성공, 응답: {success_response}")
        return Response(success_response)
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"공고 저장 중 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"공고 저장 중 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def vectorize_job_postings(request):
    """
    Firestore에서 모든 공고를 불러와서 평문 변환, 벡터화하여 Pinecone에 저장합니다.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    logger.info("공고 벡터화 요청")
    try:
        # 1. Firestore에서 모든 공고 불러오기
        job_list = get_all_jobs_from_firestore()
        logger.info(f"Firestore에서 {len(job_list)}개의 공고 조회")
        
        if not job_list:
            error_response = {
                "success": False,
                "message": "저장된 공고가 없습니다."
            }
            logger.warning(f"저장된 공고 없음, 응답: {error_response}")
            return Response(error_response, status=404)
        
        # 2. 평문 변환, 벡터화하여 Pinecone에 저장
        vectorize_and_upsert_to_pinecone(job_list)
        
        success_response = {
            "success": True,
            "message": f"{len(job_list)}개의 공고가 성공적으로 벡터화되어 Pinecone에 저장되었습니다.",
            "processed_count": len(job_list)
        }
        logger.info(f"공고 벡터화 성공, 응답: {success_response}")
        return Response(success_response)
        
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"벡터화 과정에서 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"벡터화 과정에서 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)



@api_view(["GET"])
def get_user_recommendations_view(request):
    """
    사용자의 페르소나에 저장된 추천 공고들을 상세 정보와 함께 반환합니다.
    query parameter에서 user_id, persona_id를 받습니다.
    """
    logger.info("사용자 추천 공고 조회 요청")
    try:
        user_id = request.GET.get('user_id')
        persona_id = request.GET.get('persona_id')
        logger.info(f"요청 파라미터 - user_id: {user_id}, persona_id: {persona_id}")
        
        if not user_id:
            error_response = {
                "success": False,
                "message": "user_id가 필요합니다."
            }
            logger.warning(f"user_id 누락, 응답: {error_response}")
            return Response(error_response, status=400)
            
        if not persona_id:
            error_response = {
                "success": False,
                "message": "persona_id가 필요합니다."
            }
            logger.warning(f"persona_id 누락, 응답: {error_response}")
            return Response(error_response, status=400)
        
        # 추천 공고 정보 가져오기
        result = get_user_recommendations(user_id, persona_id)
        logger.info(f"추천 공고 조회 결과: {result}")
        
        if 'error' not in result:
            success_response = {
                "persona_card": result['persona_card'],
                "competency": result['competency'],
                "recommendations": result['recommendations'],
                "total_count": result['total_count']
            }
            logger.info(f"추천 공고 조회 성공, 응답: {success_response}")
            return Response(success_response)
        else:
            error_response = {
                "success": False,
                "message": f"추천 공고 조회 중 오류가 발생했습니다: {result['error']}"
            }
            logger.error(f"추천 공고 조회 오류: {result['error']}, 응답: {error_response}")
            return Response(error_response, status=500)
            
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"사용자 추천 공고 조회 중 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)


@api_view(["GET"])
def get_job_detail_with_recommendation_view(request, job_posting_id):
    """
    특정 공고의 상세 정보와 추천 이유를 반환합니다.
    path parameter에서 job_posting_id를, query parameter에서 user_id, persona_id를 받습니다.
    """
    logger.info(f"공고 상세 정보 조회 요청 - job_posting_id: {job_posting_id}")
    try:
        user_id = request.GET.get('user_id')
        persona_id = request.GET.get('persona_id')
        logger.info(f"요청 파라미터 - user_id: {user_id}, persona_id: {persona_id}")
        
        if not user_id:
            error_response = {
                "success": False,
                "message": "user_id가 필요합니다."
            }
            logger.warning(f"user_id 누락, 응답: {error_response}")
            return Response(error_response, status=400)
            
        if not persona_id:
            error_response = {
                "success": False,
                "message": "persona_id가 필요합니다."
            }
            logger.warning(f"persona_id 누락, 응답: {error_response}")
            return Response(error_response, status=400)
            
        
        # 공고 상세 정보와 추천 이유 가져오기
        result = get_job_detail_with_recommendation(user_id, persona_id, job_posting_id)
        logger.info(f"공고 상세 정보 조회 결과: {result}")
        
        if result['success']:
            success_response = {
                "job_posting": result['job_posting'],
                "recommendation": result['recommendation'],
                "cover_letter_preview": result['cover_letter_preview']
            }
            logger.info(f"공고 상세 정보 조회 성공, 응답: {success_response}")
            return Response(success_response)
        else:
            error_response = {
                "success": False,
                "message": f"공고 상세 정보 조회 중 오류가 발생했습니다: {result['error']}"
            }
            logger.error(f"공고 상세 정보 조회 오류: {result['error']}, 응답: {error_response}")
            return Response(error_response, status=500)
            
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"공고 상세 정보 조회 중 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)


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
    logger.info("페르소나-공고 점수 계산 요청")
    try:
        user_id = request.data.get('user_id')
        persona_id = request.data.get('persona_id')
        logger.info(f"요청 파라미터 - user_id: {user_id}, persona_id: {persona_id}")
        
        if not user_id:
            error_response = {
                "success": False,
                "message": "user_id가 필요합니다."
            }
            logger.warning(f"user_id 누락, 응답: {error_response}")
            return Response(error_response, status=400)
            
        if not persona_id:
            error_response = {
                "success": False,
                "message": "persona_id가 필요합니다."
            }
            logger.warning(f"persona_id 누락, 응답: {error_response}")
            return Response(error_response, status=400)
        
        # 각 공고의 점수 계산
        result = calculate_persona_job_scores(user_id, persona_id)
        logger.info(f"점수 계산 결과: {result}")
        
        if result['success']:
            success_response = {
                "success": True,
                "message": result['message'],
                "persona_data": result['persona_data'],
                "job_scores": result['job_scores'],
                "total_jobs": result['total_jobs']
            }
            logger.info(f"점수 계산 성공, 응답: {success_response}")
            return Response(success_response)
        else:
            error_response = {
                "success": False,
                "message": f"점수 계산 중 오류가 발생했습니다: {result['error']}"
            }
            logger.error(f"점수 계산 오류: {result['error']}, 응답: {error_response}")
            return Response(error_response, status=500)
            
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"점수 계산 중 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)


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
    logger.info("페르소나 데이터로 점수 계산 요청")
    try:
        persona_data = request.data.get('persona_data')
        logger.info(f"받은 persona_data: {persona_data}")
        
        if not persona_data:
            error_response = {
                "success": False,
                "message": "persona_data가 필요합니다."
            }
            logger.warning(f"persona_data 누락, 응답: {error_response}")
            return Response(error_response, status=400)
        
        # 각 공고의 점수 계산
        result = calculate_persona_job_scores_from_data(persona_data)
        logger.info(f"점수 계산 결과: {result}")
        
        if result['success']:
            success_response = {
                "success": True,
                "message": result['message'],
                "persona_data": result['persona_data'],
                "job_scores": result['job_scores'],
                "total_jobs": result['total_jobs']
            }
            logger.info(f"점수 계산 성공, 응답: {success_response}")
            return Response(success_response)
        else:
            error_response = {
                "success": False,
                "message": f"점수 계산 중 오류가 발생했습니다: {result['error']}"
            }
            logger.error(f"점수 계산 오류: {result['error']}, 응답: {error_response}")
            return Response(error_response, status=500)
            
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"점수 계산 중 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)


@api_view(["POST"])
def add_scrap_view(request):
    """
    공고를 스크랩에 추가합니다.
    request body에서 user_id, persona_id, job_posting_id를 받습니다.
    """
    logger.info("📌 공고 스크랩 추가 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 요청 데이터: {request.data}")
    
    try:
        user_id = request.data.get('user_id')
        persona_id = request.data.get('persona_id')
        job_posting_id = request.data.get('job_posting_id')
        
        logger.info(f"📋 파라미터 추출 완료")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        logger.info(f"   💼 job_posting_id: {job_posting_id}")
        
        # 파라미터 검증
        logger.info(f"🔍 파라미터 검증 시작")
        
        if not user_id:
            error_response = {
                "success": False,
                "message": "user_id가 필요합니다."
            }
            logger.warning(f"❌ user_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=400)
            
        if not persona_id:
            error_response = {
                "success": False,
                "message": "persona_id가 필요합니다."
            }
            logger.warning(f"❌ persona_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=400)
            
        if not job_posting_id:
            error_response = {
                "success": False,
                "message": "job_posting_id가 필요합니다."
            }
            logger.warning(f"❌ job_posting_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=400)
        
        logger.info(f"✅ 파라미터 검증 완료")
        
        # 공고 스크랩 추가
        logger.info(f"📤 스크랩 서비스 호출 시작")
        logger.info(f"   🔗 add_job_to_scrap(user_id={user_id}, persona_id={persona_id}, job_posting_id={job_posting_id})")
        
        result = add_job_to_scrap(user_id, persona_id, job_posting_id)
        
        logger.info(f"📥 스크랩 서비스 응답 수신")
        logger.info(f"   📊 결과: {result}")
        logger.info(f"   ✅ 성공 여부: {result.get('success', False)}")
        
        if result['success']:
            logger.info(f"🎉 스크랩 추가 성공")
            logger.info(f"📤 성공 응답 전송: {result}")
            return Response(result, status=201)
        else:
            logger.warning(f"⚠️ 스크랩 추가 실패")
            logger.warning(f"📤 실패 응답 전송: {result}")
            return Response(result, status=400)
            
    except ScrapServiceError as e:
        error_response = {
            "success": False,
            "message": str(e)
        }
        logger.error(f"스크랩 서비스 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=400)
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"스크랩 추가 중 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)


@api_view(["DELETE"])
def remove_scrap_view(request):
    """
    공고를 스크랩에서 제거합니다.
    request body에서 user_id, persona_id, job_posting_id를 받습니다.
    """
    logger.info("🗑️ 공고 스크랩 제거 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 요청 데이터: {request.data}")
    
    try:
        user_id = request.data.get('user_id')
        persona_id = request.data.get('persona_id')
        job_posting_id = request.data.get('job_posting_id')
        
        logger.info(f"📋 파라미터 추출 완료")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        logger.info(f"   💼 job_posting_id: {job_posting_id}")
        
        # 파라미터 검증
        logger.info(f"🔍 파라미터 검증 시작")
        
        if not user_id:
            error_response = {
                "success": False,
                "message": "user_id가 필요합니다."
            }
            logger.warning(f"❌ user_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=400)
            
        if not persona_id:
            error_response = {
                "success": False,
                "message": "persona_id가 필요합니다."
            }
            logger.warning(f"❌ persona_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=400)
            
        if not job_posting_id:
            error_response = {
                "success": False,
                "message": "job_posting_id가 필요합니다."
            }
            logger.warning(f"❌ job_posting_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=400)
        
        logger.info(f"✅ 파라미터 검증 완료")
        
        # 공고 스크랩 제거
        logger.info(f"📤 스크랩 서비스 호출 시작")
        logger.info(f"   🔗 remove_job_from_scrap(user_id={user_id}, persona_id={persona_id}, job_posting_id={job_posting_id})")
        
        result = remove_job_from_scrap(user_id, persona_id, job_posting_id)
        
        logger.info(f"📥 스크랩 서비스 응답 수신")
        logger.info(f"   📊 결과: {result}")
        logger.info(f"   ✅ 성공 여부: {result.get('success', False)}")
        
        if result['success']:
            logger.info(f"스크랩 제거 성공, 응답: {result}")
            return Response(result)
        else:
            logger.warning(f"스크랩 제거 실패, 응답: {result}")
            return Response(result, status=400)
            
    except ScrapServiceError as e:
        error_response = {
            "success": False,
            "message": str(e)
        }
        logger.error(f"스크랩 서비스 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=400)
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"스크랩 제거 중 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)


@api_view(["GET"])
def get_scraped_jobs_view(request):
    """
    스크랩된 공고 목록을 조회합니다.
    query parameter에서 user_id, persona_id를 받습니다.
    """
    logger.info("📋 스크랩된 공고 목록 조회 요청 시작")
    logger.info(f"🔍 요청 메서드: {request.method}")
    logger.info(f"🔍 요청 헤더: {dict(request.headers)}")
    logger.info(f"🔍 쿼리 파라미터: {dict(request.GET)}")
    
    try:
        user_id = request.GET.get('user_id')
        persona_id = request.GET.get('persona_id')
        
        logger.info(f"📋 파라미터 추출 완료")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        
        # 파라미터 검증
        logger.info(f"🔍 파라미터 검증 시작")
        
        if not user_id:
            error_response = {
                "success": False,
                "message": "user_id가 필요합니다."
            }
            logger.warning(f"❌ user_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=400)
            
        if not persona_id:
            error_response = {
                "success": False,
                "message": "persona_id가 필요합니다."
            }
            logger.warning(f"❌ persona_id 누락")
            logger.warning(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=400)
        
        logger.info(f"✅ 파라미터 검증 완료")
        
        # 스크랩된 공고 목록 조회
        logger.info(f"📤 스크랩 서비스 호출 시작")
        logger.info(f"   🔗 get_scraped_jobs(user_id={user_id}, persona_id={persona_id})")
        
        scraped_jobs = get_scraped_jobs(user_id, persona_id)
        
        logger.info(f"📥 스크랩 서비스 응답 수신")
        logger.info(f"   📊 스크랩된 공고 수: {len(scraped_jobs) if scraped_jobs else 0}")
        logger.info(f"   📋 스크랩된 공고 목록: {scraped_jobs}")
        
        # 페르소나 카드 데이터 조회
        logger.info(f"📤 페르소나 데이터 조회 시작")
        from core.services.firebase_personas import get_persona_document
        from core.utils import create_persona_card
        from django.conf import settings
        
        db = getattr(settings, "FIREBASE_DB", None)
        if not db:
            error_response = {
                "success": False,
                "message": "Firestore 클라이언트를 찾을 수 없습니다."
            }
            logger.error(f"❌ Firestore 클라이언트 없음")
            logger.error(f"📤 오류 응답: {error_response}")
            return Response(error_response, status=500)
        
        logger.info(f"🔗 Firestore 클라이언트 확인 완료")
        logger.info(f"   🔗 get_persona_document(user_id={user_id}, persona_id={persona_id})")
        
        persona_data = get_persona_document(user_id=user_id, persona_id=persona_id, db=db)
        logger.info(f"📥 페르소나 데이터 수신 완료")
        logger.info(f"   📊 페르소나 데이터: {persona_data}")
        
        logger.info(f"🔧 페르소나 카드 생성 시작")
        persona_card = create_persona_card(persona_data)
        logger.info(f"✅ 페르소나 카드 생성 완료")
        logger.info(f"   📋 페르소나 카드: {persona_card}")
        
        success_response = {
            "success": True,
            "scraped_jobs": scraped_jobs,
            "total_count": len(scraped_jobs),
            "persona_card": persona_card
        }
        logger.info(f"스크랩된 공고 목록 조회 성공, 응답: {success_response}")
        return Response(success_response)
            
    except Exception as e:
        error_response = {
            "success": False,
            "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        }
        logger.error(f"스크랩된 공고 목록 조회 중 오류: {str(e)}, 응답: {error_response}")
        return Response(error_response, status=500)