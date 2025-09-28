"""
직무별 핵심 역량 정보를 관리하는 서비스 모듈
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class JobCompetenciesService:
    """직무별 핵심 역량 정보를 제공하는 서비스 클래스"""
    
    def __init__(self):
        """job-data.json 파일을 로드하여 초기화"""
        self._job_data = None
        self._load_job_data()
    
    def _load_job_data(self) -> None:
        """job-data.json 파일을 로드합니다."""
        try:
            # core/data 디렉토리에서 job-data.json 파일 찾기
            current_file = Path(__file__)
            job_data_path = current_file.parent.parent / "data" / "job-data.json"
            
            if not job_data_path.exists():
                logger.error(f"job-data.json 파일을 찾을 수 없습니다: {job_data_path}")
                return
            
            with open(job_data_path, 'r', encoding='utf-8') as f:
                self._job_data = json.load(f)
            
            logger.info(f"job-data.json 로드 완료: {len(self._job_data.get('job_groups', []))}개 직군")
            
        except Exception as e:
            logger.error(f"job-data.json 로드 실패: {e}")
            self._job_data = None
    
    def get_core_competencies_by_job_category(self, job_category: str) -> List[Dict[str, str]]:
        """
        직군명으로 핵심 역량 목록을 반환합니다.
        
        Args:
            job_category: 직군명 (예: "기획", "전략", "PM·PO" 등)
            
        Returns:
            핵심 역량 목록 (id, name, description 포함)
            
        Example:
            >>> service = JobCompetenciesService()
            >>> competencies = service.get_core_competencies_by_job_category("기획")
            >>> print(competencies)
            [
                {
                    "id": "JG_01_C01",
                    "name": "문제정의",
                    "description": "모호한 요구를 핵심 문제로 압축하는 역량"
                },
                ...
            ]
        """
        if not self._job_data:
            logger.warning("job-data.json이 로드되지 않았습니다.")
            return []
        
        job_groups = self._job_data.get('job_groups', [])
        
        # 직군명으로 매칭 (정확한 매칭 우선, 부분 매칭도 허용)
        matched_group = None
        
        # 1. 정확한 매칭 시도
        for group in job_groups:
            if group.get('name') == job_category:
                matched_group = group
                break
        
        # 2. 부분 매칭 시도 (정확한 매칭이 없는 경우)
        if not matched_group:
            for group in job_groups:
                group_name = group.get('name', '')
                if job_category in group_name or group_name in job_category:
                    matched_group = group
                    logger.info(f"부분 매칭으로 직군 찾음: '{job_category}' -> '{group_name}'")
                    break
        
        if not matched_group:
            logger.warning(f"직군을 찾을 수 없습니다: '{job_category}'")
            return []
        
        core_competencies = matched_group.get('core_competencies', [])
        logger.info(f"직군 '{matched_group.get('name')}'의 핵심 역량 {len(core_competencies)}개 반환")
        
        return core_competencies
    
    def get_all_job_categories(self) -> List[str]:
        """
        모든 직군명 목록을 반환합니다.
        
        Returns:
            직군명 목록
        """
        if not self._job_data:
            return []
        
        job_groups = self._job_data.get('job_groups', [])
        return [group.get('name', '') for group in job_groups if group.get('name')]
    
    def get_job_group_info(self, job_category: str) -> Optional[Dict]:
        """
        직군명으로 전체 직군 정보를 반환합니다.
        
        Args:
            job_category: 직군명
            
        Returns:
            직군 정보 (roles, core_competencies 포함) 또는 None
        """
        if not self._job_data:
            return None
        
        job_groups = self._job_data.get('job_groups', [])
        
        for group in job_groups:
            if group.get('name') == job_category:
                return group
        
        return None


# 전역 인스턴스 생성
job_competencies_service = JobCompetenciesService()


def get_core_competencies_by_job_category(job_category: str) -> List[Dict[str, str]]:
    """
    직군명으로 핵심 역량 목록을 반환하는 편의 함수
    
    Args:
        job_category: 직군명
        
    Returns:
        핵심 역량 목록
    """
    return job_competencies_service.get_core_competencies_by_job_category(job_category)


def get_all_job_categories() -> List[str]:
    """
    모든 직군명 목록을 반환하는 편의 함수
    
    Returns:
        직군명 목록
    """
    return job_competencies_service.get_all_job_categories()
