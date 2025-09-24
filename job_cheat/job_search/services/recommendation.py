import os
import openai
from firebase_admin import firestore
from core.utils import create_persona_card


def create_competency_info(persona_data: dict) -> dict:
    """
    페르소나 데이터에서 competency 정보를 추출합니다.
    scores와 reasons를 하나로 합쳐서 반환합니다.
    
    Args:
        persona_data (dict): 페르소나 데이터
        
    Returns:
        dict: competency 정보
    """
    competency_scores = persona_data.get('competency_scores', {})
    competency_reasons = persona_data.get('competency_reasons', {})
    
    # scores와 reasons를 하나로 합치기
    competency_details = {}
    for key, score in competency_scores.items():
        reason = competency_reasons.get(key, '')
        competency_details[key] = {
            'score': score,
            'reason': reason
        }
    
    return {
        'details': competency_details,
        'ai_analysis_summary': persona_data.get('ai_analysis_summary', '')
    }


def get_user_recommendations(user_id: str, persona_id: str) -> dict:
    """
    사용자의 페르소나에 저장된 추천 공고들을 가져와서 상세 정보와 함께 반환합니다.
    페르소나 정보도 함께 반환합니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        
    Returns:
        dict: 추천 공고들의 상세 정보와 페르소나 정보
    """
    try:
        db = firestore.client()
        
        # 1. 페르소나 정보 가져오기
        persona_doc = db.collection('users').document(user_id).collection('personas').document(persona_id).get()
        
        if not persona_doc.exists:
            return {
                'success': False,
                'error': '페르소나를 찾을 수 없습니다.',
                'recommendations': [],
                'total_count': 0
            }
        
        persona_data = persona_doc.to_dict()
        
        # 2. 페르소나 정보 구성 (util 함수 사용)
        persona_card = create_persona_card(persona_data)
        competency = create_competency_info(persona_data)
        
        # 3. recommendations 컬렉션에서 추천 데이터 가져오기
        recommendations_ref = db.collection('users').document(user_id).collection('personas').document(persona_id).collection('recommendations')
        recommendations_docs = recommendations_ref.stream()
        
        recommendations = []
        for doc in recommendations_docs:
            recommendation_data = doc.to_dict()
            recommendations.append({
                'recommendation_id': doc.id,
                'job_posting_id': recommendation_data.get('job_posting_id'),
                'recommendation_score': recommendation_data.get('recommendation_score')
            })
        
        if not recommendations:
            return {
                'persona_card': persona_card,
                'competency': competency,
                'recommendations': [],
                'total_count': 0
            }
        
        # 4. 각 추천 공고의 상세 정보를 job_postings에서 가져오기
        detailed_recommendations = []
        for rec in recommendations:
            job_posting_id = rec['job_posting_id']
            
            # job_postings 컬렉션에서 공고 상세 정보 가져오기
            job_doc = db.collection('job_postings').document(job_posting_id).get()
            
            if job_doc.exists:
                job_data = job_doc.to_dict()
                
                # 필요한 정보만 추출
                detailed_recommendation = {
                    'job_posting_id': job_posting_id,
                    'recommendation_score': rec['recommendation_score'],
                    'company_name': job_data.get('company_name', ''),
                    'company_logo': job_data.get('company_logo', ''),
                    'job_category': job_data.get('job_category', ''),
                    'job_title': job_data.get('job_title', ''),
                    'location': job_data.get('work_conditions', {}).get('location', ''),
                    'application_deadline': job_data.get('application_deadline', '')
                }
                
                detailed_recommendations.append(detailed_recommendation)
            else:
                # job_posting이 존재하지 않는 경우 (삭제된 공고)
                detailed_recommendation = {
                    'job_posting_id': job_posting_id,
                    'recommendation_score': rec['recommendation_score'],
                    'company_name': '',
                    'company_logo': '',
                    'job_category': '',
                    'job_title': '',
                    'location': '',
                    'application_deadline': '',
                    'error': '공고 정보를 찾을 수 없습니다.'
                }
                
                detailed_recommendations.append(detailed_recommendation)
        
        # 5. 추천 점수 순으로 정렬 (높은 점수부터)
        detailed_recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return {
            'persona_card': persona_card,
            'competency': competency,
            'recommendations': detailed_recommendations,
            'total_count': len(detailed_recommendations)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'recommendations': [],
            'total_count': 0
        }


