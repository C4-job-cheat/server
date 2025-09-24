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

    # competency_reasons 맵에서 value(설명)만 추출하여 하나의 문자열로 합침
    competency_reasons_map = persona_data.get('competency_reasons', {})
    reasons_text = ' '.join(competency_reasons_map.values())

    # f-string을 사용하여 전체 텍스트를 최종적으로 조합
    plain_text = f"""
직군 및 직무: {persona_data.get('job_category', '')}, {persona_data.get('job_title', '')}
학력: {education_text}
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


def find_matching_jobs(persona_data: dict) -> list:
    """
    페르소나 데이터를 기반으로 유사한 공고를 찾습니다. 
    
    Args:
        persona_data (dict): 사용자 페르소나 데이터
        
    Returns:
        list: 매칭된 공고 리스트 (유사도 점수와 메타데이터 포함)
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
        top_k=50,
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


def get_job_requirements_and_preferred(firestore_id: str) -> dict:
    """
    Firestore에서 공고의 requirements와 preferred를 가져옵니다.
    
    Args:
        firestore_id (str): 공고의 Firestore ID
        
    Returns:
        dict: requirements와 preferred 리스트
    """
    db = firestore.client()
    doc_ref = db.collection('job_postings').document(firestore_id)
    doc = doc_ref.get()
    
    if doc.exists:
        job_data = doc.to_dict()
        return {
            'requirements': job_data.get('requirements', []),
            'preferred': job_data.get('preferred', [])
        }
    else:
        return {
            'requirements': [],
            'preferred': []
        }


def calculate_skill_score(persona_skills: list, job_requirements: list, job_preferred: list) -> float:
    """
    페르소나의 skills와 공고의 requirements, preferred를 비교하여 skill 점수를 계산합니다.
    
    Args:
        persona_skills (list): 페르소나의 skills 리스트
        job_requirements (list): 공고의 requirements 리스트
        job_preferred (list): 공고의 preferred 리스트
        
    Returns:
        float: skill 점수 (0.0 ~ 1.0)
    """
    if not persona_skills:
        return 0.0
    
    # Requirements 점수 계산 (0.0 ~ 1.0 사이의 기본 점수)
    requirements_matches = 0
    for skill in persona_skills:
        for req in job_requirements:
            if skill.lower() in req.lower() or req.lower() in skill.lower():
                requirements_matches += 1
                break
    requirements_score = requirements_matches / len(job_requirements) if job_requirements else 0.0

    # Preferred 점수 계산 (가산점 계산용)
    preferred_matches = 0
    for skill in persona_skills:
        for pref in job_preferred:
            if skill.lower() in pref.lower() or pref.lower() in skill.lower():
                preferred_matches += 1
                break
    preferred_score = preferred_matches / len(job_preferred) if job_preferred else 0.0

    # 최종 스킬 점수 계산 (가산점 적용)
    # 우대사항의 영향력을 결정하는 가중치 (최대 보너스 점수)
    BONUS_WEIGHT = 0.2

    # 보너스 점수 계산
    bonus_score = preferred_score * BONUS_WEIGHT

    # 최종 스킬 점수 
    final_skill_score = requirements_score + bonus_score

    # 스킬 점수 정규화
    MAX_THEORETICAL_SKILL_SCORE = 1.0 + BONUS_WEIGHT
    normalized_skill_score = final_skill_score / MAX_THEORETICAL_SKILL_SCORE
    
    return round(normalized_skill_score, 4)


def calculate_final_score(similarity_score: float, skill_score: float) -> float:
    """
    유사도 점수와 skill 점수를 가중치를 적용하여 최종 점수를 계산합니다.
    
    Args:
        similarity_score (float): 유사도 점수
        skill_score (float): skill 점수
        
    Returns:
        float: 최종 점수
    """
    # 가중치 적용: 유사도 0.65, skill 0.35
    final_score = (similarity_score * 0.65) + (skill_score * 0.35)
    return round(final_score, 4)


