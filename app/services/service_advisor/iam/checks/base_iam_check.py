"""
IAM 검사 항목의 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR
)

class BaseIAMCheck(ABC):
    """IAM 검사 항목의 기본 클래스"""
    
    @abstractmethod
    def collect_data(self) -> Dict[str, Any]:
        """
        AWS에서 필요한 데이터를 수집합니다.
        
        Returns:
            Dict[str, Any]: 수집된 데이터
        """
        pass
    
    @abstractmethod
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        수집된 데이터를 분석하여 결과를 생성합니다.
        
        Args:
            collected_data: 수집된 데이터
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        pass
    
    @abstractmethod
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        분석 결과를 바탕으로 권장사항을 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            List[str]: 권장사항 목록
        """
        pass
    
    @abstractmethod
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """
        분석 결과를 바탕으로 메시지를 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            str: 결과 메시지
        """
        pass
    
    def run(self, role_arn=None) -> Dict[str, Any]:
        """
        검사를 실행하고 결과를 반환합니다.
        
        Args:
            role_arn: AWS 역할 ARN (선택 사항)
            
        Returns:
            Dict[str, Any]: 검사 결과
        """
        try:
            # 데이터 수집
            collected_data = self.collect_data()
            
            # 데이터 분석
            analysis_result = self.analyze_data(collected_data)
            
            # 권장사항 생성
            recommendations = self.generate_recommendations(analysis_result)
            
            # 메시지 생성
            message = self.create_message(analysis_result)
            
            # 상태 결정
            problem_count = analysis_result.get('problem_count', 0)
            if problem_count > 0:
                status = STATUS_WARNING
            else:
                status = STATUS_OK
            
            # 리소스 목록 가져오기
            resources = analysis_result.get('resources', [])
            
            # 통일된 결과 생성
            result = create_unified_check_result(
                status=status,
                message=message,
                resources=resources,
                recommendations=recommendations,
                check_id=getattr(self, 'check_id', '')
            )
            
            return result
        except Exception as e:
            return create_error_result(f'검사 실행 중 오류가 발생했습니다: {str(e)}')