def get_job_detail_with_recommendation(user_id: str, persona_id: str, job_posting_id: str) -> dict:
    """
    특정 공고의 상세 정보와 추천 이유를 반환합니다.
    reason_summary가 비어있으면 LLM으로 생성합니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        job_posting_id (str): 공고 ID
        
    Returns:
        dict: 공고 상세 정보와 추천 이유
    """
    try:
        db = firestore.client()
        
        # 1. 페르소나 정보 가져오기
        persona_doc = db.collection('users').document(user_id).collection('personas').document(persona_id).get()
        
        if not persona_doc.exists:
            return {
                'success': False,
                'error': '페르소나를 찾을 수 없습니다.'
            }
        
        persona_data = persona_doc.to_dict()
        
        # 2. 공고 상세 정보 가져오기
        job_doc = db.collection('job_postings').document(job_posting_id).get()
        
        if not job_doc.exists:
            return {
                'success': False,
                'error': '공고를 찾을 수 없습니다.'
            }
        
        job_data = job_doc.to_dict()
        
        # 3. 추천 정보 가져오기
        recommendations_ref = db.collection('users').document(user_id).collection('personas').document(persona_id).collection('recommendations')
        recommendations_query = recommendations_ref.where('job_posting_id', '==', job_posting_id).limit(1)
        recommendations_docs = list(recommendations_query.stream())
        
        if not recommendations_docs:
            return {
                'success': False,
                'error': '해당 공고에 대한 추천 정보를 찾을 수 없습니다.'
            }
        
        recommendation_doc = recommendations_docs[0]
        recommendation_data = recommendation_doc.to_dict()
        recommendation_id = recommendation_doc.id
        
        # 4. reason_summary 확인 및 생성
        reason_summary = recommendation_data.get('reason_summary', {})
        match_points = reason_summary.get('match_points', [])
        improvement_points = reason_summary.get('improvement_points', [])
        growth_suggestions = reason_summary.get('growth_suggestions', [])
        
        # reason_summary가 비어있으면 LLM으로 생성
        if not match_points and not improvement_points and not growth_suggestions:
            llm_result = generate_reason_summary_with_llm(persona_data, job_data)
            
            if llm_result['success']:
                # Firestore에 저장
                updated_reason_summary = {
                    'match_points': llm_result['match_points'],
                    'improvement_points': llm_result['improvement_points'],
                    'growth_suggestions': llm_result['growth_suggestions']
                }
                
                # recommendation 문서 업데이트
                recommendations_ref.document(recommendation_id).update({
                    'reason_summary': updated_reason_summary
                })
                
                match_points = llm_result['match_points']
                improvement_points = llm_result['improvement_points']
                growth_suggestions = llm_result['growth_suggestions']
            else:
                return {
                    'success': False,
                    'error': f'추천 이유 생성 중 오류가 발생했습니다: {llm_result["error"]}'
                }
        
        # 5. 결과 반환
        return {
            'success': True,
            'job_posting': job_data,
            'recommendation': {
                'recommendation_score': recommendation_data.get('recommendation_score'),
                'reason_summary': {
                    'match_points': match_points,
                    'improvement_points': improvement_points,
                    'growth_suggestions': growth_suggestions
                }
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_reason_summary_with_llm(persona_data: dict, job_data: dict) -> dict:
    """
    LLM을 사용하여 추천 이유를 생성합니다.
    
    Args:
        persona_data (dict): 페르소나 데이터
        job_data (dict): 공고 데이터
        
    Returns:
        dict: 생성된 추천 이유
    """
    try:
        # OpenAI 클라이언트 설정
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # 프롬프트 구성
        prompt = f"""
다음은 사용자 페르소나 정보와 채용 공고 정보입니다. 
이 사용자가 이 공고에 적합한 이유를 분석하여 다음 3가지 관점에서 각각 3개의 항목으로 정리해주세요:

**사용자 페르소나 정보:**
- 직무: {persona_data.get('job_category', '')} / {persona_data.get('job_title', '')}
- 학력: {persona_data.get('education', {}).get('school', '')} {persona_data.get('education', {}).get('major', '')}
- 보유 기술: {', '.join(persona_data.get('skills', []))}
- 역량 점수: {persona_data.get('competency_scores', {})}

**채용 공고 정보:**
- 회사: {job_data.get('company_name', '')}
- 직무: {job_data.get('job_category', '')} / {job_data.get('job_title', '')}
- 필수 요구사항: {', '.join(job_data.get('requirements', []))}
- 우대사항: {', '.join(job_data.get('preferred', []))}
- 업무 설명: {job_data.get('job_description', '')}

다음 JSON 형식으로 응답해주세요:
{{
    "match_points": ["일치하는 요소 1", "일치하는 요소 2", "일치하는 요소 3"],
    "improvement_points": ["보완이 필요한 부분 1", "보완이 필요한 부분 2", "보완이 필요한 부분 3"],
    "growth_suggestions": ["성장 방향 제안 1", "성장 방향 제안 2", "성장 방향 제안 3"]
}}
"""
        
        # GPT 모델 호출 (새로운 방식)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "당신은 채용 전문가입니다. 사용자와 공고의 매칭도를 정확하게 분석해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        # 응답 파싱
        content = response.choices[0].message.content.strip()
        
        # JSON 파싱 시도
        import json
        try:
            result = json.loads(content)
            return {
                'success': True,
                'match_points': result.get('match_points', []),
                'improvement_points': result.get('improvement_points', []),
                'growth_suggestions': result.get('growth_suggestions', [])
            }
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본값 반환
            return {
                'success': True,
                'match_points': ["페르소나와 공고 요구사항이 일치합니다."],
                'improvement_points': ["추가적인 역량 개발이 필요합니다."],
                'growth_suggestions': ["지속적인 학습과 성장을 권장합니다."]
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
