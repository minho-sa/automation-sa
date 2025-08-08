import boto3
from typing import Dict, List, Any, Optional
from app.services.service_advisor.common.base_advisor import BaseAdvisor
from app.services.service_advisor.common.aws_client import AWSClient
from app.services.service_advisor.s3.checks import (
    public_access,
    encryption,
    versioning_check,
    lifecycle_check,
    logging_check,
    cors_check,
    object_lock_check,
    replication_check,
    intelligent_tiering_check
)

class S3Advisor(BaseAdvisor):
    """
    S3 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        S3 어드바이저 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        super().__init__(session)
        self.aws_client = AWSClient(session)
    
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
            category='보안',
            severity='high'
        )
        
        # 버전 관리 설정 검사
        self.register_check(
            check_id='s3-versioning',
            name='버전 관리 설정',
            description='S3 버킷의 버전 관리 설정을 검사하여 데이터 보호 수준을 평가합니다. 버전 관리가 활성화되지 않은 버킷을 식별하고 개선 방안을 제시합니다.',
            function=versioning_check.run,
            category='내결함성',
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
        
        # CORS 설정 검사
        self.register_check(
            check_id='s3-cors',
            name='CORS 설정',
            description='S3 버킷의 CORS(Cross-Origin Resource Sharing) 설정을 검사하여 보안 위험을 식별합니다. 과도하게 허용적인 CORS 설정이 있는 버킷을 찾아 개선 방안을 제시합니다.',
            function=cors_check.run,
            category='보안',
            severity='medium'
        )
        
        # 객체 잠금 설정 검사
        self.register_check(
            check_id='s3-object-lock',
            name='객체 잠금 설정',
            description='S3 버킷의 객체 잠금(Object Lock) 설정을 검사하여 데이터 보호 수준을 평가합니다. 중요한 데이터를 저장하는 버킷에 객체 잠금이 활성화되지 않은 경우 개선 방안을 제시합니다.',
            function=object_lock_check.run,
            category='내결함성',
            severity='medium'
        )
        
        # 복제 설정 검사
        self.register_check(
            check_id='s3-replication',
            name='복제 설정',
            description='S3 버킷의 복제(Replication) 설정을 검사하여 재해 복구 수준을 평가합니다. 프로덕션 환경의 버킷에 복제가 구성되지 않은 경우 개선 방안을 제시합니다.',
            function=replication_check.run,
            category='내결함성',
            severity='medium'
        )
        
        # Intelligent-Tiering 설정 검사
        self.register_check(
            check_id='s3-intelligent-tiering',
            name='Intelligent-Tiering 설정',
            description='S3 버킷의 Intelligent-Tiering 설정을 검사하여 비용 최적화 기회를 식별합니다. 액세스 패턴이 예측할 수 없는 데이터에 대해 Intelligent-Tiering 사용을 권장합니다.',
            function=intelligent_tiering_check.run,
            category='비용 최적화',
            severity='low'
        )