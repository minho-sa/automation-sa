from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.services.service_advisor.common.base_advisor import BaseAdvisor

class BaseACMCheck(BaseAdvisor, ABC):
    """ACM 검사의 기본 클래스"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.service_name = 'acm'
    
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
        try:
            # 데이터 수집
            collected_data = self.collect_data(role_arn=role_arn)
            
            # 데이터 분석
            analysis_result = self.analyze_data(collected_data)
            
            # 권장사항 생성
            recommendations = self.generate_recommendations(analysis_result)
            
            # 메시지 생성
            message = self.create_message(analysis_result)
            
            # 상태 결정
            status = 'ok'
            if analysis_result.get('problem_count', 0) > 0:
                status = 'warning'
            
            return {
                'status': status,
                'message': message,
                'resources': analysis_result.get('resources', []),
                'recommendations': recommendations,
                'total_resources': analysis_result.get('total_resources', 0),
                'problem_count': analysis_result.get('problem_count', 0)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'검사 실행 중 오류가 발생했습니다: {str(e)}',
                'resources': [],
                'recommendations': [],
                'total_resources': 0,
                'problem_count': 0
            }