def save_persona_recommendations_score(user_id: str, persona_id: str) -> dict:
    """
    사용자 ID와 페르소나 ID로 페르소나를 가져와서 skill 점수를 포함한 추천 데이터를 저장합니다.
    유사도 점수가 기준 이상인 공고들만 스킬 점수를 계산하고, 최종 점수가 기준 이상인 공고만 저장합니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        
    Returns:
        dict: 추천 저장 결과
    """
    try:
        # 유사도 점수 기준 설정 (이 기준을 통과한 공고들만 스킬 점수 계산)
        min_similarity_score = 0.5
        # 최종 점수 기준 설정
        min_final_score = 0.6
        
        # 1. Firestore에서 페르소나 데이터 가져오기
        persona_data = get_persona_from_firestore(user_id, persona_id)
        persona_skills = persona_data.get('skills', [])
        
        # 2. 매칭된 공고 찾기
        matching_jobs = find_matching_jobs(persona_data)
        
        if not matching_jobs:
            return {
                'success': True,
                'message': '매칭된 공고가 없어서 저장할 데이터가 없습니다.',
                'saved_count': 0
            }
        
        # 3. 유사도 점수 기준을 통과한 공고들만 필터링
        similarity_filtered_jobs = [job for job in matching_jobs if job['similarity_score'] >= min_similarity_score]
        
        if not similarity_filtered_jobs:
            return {
                'success': True,
                'message': f'유사도 점수 {min_similarity_score} 이상인 공고가 없어서 저장할 데이터가 없습니다.',
                'saved_count': 0
            }
        
        # 4. 유사도 기준을 통과한 공고들에 대해서만 skill 점수와 최종 점수 계산
        enhanced_jobs = []
        for job in similarity_filtered_jobs:
            # 공고의 requirements와 preferred 가져오기
            job_details = get_job_requirements_and_preferred(job['firestore_id'])
            
            # skill 점수 계산
            skill_score = calculate_skill_score(
                persona_skills,
                job_details['requirements'],
                job_details['preferred']
            )
            
            # 최종 점수 계산
            final_score = calculate_final_score(job['similarity_score'], skill_score)
            
            enhanced_jobs.append({
                'firestore_id': job['firestore_id'],
                'similarity_score': job['similarity_score'],
                'skill_score': skill_score,
                'final_score': final_score
            })
        
        # 5. 최종 점수 min_final_score 이상인 공고만 필터링
        filtered_jobs = [job for job in enhanced_jobs if job['final_score'] >= min_final_score]
        
        if not filtered_jobs:
            return {
                'success': True,
                'message': f'최종 점수 {min_final_score} 이상인 공고가 없어서 저장할 데이터가 없습니다.',
                'saved_count': 0
            }
        
        # 5. Firestore에 추천 데이터 저장
        db = firestore.client()
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
                'recommendation_score': round(job['final_score'] * 100),
                'reason_summary': {
                    'match_points': [],
                    'improvement_points': [],
                    'growth_suggestions': []
                }
            }
            
            recommendations_ref.add(recommendation_data)
            saved_count += 1
        
        return {
            'success': True,
            'message': f'{saved_count}개의 추천 공고를 저장했습니다.',
            'saved_count': saved_count,
            'min_final_score': min_final_score
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'saved_count': 0
        }


