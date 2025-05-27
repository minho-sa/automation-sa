import boto3
from typing import Dict, List, Any
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.ec2.checks import (
    security_group_check,
    instance_type_check,
    stopped_instance_check,
    ebs_optimization_check,
    tag_compliance_check,
    ami_age_check,
    auto_scaling_check,
    instance_metadata_check
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
            description='EC2 인스턴스의 보안 그룹 설정을 검사하여 0.0.0.0/0과 같이 과도하게 개방된 인바운드 규칙이 있는지 확인합니다. SSH(22), RDP(3389), 데이터베이스 포트(3306, 5432) 등 중요 서비스가 인터넷에 노출되어 있는 경우 보안 위험을 식별하고 개선 방안을 제시합니다.',
            function=security_group_check.run,
            category='보안',
            severity='high'
        )
        
        # 인스턴스 타입 최적화 검사
        self.register_check(
            check_id='ec2-instance-type',
            name='인스턴스 타입 최적화',
            description='CloudWatch 지표를 분석하여 EC2 인스턴스의 CPU 사용률을 확인하고, 과다 프로비저닝되거나 부족한 인스턴스를 식별합니다. 평균 CPU 사용률이 10% 미만인 경우 다운사이징을, 80% 이상인 경우 업그레이드를 권장하여 비용 효율성과 성능을 최적화합니다.',
            function=instance_type_check.run,
            category='비용 최적화',
            severity='medium'
        )
        
        # 중지된 인스턴스 검사
        self.register_check(
            check_id='ec2-stopped-instances',
            name='중지된 인스턴스 검사',
            description='30일 이상 중지된 상태로 유지되는 EC2 인스턴스를 식별합니다. 중지된 인스턴스는 EBS 볼륨 비용이 계속 발생하므로, 장기간 사용하지 않는 인스턴스는 AMI를 생성한 후 종료하거나 스케줄링 도구를 사용하여 자동으로 시작/중지하는 방안을 제안합니다.',
            function=stopped_instance_check.run,
            category='비용 최적화',
            severity='low'
        )
        
        # EBS 최적화 검사
        self.register_check(
            check_id='ec2-ebs-optimization',
            name='EBS 볼륨 최적화',
            description='EBS 볼륨의 IOPS 사용량과 볼륨 타입을 분석하여 비용 효율적인 구성을 제안합니다. 사용량이 낮은 gp2 볼륨은 gp3로 변경하여 비용을 절감하고, 사용량이 높은 경우 io1/io2로 변경하여 성능을 향상시키는 방안을 제시합니다. 또한 연결되지 않은 미사용 볼륨을 식별하여 불필요한 비용 발생을 방지합니다.',
            function=ebs_optimization_check.run,
            category='성능',
            severity='medium'
        )
        
        # 태그 규정 준수 검사
        self.register_check(
            check_id='ec2-tag-compliance',
            name='태그 규정 준수 검사',
            description='EC2 인스턴스와 EBS 볼륨에 필수 태그(Name, Environment, Owner, Project)가 적용되어 있는지 확인합니다. 태그는 리소스 관리, 비용 할당, 액세스 제어에 중요하며, 태그 정책 구현 및 AWS Config 규칙을 통한 자동화된 태그 규정 준수 모니터링 방안을 제안합니다.',
            function=tag_compliance_check.run,
            category='거버넌스',
            severity='low'
        )
        
        # AMI 수명 검사
        self.register_check(
            check_id='ec2-ami-age',
            name='AMI 수명 검사',
            description='EC2 인스턴스가 사용 중인 AMI의 생성 시간을 분석하여 오래된 AMI를 식별합니다. 6개월 이상된 AMI는 "오래됨", 1년 이상된 AMI는 "매우 오래됨"으로 분류하고, 보안 패치가 누락되었을 가능성이 있는 오래된 AMI를 최신 버전으로 업데이트하는 방안을 제안합니다.',
            function=ami_age_check.run,
            category='보안',
            severity='medium'
        )
        
        # Auto Scaling 구성 검사
        self.register_check(
            check_id='ec2-auto-scaling',
            name='Auto Scaling 구성 검사',
            description='Auto Scaling 그룹의 구성을 검사하여 고가용성과 확장성을 개선할 수 있는 방안을 제안합니다. 단일 가용 영역에만 배포된 경우, 스케일링 정책이 없는 경우, 최소/최대 크기가 동일한 경우 등의 문제를 식별하고, 여러 가용 영역 사용, 적절한 스케일링 정책 구성, 워크로드 변동에 맞는 최소/최대 크기 설정 등을 권장합니다.',
            function=auto_scaling_check.run,
            category='성능',
            severity='medium'
        )
        
        # 인스턴스 메타데이터 서비스 검사
        self.register_check(
            check_id='ec2-metadata-service',
            name='인스턴스 메타데이터 서비스 검사',
            description='EC2 인스턴스의 메타데이터 서비스 설정을 검사하여 보안이 강화된 IMDSv2(인스턴스 메타데이터 서비스 버전 2)를 사용하고 있는지 확인합니다. IMDSv1은 SSRF(서버 사이드 요청 위조) 취약점에 노출될 수 있으므로, 모든 인스턴스에서 IMDSv2를 필수로 설정하도록 권장하고 구현 방안을 제시합니다.',
            function=instance_metadata_check.run,
            category='보안',
            severity='high'
        )