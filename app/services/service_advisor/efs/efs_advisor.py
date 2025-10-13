import boto3
from typing import Dict, List, Any, Optional
from app.services.service_advisor.common.base_advisor import BaseAdvisor
from app.services.service_advisor.common.aws_client import AWSClient
from app.services.service_advisor.efs.checks import data_in_transit_encryption_check

class EFSAdvisor(BaseAdvisor):
    """
    EFS 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        EFS 어드바이저 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        super().__init__(session)
        self.aws_client = AWSClient(session)
    
    def _register_checks(self) -> None:
        """EFS 서비스에 대한 검사 항목을 등록합니다."""
        
        # 전송 중 데이터 암호화 검사
        self.register_check(
            check_id='efs-data-in-transit-encryption',
            name='전송 중 데이터 암호화',
            description='전송 중 데이터 암호화를 사용하여 Amazon EFS 파일 시스템이 탑재되었는지 확인합니다. 우발적인 노출 또는 무단 액세스로부터 데이터를 보호하기 위해 모든 데이터 흐름에 전송 중 데이터 암호화를 사용할 것을 권장합니다.',
            function=data_in_transit_encryption_check.run,
            category='보안',
            severity='high'
        )