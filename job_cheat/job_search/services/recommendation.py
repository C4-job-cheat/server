import os
from firebase_admin import firestore


def get_user_recommendations(user_id: str, persona_id: str) -> dict:
    """
    사용자의 페르소나에 저장된 추천 공고들을 가져와서 상세 정보와 함께 반환합니다.
    
    Args:
        user_id (str): 사용자 ID
        persona_id (str): 페르소나 ID
        
    Returns:
        dict: 추천 공고들의 상세 정보
    """
    try:
        db = firestore.client()
        
        # 1. recommendations 컬렉션에서 추천 데이터 가져오기
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
                'success': True,
                'message': '저장된 추천 공고가 없습니다.',
                'recommendations': [],
                'total_count': 0
            }
        
        # 2. 각 추천 공고의 상세 정보를 job_postings에서 가져오기
        detailed_recommendations = []
        for rec in recommendations:
            job_posting_id = rec['job_posting_id']
            
            # job_postings 컬렉션에서 공고 상세 정보 가져오기
            job_doc = db.collection('job_postings').document(job_posting_id).get()
            
            if job_doc.exists:
                job_data = job_doc.to_dict()
                
                # 필요한 정보만 추출
                detailed_recommendation = {
                    'recommendation_id': rec['recommendation_id'],
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
                    'recommendation_id': rec['recommendation_id'],
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
        
        # 3. 추천 점수 순으로 정렬 (높은 점수부터)
        detailed_recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return {
            'success': True,
            'message': f'{len(detailed_recommendations)}개의 추천 공고를 가져왔습니다.',
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
