import boto3
from typing import Dict, List, Any
from app.services.service_advisor.common.base_advisor import BaseAdvisor

class BaseVPNCheck(BaseAdvisor):
    """VPN 검사 기본 클래스"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.service_name = 'vpn'
    
    def run(self, role_arn=None) -> Dict[str, Any]:
        """검사 실행"""
        try:
            # 데이터 수집
            collected_data = self.collect_data(role_arn)
            
            # 데이터 분석
            analysis_result = self.analyze_data(collected_data)
            
            # 권장 사항 생성
            recommendations = self.generate_recommendations(analysis_result)
            
            # 메시지 생성
            message = self.create_message(analysis_result)
            
            # 상태 결정
            status = self.determine_status(analysis_result)
            
            return {
                'status': status,
                'message': message,
                'recommendations': recommendations,
                'resources': analysis_result.get('resources', []),
                'total_resources': analysis_result.get('total_resources', 0),
                'problem_count': analysis_result.get('problem_count', 0)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'검사 중 오류가 발생했습니다: {str(e)}',
                'recommendations': [],
                'resources': [],
                'total_resources': 0,
                'problem_count': 0
            }
    
    def determine_status(self, analysis_result: Dict[str, Any]) -> str:
        """상태 결정"""
        problem_count = analysis_result.get('problem_count', 0)
        total_resources = analysis_result.get('total_resources', 0)
        
        if total_resources == 0:
            return 'ok'
        elif problem_count == 0:
            return 'ok'
        elif problem_count < total_resources:
            return 'warning'
        else:
            return 'error'