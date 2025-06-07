"""
EC2 서비스 어드바이저 클래스
"""
import boto3
from typing import Dict, List, Any, Optional
from app.services.service_advisor.common.base_advisor import BaseAdvisor
from app.services.service_advisor.common.aws_client import AWSClient
from app.services.service_advisor.ec2.checks.security_group_check import SecurityGroupCheck
from app.services.service_advisor.ec2.checks.instance_type_check import InstanceTypeCheck

class EC2Advisor(BaseAdvisor):
    """
    EC2 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        EC2 어드바이저 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        super().__init__(session)
        self.aws_client = AWSClient(session)
    
    def _register_checks(self) -> None:
        """EC2 서비스에 대한 검사 항목을 등록합니다."""
        
        # 보안 그룹 검사
        security_check = SecurityGroupCheck()
        self.register_check(
            check_id=security_check.check_id,
            name='보안 그룹 설정 검사',
            description='EC2 인스턴스의 보안 그룹 설정을 검사하여 0.0.0.0/0과 같이 과도하게 개방된 인바운드 규칙이 있는지 확인합니다. SSH(22), RDP(3389), 데이터베이스 포트(3306, 5432) 등 중요 서비스가 인터넷에 노출되어 있는 경우 보안 위험을 식별하고 개선 방안을 제시합니다.',
            function=security_check.run,
            category='보안',
            severity='high'
        )
        
        # 인스턴스 타입 최적화 검사
        instance_check = InstanceTypeCheck()
        self.register_check(
            check_id=instance_check.check_id,
            name='인스턴스 타입 최적화',
            description='CloudWatch 지표를 분석하여 EC2 인스턴스의 CPU 사용률을 확인하고, 과다 프로비저닝되거나 부족한 인스턴스를 식별합니다. 평균 CPU 사용률이 10% 미만인 경우 다운사이징을, 80% 이상인 경우 업그레이드를 권장하여 비용 효율성과 성능을 최적화합니다.',
            function=instance_check.run,
            category='비용 최적화',
            severity='medium'
        )