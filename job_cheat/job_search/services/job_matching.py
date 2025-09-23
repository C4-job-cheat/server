import os
from firebase_admin import firestore
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone


def preprocess_persona_to_text(persona_data: dict) -> str:
    """
    복잡한 페르소나 데이터 딕셔너리에서 필요한 정보만 추출하여
    벡터화를 위한 하나의 평문 텍스트로 변환합니다.

    Args:
        persona_data (dict): 사용자 페르소나 데이터.

    Returns:
        str: 전처리된 평문 텍스트.
    """
    # education 맵에서 안전하게 데이터 추출
    education_info = persona_data.get('education', {})
    education_text = f"{education_info.get('school', '')} {education_info.get('major', '')} {education_info.get('degree', '')}"

    # skills 배열을 쉼표로 구분된 문자열로 변환
    skills_text = ', '.join(persona_data.get('skills', []))

    # competency_reasons 맵에서 value(설명)만 추출하여 하나의 문자열로 합침
    competency_reasons_map = persona_data.get('competency_reasons', {})
    reasons_text = ' '.join(competency_reasons_map.values())

    # f-string을 사용하여 전체 텍스트를 최종적으로 조합
    plain_text = f"""
직군 및 직무: {persona_data.get('job_category', '')}, {persona_data.get('job_title', '')}
학력: {education_text}
보유 기술: {skills_text}
역량 분석 상세: {reasons_text}
AI 종합 분석: {persona_data.get('ai_analysis_summary', '')}
"""
    return plain_text.strip()


def get_persona_from_firestore(user_id: str, persona_id: str) -> dict:
    """
    Firestore에서 페르소나 데이터를 가져옵니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        
    Returns:
        dict: 페르소나 데이터
    """
    db = firestore.client()
    
    doc_ref = db.collection('users').document(user_id).collection('personas').document(persona_id)
    
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()
    else:
        raise ValueError(f"사용자 {user_id}의 페르소나 {persona_id} 데이터를 찾을 수 없습니다.")


def find_matching_jobs(persona_data: dict, top_k: int = 5) -> list:
    """
    페르소나 데이터를 기반으로 유사한 공고를 찾습니다.
    
    Args:
        persona_data (dict): 사용자 페르소나 데이터
        top_k (int): 반환할 상위 공고 수 (기본값: 5)
        
    Returns:
        list: 매칭된 공고 리스트 (유사도 점수와 메타데이터 포함)
        
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    # 1. 페르소나 데이터를 평문 텍스트로 변환
    persona_text = preprocess_persona_to_text(persona_data)
    
    # 2. SentenceTransformer 모델 로드 및 벡터화
    model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    persona_vector = model.encode(persona_text).tolist()
    
    # 3. Pinecone 클라이언트 초기화
    pinecone = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index = pinecone.Index('job-postings')
    
    # 4. 필터 조건 설정 (페르소나의 직군/직무 기준)
    filter_conditions = {
        "category": {"$eq": persona_data.get('job_category', '')}
    }
    
    # job_title이 있으면 추가 필터링
    if persona_data.get('job_title'):
        filter_conditions["title"] = {"$eq": persona_data.get('job_title')}
    
    # 5. Pinecone에서 유사도 검색
    search_results = index.query(
        vector=persona_vector,
        filter=filter_conditions,
        top_k=top_k,
        include_metadata=True
    )
    
    # 6. 결과 포맷팅
    matching_jobs = []
    for match in search_results['matches']:
        matching_jobs.append({
            'firestore_id': match['metadata']['firestore_id'],
            'similarity_score': round(match['score'], 4),
        })
    
    return matching_jobs


def save_recommendations_to_firestore(user_id: str, persona_id: str, matching_jobs: list, min_score: float = 0.6) -> dict:
    """
    유사도가 min_score 이상인 공고들을 Firestore에 추천 데이터로 저장합니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        matching_jobs (list): 매칭된 공고 리스트
        min_score (float): 최소 유사도 점수 (기본값: 0.6)
        
    Returns:
        dict: 저장 결과 정보
    """
    db = firestore.client()
    
    # 유사도가 min_score 이상인 공고들만 필터링
    filtered_jobs = [job for job in matching_jobs if job['similarity_score'] >= min_score]
    
    if not filtered_jobs:
        return {
            'success': True,
            'message': f'유사도 {min_score} 이상인 공고가 없어서 저장할 데이터가 없습니다.',
            'saved_count': 0
        }
    
    # 기존 추천 데이터 삭제 (새로운 추천으로 교체)
    recommendations_ref = db.collection('users').document(user_id).collection('personas').document(persona_id).collection('recommendations')
    
    # 기존 문서들 삭제
    existing_docs = recommendations_ref.stream()
    for doc in existing_docs:
        doc.reference.delete()
    
    # 새로운 추천 데이터 저장
    saved_count = 0
    for job in filtered_jobs:
        recommendation_data = {
            'job_posting_id': job['firestore_id'],
            'recommendation_score': round(job['similarity_score'] * 100),
            'reason_summary': {
                'match_points': [],
                'improvement_points': [],
                'growth_suggestions': []
            }
        }
        
        # 새 문서 ID 생성 (자동 생성)
        recommendations_ref.add(recommendation_data)
        saved_count += 1
    
    return {
        'success': True,
        'message': f'{saved_count}개의 추천 공고를 저장했습니다.',
        'saved_count': saved_count,
        'min_score': min_score
    }


def get_persona_and_match_jobs(user_id: str, persona_id: str, top_k: int = 5) -> dict:
    """
    사용자 ID와 페르소나 ID로 페르소나를 가져와서 매칭된 공고를 반환합니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        top_k (int): 반환할 상위 공고 수
        
    Returns:
        dict: 페르소나 정보와 매칭된 공고 리스트
        
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        # 1. Firestore에서 페르소나 데이터 가져오기
        persona_data = get_persona_from_firestore(user_id, persona_id)
        
        # 2. 매칭된 공고 찾기
        matching_jobs = find_matching_jobs(persona_data, top_k)
        
        return {
            'success': True,
            'persona_data': {
                'job_category': persona_data.get('job_category'),
                'job_title': persona_data.get('job_title'),
                'skills': persona_data.get('skills', [])
            },
            'matching_jobs': matching_jobs,
            'total_matches': len(matching_jobs)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'matching_jobs': [],
            'total_matches': 0
        }


def save_persona_recommendations(user_id: str, persona_id: str) -> dict:
    """
    사용자 ID와 페르소나 ID로 페르소나를 가져와서 추천 데이터를 저장합니다.
    min_score=0.6 이상인 모든 공고를 저장합니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        
    Returns:
        dict: 추천 저장 결과
    """
    try:
        # 1. Firestore에서 페르소나 데이터 가져오기
        persona_data = get_persona_from_firestore(user_id, persona_id)
        
        # 2. 매칭된 공고 찾기 (충분히 많은 수로 설정)
        matching_jobs = find_matching_jobs(persona_data, top_k=50)  # 충분히 많은 수로 설정
        
        # 3. 추천 데이터 저장 (min_score=0.6으로 고정)
        if matching_jobs:
            recommendation_result = save_recommendations_to_firestore(user_id, persona_id, matching_jobs, min_score=0.6)
            return recommendation_result
        else:
            return {
                'success': True,
                'message': '매칭된 공고가 없어서 저장할 데이터가 없습니다.',
                'saved_count': 0
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'saved_count': 0
        }
