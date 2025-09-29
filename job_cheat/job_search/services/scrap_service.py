#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
스크랩 서비스 모듈

사용자가 추천받은 공고를 스크랩하고, 스크랩된 공고 목록을 조회하는 기능을 제공합니다.
"""

import logging
from typing import Dict, List, Any
from firebase_admin import firestore
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

USER_COLLECTION = "users"
PERSONA_SUBCOLLECTION = "personas"
JOB_POSTINGS_COLLECTION = "job_postings"


class ScrapServiceError(RuntimeError):
    """스크랩 서비스 관련 예외."""


def add_job_to_scrap(user_id: str, persona_id: str, job_posting_id: str) -> Dict[str, Any]:
    """
    공고를 스크랩에 추가합니다.
    
    Args:
        user_id: 사용자 ID
        persona_id: 페르소나 ID
        job_posting_id: 공고 ID
        
    Returns:
        스크랩 결과
    """
    try:
        logger.info(f"📌 스크랩 추가 서비스 시작")
        logger.info(f"   👤 user_id: {user_id}")
        logger.info(f"   🎭 persona_id: {persona_id}")
        logger.info(f"   💼 job_posting_id: {job_posting_id}")
        
        logger.info(f"🔗 Firestore 클라이언트 연결 시작")
        db = firestore.client()
        logger.info(f"✅ Firestore 클라이언트 연결 완료")
        
        # 페르소나 문서 참조
        logger.info(f"📋 페르소나 문서 참조 생성")
        persona_ref = (
            db.collection(USER_COLLECTION)
            .document(user_id)
            .collection(PERSONA_SUBCOLLECTION)
            .document(persona_id)
        )
        logger.info(f"   📍 경로: users/{user_id}/personas/{persona_id}")
        
        # 페르소나 데이터 조회
        logger.info(f"📤 페르소나 데이터 조회 시작")
        persona_doc = persona_ref.get()
        
        if not persona_doc.exists:
            logger.error(f"❌ 페르소나 문서가 존재하지 않음: {persona_id}")
            raise ScrapServiceError(f"페르소나를 찾을 수 없습니다: {persona_id}")
        
        logger.info(f"✅ 페르소나 문서 조회 완료")
        persona_data = persona_doc.to_dict()
        scrap_list = persona_data.get('scrap', [])
        logger.info(f"   📊 기존 스크랩 목록 길이: {len(scrap_list)}")
        logger.info(f"   📋 기존 스크랩 목록: {scrap_list}")
        
        # 중복 체크
        logger.info(f"🔍 중복 체크 시작")
        if job_posting_id in scrap_list:
            logger.warning(f"⚠️ 이미 스크랩된 공고: {job_posting_id}")
            raise ScrapServiceError("이미 스크랩된 공고입니다.")
        
        logger.info(f"✅ 중복 체크 통과")
        
        # 스크랩 목록에 추가
        logger.info(f"📝 스크랩 목록에 추가 시작")
        scrap_list.append(job_posting_id)
        logger.info(f"   📊 추가 후 스크랩 목록 길이: {len(scrap_list)}")
        logger.info(f"   📋 추가 후 스크랩 목록: {scrap_list}")
        
        # 페르소나 문서 업데이트
        logger.info(f"💾 페르소나 문서 업데이트 시작")
        persona_ref.update({
            'scrap': scrap_list
        })
        logger.info(f"✅ 페르소나 문서 업데이트 완료")
        
        logger.info(f"🎉 스크랩 추가 완료: {job_posting_id}")
        
        return {
            "success": True,
            "message": "공고가 성공적으로 스크랩되었습니다.",
            "scrap_count": len(scrap_list)
        }
        
    except google_exceptions.GoogleAPICallError as exc:
        logger.error(f"스크랩 추가 실패 (Firestore 오류): {exc}")
        raise ScrapServiceError(f"스크랩 추가 실패: {exc}") from exc
    except Exception as exc:
        logger.error(f"스크랩 추가 중 오류: {exc}")
        raise ScrapServiceError(f"스크랩 추가 실패: {exc}") from exc


def remove_job_from_scrap(user_id: str, persona_id: str, job_posting_id: str) -> Dict[str, Any]:
    """
    공고를 스크랩에서 제거합니다.
    
    Args:
        user_id: 사용자 ID
        persona_id: 페르소나 ID
        job_posting_id: 공고 ID
        
    Returns:
        제거 결과
    """
    try:
        logger.info(f"스크랩 제거: user_id={user_id}, persona_id={persona_id}, job_posting_id={job_posting_id}")
        
        db = firestore.client()
        
        # 페르소나 문서 참조
        persona_ref = (
            db.collection(USER_COLLECTION)
            .document(user_id)
            .collection(PERSONA_SUBCOLLECTION)
            .document(persona_id)
        )
        
        # 페르소나 데이터 조회
        persona_doc = persona_ref.get()
        if not persona_doc.exists:
            raise ScrapServiceError(f"페르소나를 찾을 수 없습니다: {persona_id}")
        
        persona_data = persona_doc.to_dict()
        scrap_list = persona_data.get('scrap', [])
        
        # 스크랩 목록에서 제거
        if job_posting_id in scrap_list:
            scrap_list.remove(job_posting_id)
            
            # 페르소나 문서 업데이트
            persona_ref.update({
                'scrap': scrap_list
            })
            
            logger.info(f"스크랩 제거 완료: {job_posting_id}")
            
            return {
                "success": True,
                "message": "공고가 성공적으로 스크랩에서 제거되었습니다.",
                "scrap_count": len(scrap_list)
            }
        else:
            raise ScrapServiceError("스크랩되지 않은 공고입니다.")
        
    except google_exceptions.GoogleAPICallError as exc:
        logger.error(f"스크랩 제거 실패 (Firestore 오류): {exc}")
        raise ScrapServiceError(f"스크랩 제거 실패: {exc}") from exc
    except Exception as exc:
        logger.error(f"스크랩 제거 중 오류: {exc}")
        raise ScrapServiceError(f"스크랩 제거 실패: {exc}") from exc


def get_scraped_jobs(user_id: str, persona_id: str) -> List[Dict[str, Any]]:
    """
    스크랩된 공고 목록을 조회합니다.
    
    Args:
        user_id: 사용자 ID
        persona_id: 페르소나 ID
        
    Returns:
        스크랩된 공고 목록
    """
    try:
        logger.info(f"스크랩된 공고 조회: user_id={user_id}, persona_id={persona_id}")
        
        db = firestore.client()
        
        # 페르소나 데이터 조회
        persona_ref = (
            db.collection(USER_COLLECTION)
            .document(user_id)
            .collection(PERSONA_SUBCOLLECTION)
            .document(persona_id)
        )
        
        persona_doc = persona_ref.get()
        if not persona_doc.exists:
            raise ScrapServiceError(f"페르소나를 찾을 수 없습니다: {persona_id}")
        
        persona_data = persona_doc.to_dict()
        scrap_list = persona_data.get('scrap', [])
        
        if not scrap_list:
            logger.info("스크랩된 공고가 없습니다.")
            return []
        
        # 각 스크랩된 공고의 상세 정보 조회
        scraped_jobs = []
        for job_posting_id in scrap_list:
            try:
                # 공고 상세 정보 조회
                job_posting_ref = db.collection(JOB_POSTINGS_COLLECTION).document(job_posting_id)
                job_posting_doc = job_posting_ref.get()
                
                if job_posting_doc.exists:
                    job_data = job_posting_doc.to_dict()
                    
                    # 스크랩된 공고 정보 구성
                    scraped_job = {
                        "job_posting_id": job_posting_id,
                        "company_name": job_data.get("company_name", ""),
                        "job_category": job_data.get("job_category", ""),
                        "job_title": job_data.get("job_title", ""),
                        "location": job_data.get("location", ""),
                        "requirements": job_data.get("requirements", []),
                        "preferred": job_data.get("preferred", []),
                        "deadline": job_data.get("deadline", ""),
                        "image_url": job_data.get("image_url", ""),
                        "company_logo": job_data.get("company_logo", ""),
                        "job_description": job_data.get("job_description", "")
                    }
                    
                    scraped_jobs.append(scraped_job)
                else:
                    logger.warning(f"공고 정보를 찾을 수 없습니다: {job_posting_id}")
                    
            except Exception as exc:
                logger.error(f"공고 정보 조회 실패 ({job_posting_id}): {exc}")
                continue
        
        logger.info(f"스크랩된 공고 조회 완료: {len(scraped_jobs)}개")
        return scraped_jobs
        
    except google_exceptions.GoogleAPICallError as exc:
        logger.error(f"스크랩된 공고 조회 실패 (Firestore 오류): {exc}")
        raise ScrapServiceError(f"스크랩된 공고 조회 실패: {exc}") from exc
    except Exception as exc:
        logger.error(f"스크랩된 공고 조회 중 오류: {exc}")
        raise ScrapServiceError(f"스크랩된 공고 조회 실패: {exc}") from exc
