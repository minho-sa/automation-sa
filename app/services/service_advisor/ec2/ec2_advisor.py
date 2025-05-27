import boto3
from typing import Dict, List, Any
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.ec2.checks import (
    security_group_check,
    instance_type_check,
    stopped_instance_check,
    ebs_optimization_check,
    tag_compliance_check
)

class EC2Advisor(BaseAdvisor):
    """
    EC2 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def _register_checks(self) -> None:
        """EC2 서비스에 대한 검사 항목을 등록합니다."""
        
        # 보안 그룹 검사
        self.register_check(
            check_id='ec2-security-group',
            name='보안 그룹 설정 검사',
            description='EC2 인스턴스의 보안 그룹 설정을 검사하여 과도하게 개방된 포트가 있는지 확인합니다.',
            function=security_group_check.run,
            category='보안',
            severity='high'
        )
        
        # 인스턴스 타입 최적화 검사
        self.register_check(
            check_id='ec2-instance-type',
            name='인스턴스 타입 최적화',
            description='EC2 인스턴스 타입이 워크로드에 적합한지 검사하고 비용 최적화 방안을 제안합니다.',
            function=instance_type_check.run,
            category='비용 최적화',
            severity='medium'
        )
        
        # 중지된 인스턴스 검사
        self.register_check(
            check_id='ec2-stopped-instances',
            name='중지된 인스턴스 검사',
            description='장기간 중지된 EC2 인스턴스를 식별하여 불필요한 비용 발생을 방지합니다.',
            function=stopped_instance_check.run,
            category='비용 최적화',
            severity='low'
        )
        
        # EBS 최적화 검사
        self.register_check(
            check_id='ec2-ebs-optimization',
            name='EBS 볼륨 최적화',
            description='EBS 볼륨의 사용량과 성능을 분석하여 최적화 방안을 제안합니다.',
            function=ebs_optimization_check.run,
            category='성능',
            severity='medium'
        )
        
        # 태그 규정 준수 검사
        self.register_check(
            check_id='ec2-tag-compliance',
            name='태그 규정 준수 검사',
            description='EC2 리소스에 필수 태그가 적용되어 있는지 확인합니다.',
            function=tag_compliance_check.run,
            category='거버넌스',
            severity='low'
        )