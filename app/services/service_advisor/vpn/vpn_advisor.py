from typing import Dict, List, Any
from app.services.service_advisor.common.base_advisor import BaseAdvisor

class VPNAdvisor(BaseAdvisor):
    """VPN 서비스 어드바이저"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.service_name = 'vpn'
        self.service_display_name = 'VPN'
        
        # 검사 항목 정의
        self.checks = [
            {
                'id': 'vpn_connection_status_check',
                'name': 'VPN 연결 상태 검사',
                'description': 'VPN 연결의 상태와 터널 상태를 검사합니다.',
                'category': '내결함성',
                'severity': 'high'
            },
            {
                'id': 'vpn_service_limits_check',
                'name': 'VPN 서비스 한도 검사',
                'description': 'VPN 관련 리소스의 서비스 한도 사용량을 검사합니다.',
                'category': '서비스-한도',
                'severity': 'medium'
            }
        ]
    
    def get_checks(self) -> List[Dict[str, Any]]:
        """사용 가능한 검사 목록 반환"""
        return self.checks
    
    def get_available_checks(self) -> List[Dict[str, Any]]:
        """사용 가능한 검사 목록 반환 (라우트 호환성)"""
        return self.checks
    
    def run_check(self, check_id: str, role_arn: str = None) -> Dict[str, Any]:
        """특정 검사 실행"""
        try:
            if check_id == 'vpn_connection_status_check':
                from app.services.service_advisor.vpn.checks.vpn_connection_status_check import run
                return run(role_arn)
            elif check_id == 'vpn_service_limits_check':
                from app.services.service_advisor.vpn.checks.vpn_service_limits_check import run
                return run(role_arn)
            else:
                return {
                    'status': 'error',
                    'message': f'알 수 없는 검사 ID: {check_id}',
                    'recommendations': [],
                    'resources': []
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'검사 실행 중 오류 발생: {str(e)}',
                'recommendations': [],
                'resources': []
            }