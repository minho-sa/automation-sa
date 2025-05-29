import boto3
from typing import Dict, List, Any
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.s3.checks import (
    public_access,
    encryption
)

class S3Advisor(BaseAdvisor):
    """
    S3 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def _register_checks(self) -> None:
        """S3 서비스에 대한 검사 항목을 등록합니다."""
        
        # 퍼블릭 액세스 설정 검사
        self.register_check(
            check_id='s3-public-access',
            name='퍼블릭 액세스 설정',
            description='S3 버킷의 퍼블릭 액세스 설정을 검사하여 보안 위험을 식별합니다. 퍼블릭 액세스 차단 설정이 활성화되지 않은 버킷을 찾아 개선 방안을 제시합니다.',
            function=public_access.run,
            category='보안',
            severity='high'
        )
        
        # 암호화 설정 검사
        self.register_check(
            check_id='s3-encryption',
            name='암호화 설정',
            description='S3 버킷의 기본 암호화 설정을 검사하여 데이터 보호 수준을 평가합니다. 암호화가 설정되지 않은 버킷을 식별하고 개선 방안을 제시합니다.',
            function=encryption.run,
            category='데이터 보호',
            severity='high'
        )