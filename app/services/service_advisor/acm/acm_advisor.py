from typing import Dict, List, Any
import boto3
from app.services.service_advisor.common.base_advisor import BaseAdvisor
from app.services.service_advisor.acm.checks.certificate_expiry_check import CertificateExpiryCheck

class ACMAdvisor(BaseAdvisor):
    """ACM 서비스 어드바이저"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.service_name = 'acm'
        self.service_display_name = 'AWS Certificate Manager'
        
        # 검사 항목 등록
        self.checks = {
            'certificate_expiry_check': {
                'class': CertificateExpiryCheck,
                'name': '인증서 만료 검사',
                'description': 'ACM 인증서의 만료일을 확인하고 갱신이 필요한 인증서를 식별합니다.',
                'category': '보안',
                'severity': 'high'
            }
        }
    
    def get_service_info(self) -> Dict[str, Any]:
        """서비스 정보 반환"""
        return {
            'name': self.service_display_name,
            'id': self.service_name,
            'description': 'SSL/TLS 인증서 관리 서비스',
            'icon': 'fas fa-certificate'
        }
    
    def get_available_checks(self) -> List[Dict[str, Any]]:
        """사용 가능한 검사 항목 목록 반환"""
        available_checks = []
        
        for check_id, check_info in self.checks.items():
            available_checks.append({
                'id': check_id,
                'name': check_info['name'],
                'description': check_info['description'],
                'category': check_info['category'],
                'severity': check_info['severity']
            })
        
        return available_checks
    
    def run_check(self, check_id: str, role_arn: str = None) -> Dict[str, Any]:
        """특정 검사 실행"""
        if check_id not in self.checks:
            return {
                'status': 'error',
                'message': f'검사 항목 {check_id}를 찾을 수 없습니다.',
                'resources': [],
                'recommendations': []
            }
        
        check_class = self.checks[check_id]['class']
        check_instance = check_class(session=self.session)
        
        return check_instance.run(role_arn=role_arn)