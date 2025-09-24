import os
from firebase_admin import firestore
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone

# --------------------------------------------------------------------------
# 0. Firestore에 단일 공고 추가 (데이터 세팅 및 관리자용)
# --------------------------------------------------------------------------
def add_job_to_firestore(job_data: dict) -> str:
    """
    주어진 공고 데이터를 Firestore 'job_postings' 컬렉션에 추가합니다.
    Args:
        job_data (dict): 저장할 공고 데이터.
    Returns:
        str: 생성된 Firestore 문서의 ID.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    db = firestore.client()
    collection_ref = db.collection('job_postings')
    update_time, doc_ref = collection_ref.add(job_data)
    
    print(f"Firestore에 문서 추가 완료. ID: {doc_ref.id}")
    return doc_ref.id

# --------------------------------------------------------------------------
# 1. Firestore에서 모든 공고 불러오기
# --------------------------------------------------------------------------
def get_all_jobs_from_firestore() -> list[tuple[str, dict]]:
    """
    Firestore 'job_postings' 컬렉션의 모든 문서를 가져옵니다.
    Returns:
        list[tuple[str, dict]]: (문서ID, 문서 데이터 딕셔너리)의 리스트.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    db = firestore.client()
    collection_ref = db.collection('job_postings')
    docs = collection_ref.stream()
    
    job_list = [(doc.id, doc.to_dict()) for doc in docs]
    
    print(f"Firestore에서 {len(job_list)}개의 공고를 불러왔습니다.")
    return job_list

# --------------------------------------------------------------------------
# 2. 공고 데이터를 평문 텍스트로 변환
# --------------------------------------------------------------------------
def preprocess_job_to_text(job_data: dict) -> str:
    """
    공고 데이터 딕셔너리를 벡터화를 위한 평문 텍스트로 변환합니다.
    Args:
        job_data (dict): Firestore에서 가져온 공고 데이터.
    Returns:
        str: 전처리된 평문 텍스트.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    #requirements = '; '.join(job_data.get('requirements', []))
    #preferred = '; '.join(job_data.get('preferred', []))
    required_qualifications = '; '.join(job_data.get('required_qualifications', []))
    preferred_qualifications = '; '.join(job_data.get('preferred_qualifications', []))
    ideal_candidate = '; '.join(job_data.get('ideal_candidate', []))

    plain_text = f"""
제목: {job_data.get('title', '')}
업무 내용: {job_data.get('job_description', '')}
필수 자격: {required_qualifications}
우대 자격: {preferred_qualifications}
인재상: {ideal_candidate}
"""
#필수 요구사항: {requirements}
#우대사항: {preferred}
    return plain_text.strip()

# --------------------------------------------------------------------------
# 3 & 4. 벡터화하여 Pinecone에 저장 (메인 파이프라인 함수)
# --------------------------------------------------------------------------
def vectorize_and_upsert_to_pinecone(job_list: list[tuple[str, dict]]):
    """
    공고 리스트를 받아 벡터화한 후 Pinecone에 저장합니다.
    Args:
        job_list (list[tuple[str, dict]]): (문서ID, 문서 데이터)의 리스트.
    
    TODO: 삭제 예정 - 테스트용으로만 사용
    """
    model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    pinecone = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index = pinecone.Index('job-postings')

    vectors_to_upsert = []
    for job_id, job_data in job_list:
        plain_text = preprocess_job_to_text(job_data)
        vector = model.encode(plain_text).tolist()
        
        vectors_to_upsert.append({
            'id': job_id,
            'values': vector,
            'metadata': {
                'firestore_id': job_id,
                'category': job_data.get('job_category', 'N/A'),
                'title': job_data.get('job_title', 'N/A')
            }
        })
    
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert)
        print(f"Pinecone에 {len(vectors_to_upsert)}개의 벡터를 저장했습니다.")
    else:
        print("Pinecone에 저장할 데이터가 없습니다.")