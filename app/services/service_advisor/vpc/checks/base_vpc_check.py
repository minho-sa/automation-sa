from abc import ABC, abstractmethod
from typing import Dict, Any, List
import boto3

class BaseVPCCheck(ABC):
    """VPC 검사의 기본 클래스"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = None
    
    @abstractmethod
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """데이터 수집"""
        pass
    
    @abstractmethod
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 분석"""
        pass
    
    @abstractmethod
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """권장사항 생성"""
        pass
    
    @abstractmethod
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """메시지 생성"""
        pass
    
    def run(self, role_arn=None) -> Dict[str, Any]:
        """검사 실행"""
        from app.services.service_advisor.common.unified_result import (
            create_unified_check_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR
        )
        
        try:
            # 데이터 수집
            collected_data = self.collect_data(role_arn)
            
            # 데이터 분석
            analysis_result = self.analyze_data(collected_data)
            
            # 권장사항 생성
            recommendations = self.generate_recommendations(analysis_result)
            
            # 메시지 생성
            message = self.create_message(analysis_result)
            
            # 상태 결정
            if analysis_result.get('problem_count', 0) > 0:
                status = STATUS_WARNING
            else:
                status = STATUS_OK
            
            return create_unified_check_result(
                status=status,
                message=message,
                resources=analysis_result.get('resources', []),
                recommendations=recommendations
            )
            
        except Exception as e:
            from app.services.service_advisor.common.unified_result import create_error_result
            return create_error_result(f'VPC 검사 중 오류가 발생했습니다: {str(e)}')