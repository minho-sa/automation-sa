from typing import Dict, List, Any
from app.services.service_advisor.common.base_advisor import BaseAdvisor

class EBSAdvisor(BaseAdvisor):
    """EBS 서비스 어드바이저"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.service_name = 'ebs'
        self.service_display_name = 'EBS'
        
        # 검사 항목 정의
        self.checks = [
            {
                'id': 'ebs_encryption_check',
                'name': 'EBS 볼륨 암호화 검사',
                'description': 'EBS 볼륨의 암호화 상태를 검사합니다.',
                'category': '보안',
                'severity': 'high'
            },
            {
                'id': 'unused_volumes_check',
                'name': '사용하지 않는 EBS 볼륨 검사',
                'description': '인스턴스에 연결되지 않은 EBS 볼륨을 검사합니다.',
                'category': '비용-최적화',
                'severity': 'medium'
            },
            {
                'id': 'snapshot_management_check',
                'name': 'EBS 스냅샷 관리 검사',
                'description': 'EBS 스냅샷의 상태와 수명주기를 검사합니다.',
                'category': '비용-최적화',
                'severity': 'low'
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
            if check_id == 'ebs_encryption_check':
                from app.services.service_advisor.ebs.checks.ebs_encryption_check import run
                return run(role_arn)
            elif check_id == 'unused_volumes_check':
                from app.services.service_advisor.ebs.checks.unused_volumes_check import run
                return run(role_arn)
            elif check_id == 'snapshot_management_check':
                from app.services.service_advisor.ebs.checks.snapshot_management_check import run
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