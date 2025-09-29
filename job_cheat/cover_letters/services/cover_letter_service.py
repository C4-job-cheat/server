#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
자기소개서 생성 서비스 모듈

이 모듈은 사용자의 페르소나 데이터와 RAG 검색을 통해
지원 회사에 맞는 자기소개서를 생성하는 서비스를 제공합니다.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.conf import settings
from firebase_admin import firestore
from google.api_core import exceptions as google_exceptions

from core.services.firebase_personas import get_persona_document, PersonaNotFoundError
from core.services.conversation_rag_service import get_rag_context
from core.services.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)

USER_COLLECTION = "users"
PERSONA_SUBCOLLECTION = "personas"
COVER_LETTER_SUBCOLLECTION = "cover_letter"


class CoverLetterServiceError(RuntimeError):
    """자기소개서 서비스 관련 예외."""


class CoverLetterService:
    """자기소개서 생성 및 관리를 담당하는 서비스."""
    
    def __init__(self):
        """서비스 초기화."""
        self.gemini_service = get_gemini_service()
        self.db = getattr(settings, "FIREBASE_DB", None)
        if not self.db:
            raise CoverLetterServiceError("Firestore 클라이언트를 찾을 수 없습니다.")
    
    async def generate_cover_letter(
        self,
        user_id: str,
        persona_id: str,
        company_name: str,
        strengths: str,
        activities: str,
        style: str
    ) -> Dict[str, Any]:
        """
        사용자의 페르소나 데이터와 RAG 검색을 통해 자기소개서를 생성합니다.
        
        Args:
            user_id: 사용자 ID
            persona_id: 페르소나 ID
            company_name: 지원 회사 이름
            strengths: 본인의 강점
            activities: 관련 활동 정보
            style: 자기소개서 스타일 (경험 중심, 지식 위주, 창의적)
            
        Returns:
            생성된 자기소개서 데이터
            
        Raises:
            CoverLetterServiceError: 생성 실패 시
        """
        try:
            logger.info(f"📝 자기소개서 생성 서비스 시작")
            logger.info(f"   👤 user_id: {user_id}")
            logger.info(f"   🎭 persona_id: {persona_id}")
            logger.info(f"   🏢 company_name: {company_name}")
            logger.info(f"   💪 strengths: {strengths}")
            logger.info(f"   🎯 activities: {activities}")
            logger.info(f"   🎨 style: {style}")
            
            # 1. 사용자 페르소나 데이터 조회
            logger.info(f"📤 페르소나 데이터 조회 시작")
            logger.info(f"   🔗 get_persona_document(user_id={user_id}, persona_id={persona_id})")
            persona_data = get_persona_document(user_id=user_id, persona_id=persona_id, db=self.db)
            logger.info(f"📥 페르소나 데이터 수신 완료")
            logger.info(f"   📊 페르소나 데이터: {persona_data}")
            
            # 2. 페르소나에서 필요한 정보 추출
            logger.info(f"🔧 페르소나 정보 추출 시작")
            job_category = persona_data.get('job_category', '')
            job_role = persona_data.get('job_role', '')
            skills = persona_data.get('skills', [])
            certifications = persona_data.get('certifications', [])
            school_name = persona_data.get('school_name', '')
            major = persona_data.get('major', '')
            final_evaluation = persona_data.get('final_evaluation', '')
            
            logger.info(f"✅ 페르소나 정보 추출 완료")
            logger.info(f"   💼 job_category: {job_category}")
            logger.info(f"   🎯 job_role: {job_role}")
            logger.info(f"   🛠️ skills: {skills}")
            logger.info(f"   📜 certifications: {certifications}")
            logger.info(f"   🎓 school_name: {school_name}")
            logger.info(f"   📚 major: {major}")
            logger.info(f"   ⭐ final_evaluation: {final_evaluation}")
            
            # 3. RAG 검색을 위한 쿼리 생성
            logger.info(f"🔍 RAG 검색 쿼리 생성 시작")
            rag_query = self._create_rag_query(company_name, job_category, job_role, strengths)
            logger.info(f"✅ RAG 검색 쿼리 생성 완료")
            logger.info(f"   📝 쿼리: {rag_query}")
            
            # 4. RAG 검색으로 관련 대화 내역 조회
            logger.info(f"📤 RAG 검색 시작")
            logger.info(f"   🔗 get_rag_context(query={rag_query}, user_id={user_id}, top_k=5)")
            rag_context = await get_rag_context(rag_query, user_id, top_k=5)
            logger.info(f"📥 RAG 검색 완료")
            logger.info(f"   📊 검색된 컨텍스트 수: {len(rag_context) if rag_context else 0}")
            logger.info(f"   📋 RAG 컨텍스트: {rag_context}")
            
            # 5. 자기소개서 생성 프롬프트 구성
            logger.info(f"🔧 자기소개서 프롬프트 구성 시작")
            prompt = self._create_cover_letter_prompt(
                company_name=company_name,
                job_category=job_category,
                job_role=job_role,
                strengths=strengths,
                activities=activities,
                skills=skills,
                certifications=certifications,
                school_name=school_name,
                major=major,
                final_evaluation=final_evaluation,
                rag_context=rag_context,
                style=style
            )
            logger.info(f"✅ 자기소개서 프롬프트 구성 완료")
            logger.info(f"   📝 프롬프트 길이: {len(prompt)}자")
            logger.info(f"   📋 프롬프트 미리보기: {prompt[:200]}...")
            
            # 6. Gemini를 통해 자기소개서 생성
            logger.info(f"📤 Gemini 자기소개서 생성 시작")
            logger.info(f"   🔗 generate_structured_response(prompt, response_format='json')")
            cover_letter_json = await self.gemini_service.generate_structured_response(
                prompt, response_format="json"
            )
            logger.info(f"📥 Gemini 자기소개서 생성 완료")
            logger.info(f"   📊 생성된 JSON 길이: {len(cover_letter_json)}자")
            logger.info(f"   📋 생성된 JSON: {cover_letter_json}")
            
            # 7. JSON 파싱 및 검증
            logger.info(f"🔧 JSON 파싱 시작")
            cover_letter_data = json.loads(cover_letter_json)
            logger.info(f"✅ JSON 파싱 완료")
            logger.info(f"   📊 파싱된 데이터: {cover_letter_data}")
            
            # 8. 글자 수 계산
            logger.info(f"🔢 글자 수 계산 시작")
            total_text = ""
            for paragraph_data in cover_letter_data.get("cover_letter", []):
                total_text += paragraph_data.get("paragraph", "")
            cover_letter_data["character_count"] = len(total_text)
            logger.info(f"✅ 글자 수 계산 완료")
            logger.info(f"   📊 총 글자 수: {cover_letter_data['character_count']}자")
            
            # 9. Firestore에 저장
            logger.info(f"💾 Firestore 저장 시작")
            logger.info(f"   🔗 _save_cover_letter(user_id={user_id}, persona_id={persona_id}, company_name={company_name})")
            saved_data = await self._save_cover_letter(
                user_id=user_id,
                persona_id=persona_id,
                company_name=company_name,
                cover_letter_data=cover_letter_data
            )
            logger.info(f"✅ Firestore 저장 완료")
            logger.info(f"   📊 저장된 데이터: {saved_data}")
            
            logger.info(f"🎉 자기소개서 생성 완료")
            logger.info(f"   👤 user_id: {user_id}")
            logger.info(f"   🏢 company: {company_name}")
            logger.info(f"   📝 글자 수: {cover_letter_data['character_count']}자")
            
            return saved_data
            
        except PersonaNotFoundError as exc:
            logger.error(f"페르소나를 찾을 수 없습니다: {exc}")
            raise CoverLetterServiceError(f"페르소나를 찾을 수 없습니다: {exc}") from exc
        except json.JSONDecodeError as exc:
            logger.error(f"자기소개서 JSON 파싱 실패: {exc}")
            raise CoverLetterServiceError(f"자기소개서 생성 실패: {exc}") from exc
        except Exception as exc:
            logger.error(f"자기소개서 생성 실패: {exc}")
            raise CoverLetterServiceError(f"자기소개서 생성 실패: {exc}") from exc
    
    def _create_rag_query(
        self, 
        company_name: str, 
        job_category: str, 
        job_role: str, 
        strengths: str
    ) -> str:
        """RAG 검색을 위한 쿼리를 생성합니다."""
        query_parts = []
        
        if company_name:
            query_parts.append(f"{company_name} 지원")
        
        if job_category:
            query_parts.append(f"{job_category} 분야")
        
        if job_role:
            query_parts.append(f"{job_role} 역할")
        
        if strengths:
            query_parts.append(f"강점 {strengths}")
        
        # 자기소개서에 도움이 될 만한 대화 검색
        query_parts.extend([
            "프로젝트 경험",
            "성과",
            "도전",
            "성장",
            "문제 해결",
            "리더십",
            "협업"
        ])
        
        return " ".join(query_parts)
    
    def _create_cover_letter_prompt(
        self,
        company_name: str,
        job_category: str,
        job_role: str,
        strengths: str,
        activities: str,
        skills: List[str],
        certifications: List[str],
        school_name: str,
        major: str,
        final_evaluation: str,
        rag_context: str,
        style: str
    ) -> str:
        """자기소개서 생성 프롬프트를 생성합니다."""
        
        # 스타일별 가이드라인
        style_guidelines = {
            "experience": "구체적인 프로젝트 경험, 성과, 도전과제 해결 과정을 중심으로 작성하세요. STAR 방법론(상황-과제-행동-결과)을 활용하세요.",
            "knowledge": "전문 지식, 기술적 이해도, 학습 과정을 중심으로 작성하세요. 이론적 배경과 실무 적용 사례를 강조하세요.",
            "creative": "독창적인 아이디어, 혁신적 사고, 창의적 문제 해결 과정을 중심으로 작성하세요. 상상력과 비전을 표현하세요."
        }
        
        style_guide = style_guidelines.get(style, "균형 잡힌 자기소개서를 작성하세요.")

        prompt = f"""
당신은 취업 전문가입니다. 주어진 정보를 바탕으로 {company_name}에 지원하는 자기소개서를 작성해주세요.

## 지원 정보
- 회사명: {company_name}
- 직무 분야: {job_category}
- 직무 역할: {job_role or "미지정"}
- 본인의 강점: {strengths}
- 관련 활동: {activities}
- 자기소개서 스타일: {style}

## 개인 정보
- 학력: {school_name} {major}
- 보유 기술: {', '.join(skills) if skills else "없음"}
- 자격증: {', '.join(certifications) if certifications else "없음"}
- 평가 결과: {final_evaluation if final_evaluation else "없음"}

## 관련 대화 내역 (RAG 검색 결과)
{rag_context if rag_context else "관련 대화 내역이 없습니다."}

## 요구사항
1. 자기소개서는 여러개의 문단으로 구성해주세요.
2. 각 문단마다 작성 이유를 포함해주세요. 
3. RAG 검색 결과에서 찾은 관련 경험을 적절히 활용해주세요.
4. 관련 대화 내역을 토대로 작성한 문단이라면 그 내용을 이유로 포함해주세요.
5. 회사와 직무에 맞는 구체적인 경험과 성과를 포함해주세요.
6. 진정성 있고 설득력 있는 내용으로 작성해주세요.
7. 스타일 가이드라인: {style_guide}

## 응답 형식
다음 JSON 형식으로 응답해주세요:
{{
  "cover_letter": [
    {{
      "paragraph": "문단 내용",
      "reason": "이 문단을 작성한 이유"
    }},
    {{
      "paragraph": "문단 내용", 
      "reason": "이 문단을 작성한 이유"
    }}
  ],
  "style": "{style}",
  "character_count": 0
}}
"""
        return prompt
    
    async def _save_cover_letter(
        self,
        user_id: str,
        persona_id: str,
        company_name: str,
        cover_letter_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """생성된 자기소개서를 Firestore에 저장합니다."""
        try:
            # Firestore 문서 참조 생성
            doc_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(COVER_LETTER_SUBCOLLECTION)
                .document()
            )
            
            # 저장할 데이터 구성
            save_data = {
                **cover_letter_data,
                "company_name": company_name,
                "user_id": user_id,
                "persona_id": persona_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            
            # Firestore에 저장
            doc_ref.set(save_data)
            
            # 저장된 데이터 조회
            snapshot = doc_ref.get()
            saved_data = snapshot.to_dict() if snapshot.exists else save_data
            saved_data["id"] = snapshot.id
            
            logger.info(f"자기소개서 저장 완료: user_id={user_id}, company={company_name}")
            return saved_data
            
        except google_exceptions.GoogleAPICallError as exc:
            logger.error(f"Firestore 저장 실패: {exc}")
            raise CoverLetterServiceError(f"자기소개서 저장 실패: {exc}") from exc
        except Exception as exc:
            logger.error(f"자기소개서 저장 중 오류: {exc}")
            raise CoverLetterServiceError(f"자기소개서 저장 실패: {exc}") from exc
    
    async def get_cover_letters(
        self,
        user_id: str,
        persona_id: str
    ) -> List[Dict[str, Any]]:
        """사용자의 특정 페르소나에 대한 모든 자기소개서를 조회합니다."""
        try:
            # Firestore 컬렉션 참조
            collection_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(COVER_LETTER_SUBCOLLECTION)
            )
            
            # 문서들 조회
            docs = collection_ref.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
            
            cover_letters = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                cover_letters.append(data)
            
            logger.info(f"자기소개서 목록 조회 완료: user_id={user_id}, persona_id={persona_id}, count={len(cover_letters)}")
            return cover_letters
            
        except google_exceptions.GoogleAPICallError as exc:
            logger.error(f"자기소개서 목록 조회 실패: {exc}")
            raise CoverLetterServiceError(f"자기소개서 목록 조회 실패: {exc}") from exc
        except Exception as exc:
            logger.error(f"자기소개서 목록 조회 중 오류: {exc}")
            raise CoverLetterServiceError(f"자기소개서 목록 조회 실패: {exc}") from exc

    async def get_cover_letter_detail(
        self,
        user_id: str,
        persona_id: str,
        cover_letter_id: str
    ) -> Dict[str, Any]:
        """특정 자기소개서의 상세 정보를 조회합니다."""
        try:
            # Firestore 문서 참조
            doc_ref = (
                self.db.collection(USER_COLLECTION)
                .document(user_id)
                .collection(PERSONA_SUBCOLLECTION)
                .document(persona_id)
                .collection(COVER_LETTER_SUBCOLLECTION)
                .document(cover_letter_id)
            )

            # 문서 조회
            doc = doc_ref.get()

            if not doc.exists:
                raise CoverLetterServiceError(f"자기소개서를 찾을 수 없습니다: {cover_letter_id}")

            data = doc.to_dict()
            data["id"] = doc.id

            logger.info(f"자기소개서 상세 조회 완료: user_id={user_id}, persona_id={persona_id}, cover_letter_id={cover_letter_id}")
            return data

        except google_exceptions.GoogleAPICallError as exc:
            logger.error(f"자기소개서 상세 조회 실패: {exc}")
            raise CoverLetterServiceError(f"자기소개서 상세 조회 실패: {exc}") from exc
        except Exception as exc:
            logger.error(f"자기소개서 상세 조회 중 오류: {exc}")
            raise CoverLetterServiceError(f"자기소개서 상세 조회 실패: {exc}") from exc


# 편의 함수들
async def generate_cover_letter(
    user_id: str,
    persona_id: str,
    company_name: str,
    strengths: str,
    activities: str,
    style: str
) -> Dict[str, Any]:
    """자기소개서를 생성합니다."""
    service = CoverLetterService()
    return await service.generate_cover_letter(user_id, persona_id, company_name, strengths, activities, style)


async def get_cover_letters(user_id: str, persona_id: str) -> List[Dict[str, Any]]:
    """사용자의 자기소개서 목록을 조회합니다."""
    service = CoverLetterService()
    return await service.get_cover_letters(user_id, persona_id)


async def get_cover_letter_detail(user_id: str, persona_id: str, cover_letter_id: str) -> Dict[str, Any]:
    """특정 자기소개서의 상세 정보를 조회합니다."""
    service = CoverLetterService()
    return await service.get_cover_letter_detail(user_id, persona_id, cover_letter_id)
