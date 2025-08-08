import boto3
from typing import Dict, List, Any, Optional
from app.services.service_advisor.common.base_advisor import BaseAdvisor
from app.services.service_advisor.common.aws_client import AWSClient
from app.services.service_advisor.iam.checks import (
    access_key_rotation,
    password_policy,
    mfa_check,
    inactive_users_check,
    root_account_check,
    policy_analyzer_check,
    exposed_access_keys_check
)

class IAMAdvisor(BaseAdvisor):
    """
    IAM 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        IAM 어드바이저 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        super().__init__(session)
        self.aws_client = AWSClient(session)
    
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
        
        # MFA 설정 검사
        self.register_check(
            check_id='iam-mfa',
            name='MFA 설정',
            description='IAM 사용자의 MFA(다중 인증) 설정 상태를 검사합니다. 특히 관리자 권한이 있는 사용자에게 MFA를 설정하여 계정 보안을 강화하는 것이 중요합니다.',
            function=mfa_check.run,
            category='보안',
            severity='high'
        )
        
        # 비활성 사용자 검사
        self.register_check(
            check_id='iam-inactive-users',
            name='비활성 사용자',
            description='장기간 활동이 없는 IAM 사용자를 식별합니다. 비활성 계정은 보안 위험을 초래할 수 있으므로 정기적으로 검토하고 필요하지 않은 계정은 삭제하는 것이 좋습니다.',
            function=inactive_users_check.run,
            category='보안',
            severity='medium'
        )
        
        # 루트 계정 보안 검사
        self.register_check(
            check_id='iam-root-account',
            name='루트 계정 보안',
            description='AWS 계정의 루트 사용자 보안 설정을 검사합니다. 루트 계정에 MFA 설정 및 액세스 키 삭제 등의 보안 모범 사례를 준수하는지 확인합니다.',
            function=root_account_check.run,
            category='보안',
            severity='high'
        )
        
        # 정책 분석 검사
        self.register_check(
            check_id='iam-policy-analyzer',
            name='정책 분석',
            description='IAM 정책의 보안 위험을 분석합니다. 관리자 액세스를 허용하거나 와일드카드 리소스 또는 작업을 사용하는 정책을 식별하고 최소 권한 원칙에 따라 개선 방안을 제시합니다.',
            function=policy_analyzer_check.run,
            category='보안',
            severity='high'
        )
        
        # 노출된 액세스 키 검사
        self.register_check(
            check_id='iam-exposed-access-keys',
            name='노출된 액세스 키 검사',
            description='의심스러운 액세스 키 사용 패턴을 분석하여 노출 가능성을 검사합니다.\n이 검사는 노출된 액세스 키의 식별을 보장하지 않습니다. 액세스 키와 AWS 리소스의 안전과 보안에 대한 최종 책임은 사용자에게 있습니다. ',
            function=exposed_access_keys_check.run,
            category='보안',
            severity='high'
        )
        

        

