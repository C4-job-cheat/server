def create_persona_card(persona_data: dict) -> dict:
    """
    페르소나 데이터에서 persona_card 정보를 추출합니다.
    
    Args:
        persona_data (dict): 페르소나 데이터
        
    Returns:
        dict: persona_card 정보
    """
    education_info = persona_data.get('education', {})
    
    return {
        'school': education_info.get('school', ''),
        'major': education_info.get('major', ''),
        'job_category': persona_data.get('job_category', ''),
        'job_title': persona_data.get('job_title', ''),
        'skills': persona_data.get('skills', [])
    }
