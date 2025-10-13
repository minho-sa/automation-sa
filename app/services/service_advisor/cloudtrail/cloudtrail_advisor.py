from app.services.service_advisor.common.base_advisor import BaseAdvisor
from typing import Dict, List, Any
import importlib

class CloudTrailAdvisor(BaseAdvisor):
    def __init__(self, session=None):
        super().__init__(session)
        self.service_name = 'cloudtrail'
        self.service_display_name = 'CloudTrail'
        
        # CloudTrail 검사 항목 정의
        self.checks = [
            {
                'id': 'cloudtrail-enabled',
                'name': 'CloudTrail 활성화 상태',
                'description': 'CloudTrail이 활성화되어 있고 올바르게 구성되어 있는지 확인합니다.',
                'category': '보안',
                'severity': 'high',
                'check_function': 'cloudtrail_enabled_check'
            },
            {
                'id': 'cloudtrail-log-file-validation',
                'name': 'CloudTrail 로그 파일 검증',
                'description': 'CloudTrail 로그 파일 무결성 검증이 활성화되어 있는지 확인합니다.',
                'category': '보안',
                'severity': 'medium',
                'check_function': 'log_file_validation_check'
            }
        ]
    
    def get_available_checks(self) -> List[Dict[str, Any]]:
        """사용 가능한 검사 항목 목록을 반환합니다."""
        return self.checks
    
    def run_check(self, check_id: str, role_arn: str = None) -> Dict[str, Any]:
        """특정 검사를 실행합니다."""
        check_info = next((check for check in self.checks if check['id'] == check_id), None)
        
        if not check_info:
            return {
                'status': 'error',
                'message': f'검사 항목을 찾을 수 없습니다: {check_id}'
            }
        
        try:
            # 검사 모듈 동적 임포트
            module_name = f"app.services.service_advisor.cloudtrail.checks.{check_info['check_function']}"
            check_module = importlib.import_module(module_name)
            
            # 검사 실행
            result = check_module.run(role_arn=role_arn)
            return result
            
        except ImportError as e:
            return {
                'status': 'error',
                'message': f'검사 모듈을 찾을 수 없습니다: {check_info["check_function"]}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'검사 실행 중 오류가 발생했습니다: {str(e)}'
            }