def calculate_persona_job_scores(user_id: str, persona_id: str) -> dict:
    """
    사용자 ID와 페르소나 ID로 페르소나를 가져와서 각 공고의 최종 점수를 계산하여 반환합니다.
    유사도 점수가 기준 이상인 공고들만 스킬 점수를 계산합니다.
    테스트용으로 모든 공고의 점수를 출력합니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        
    Returns:
        dict: 각 공고의 점수 계산 결과

    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        # 유사도 점수 기준 설정 (이 기준을 통과한 공고들만 스킬 점수 계산)
        min_similarity_score = 0.5
        
        # 1. Firestore에서 페르소나 데이터 가져오기
        persona_data = get_persona_from_firestore(user_id, persona_id)
        persona_skills = persona_data.get('skills', [])
        
        # 2. 매칭된 공고 찾기
        matching_jobs = find_matching_jobs(persona_data)
        
        if not matching_jobs:
            return {
                'success': True,
                'message': '매칭된 공고가 없습니다.',
                'job_scores': [],
                'total_jobs': 0
            }
        
        # 3. 유사도 점수 기준을 통과한 공고들만 필터링
        similarity_filtered_jobs = [job for job in matching_jobs if job['similarity_score'] >= min_similarity_score]
        
        if not similarity_filtered_jobs:
            return {
                'success': True,
                'message': f'유사도 점수 {min_similarity_score} 이상인 공고가 없습니다.',
                'job_scores': [],
                'total_jobs': 0
            }
        
        # 4. 유사도 기준을 통과한 공고들에 대해서만 skill 점수와 최종 점수 계산
        job_scores = []
        for job in similarity_filtered_jobs:
            # 공고의 requirements와 preferred 가져오기
            job_details = get_job_requirements_and_preferred(job['firestore_id'])
            
            # skill 점수 계산
            skill_score = calculate_skill_score(
                persona_skills,
                job_details['requirements'],
                job_details['preferred']
            )
            
            # 최종 점수 계산
            final_score = calculate_final_score(job['similarity_score'], skill_score)
            
            job_scores.append({
                'firestore_id': job['firestore_id'],
                'similarity_score': job['similarity_score'],
                'skill_score': skill_score,
                'final_score': final_score,
                'requirements': job_details['requirements'],
                'preferred': job_details['preferred'],
                'persona_skills': persona_skills
            })
        
        # 5. 최종 점수 순으로 정렬
        job_scores.sort(key=lambda x: x['final_score'], reverse=True)
        
        return {
            'success': True,
            'message': f'{len(job_scores)}개 공고의 점수를 계산했습니다.',
            'job_scores': job_scores,
            'total_jobs': len(job_scores),
            'persona_data': {
                'job_category': persona_data.get('job_category'),
                'job_title': persona_data.get('job_title'),
                'skills': persona_skills
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'job_scores': [],
            'total_jobs': 0
        }


def calculate_persona_job_scores_from_data(persona_data: dict) -> dict:
    """
    페르소나 데이터를 직접 받아서 각 공고의 최종 점수를 계산하여 반환합니다.
    유사도 점수가 기준 이상인 공고들만 스킬 점수를 계산합니다.
    테스트용으로 모든 공고의 점수를 출력합니다.
    
    Args:
        persona_data (dict): 페르소나 데이터
        
    Returns:
        dict: 각 공고의 점수 계산 결과
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    try:
        # 유사도 점수 기준 설정 (이 기준을 통과한 공고들만 스킬 점수 계산)
        min_similarity_score = 0.5
        
        persona_skills = persona_data.get('skills', [])
        
        # 1. 매칭된 공고 찾기
        matching_jobs = find_matching_jobs(persona_data)
        
        if not matching_jobs:
            return {
                'success': True,
                'message': '매칭된 공고가 없습니다.',
                'job_scores': [],
                'total_jobs': 0
            }
        
        # 2. 유사도 점수 기준을 통과한 공고들만 필터링
        similarity_filtered_jobs = [job for job in matching_jobs if job['similarity_score'] >= min_similarity_score]
        
        if not similarity_filtered_jobs:
            return {
                'success': True,
                'message': f'유사도 점수 {min_similarity_score} 이상인 공고가 없습니다.',
                'job_scores': [],
                'total_jobs': 0
            }
        
        # 3. 유사도 기준을 통과한 공고들에 대해서만 skill 점수와 최종 점수 계산
        job_scores = []
        for job in similarity_filtered_jobs:
            # 공고의 requirements와 preferred 가져오기
            job_details = get_job_requirements_and_preferred(job['firestore_id'])
            
            # skill 점수 계산
            skill_score = calculate_skill_score(
                persona_skills,
                job_details['requirements'],
                job_details['preferred']
            )
            
            # 최종 점수 계산
            final_score = calculate_final_score(job['similarity_score'], skill_score)
            
            job_scores.append({
                'firestore_id': job['firestore_id'],
                'similarity_score': job['similarity_score'],
                'skill_score': skill_score,
                'final_score': final_score,
                'requirements': job_details['requirements'],
                'preferred': job_details['preferred'],
                'persona_skills': persona_skills
            })
        
        # 4. 최종 점수 순으로 정렬
        job_scores.sort(key=lambda x: x['final_score'], reverse=True)
        
        return {
            'success': True,
            'message': f'{len(job_scores)}개 공고의 점수를 계산했습니다.',
            'job_scores': job_scores,
            'total_jobs': len(job_scores),
            'persona_data': {
                'job_category': persona_data.get('job_category'),
                'job_title': persona_data.get('job_title'),
                'skills': persona_skills
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'job_scores': [],
            'total_jobs': 0
        }
