import boto3
from typing import Dict, List, Any
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.s3.checks import (
    public_access,
    encryption,
    versioning_check,
    lifecycle_check,
    logging_check
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
        
        # 버전 관리 설정 검사
        self.register_check(
            check_id='s3-versioning',
            name='버전 관리 설정',
            description='S3 버킷의 버전 관리 설정을 검사하여 데이터 보호 수준을 평가합니다. 버전 관리가 활성화되지 않은 버킷을 식별하고 개선 방안을 제시합니다.',
            function=versioning_check.run,
            category='데이터 보호',
            severity='medium'
        )
        
        # 수명 주기 정책 검사
        self.register_check(
            check_id='s3-lifecycle',
            name='수명 주기 정책',
            description='S3 버킷의 수명 주기 정책 설정을 검사하여 비용 최적화 기회를 식별합니다. 수명 주기 정책이 없거나 개선이 필요한 버킷을 찾아 개선 방안을 제시합니다.',
            function=lifecycle_check.run,
            category='비용 최적화',
            severity='medium'
        )
        
        # 액세스 로깅 설정 검사
        self.register_check(
            check_id='s3-logging',
            name='액세스 로깅 설정',
            description='S3 버킷의 액세스 로깅 설정을 검사하여 보안 및 감사 수준을 평가합니다. 로깅이 활성화되지 않은 버킷을 식별하고 개선 방안을 제시합니다.',
            function=logging_check.run,
            category='보안',
            severity='medium'
        )