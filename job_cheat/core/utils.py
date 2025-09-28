def create_persona_card(persona_data: dict) -> dict:
    """
    페르소나 데이터에서 persona_card 정보를 추출합니다.
    
    Args:
        persona_data (dict): 페르소나 데이터
        
    Returns:
        dict: persona_card 정보
    """
    return {
        'school': persona_data.get('school_name', ''),
        'major': persona_data.get('major', ''),
        'job_category': persona_data.get('job_category', ''),
        'job_title': persona_data.get('job_role', ''),
        'skills': persona_data.get('skills', []),
        'certifications': persona_data.get('certifications', [])
    }
