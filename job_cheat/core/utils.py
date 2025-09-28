def create_persona_card(persona_data: dict) -> dict:
    """
    페르소나 데이터에서 persona_card 정보를 추출합니다.
    
    Args:
        persona_data (dict): 페르소나 데이터
        
    Returns:
        dict: persona_card 정보
    """
    # skills와 certifications를 합쳐서 skills로 반환
    skills = list(persona_data.get('skills', []))
    certifications = persona_data.get('certifications', [])
    if certifications:
        skills.extend(certifications)
    
    return {
        'school': persona_data.get('school_name', ''),
        'major': persona_data.get('major', ''),
        'job_category': persona_data.get('job_category', ''),
        'job_title': persona_data.get('job_role', ''),
        'skills': skills
    }
