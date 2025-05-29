import boto3
from typing import Dict, List, Any
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.iam.checks import (
    access_key_rotation,
    password_policy
)

class IAMAdvisor(BaseAdvisor):
    """
    IAM 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def _register_checks(self) -> None:
        """IAM 서비스에 대한 검사 항목을 등록합니다."""
        
        # 액세스 키 교체 검사
        self.register_check(
            check_id='iam-access-key-rotation',
            name='액세스 키 교체',
            description='IAM 사용자의 액세스 키 교체 상태를 검사하여 오래된 액세스 키를 식별합니다. 90일 이상 교체되지 않은 액세스 키는 보안 위험을 초래할 수 있으므로 정기적인 교체를 권장합니다.',
            function=access_key_rotation.run,
            category='보안',
            severity='high'
        )
        
        # 암호 정책 검사
        self.register_check(
            check_id='iam-password-policy',
            name='암호 정책',
            description='계정의 암호 정책을 검사하여 보안 모범 사례를 준수하는지 확인합니다. 강력한 암호 정책은 무단 액세스를 방지하는 데 중요합니다.',
            function=password_policy.run,
            category='보안',
            severity='high'
        )