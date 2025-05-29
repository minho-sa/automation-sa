import boto3
from typing import Dict, List, Any
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.rds.checks import (
    backup_retention,
    multi_az,
    encryption_check,
    public_access_check,
    instance_sizing_check
)

class RDSAdvisor(BaseAdvisor):
    """
    RDS 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def _register_checks(self) -> None:
        """RDS 서비스에 대한 검사 항목을 등록합니다."""
        
        # 백업 보존 기간 검사
        self.register_check(
            check_id='rds-backup-retention',
            name='백업 보존 기간',
            description='RDS 인스턴스의 백업 보존 기간을 검사하여 데이터 보호 수준을 평가합니다. 백업이 비활성화되었거나 보존 기간이 짧은 인스턴스를 식별하고 개선 방안을 제시합니다.',
            function=backup_retention.run,
            category='데이터 보호',
            severity='high'
        )
        
        # 다중 AZ 구성 검사
        self.register_check(
            check_id='rds-multi-az',
            name='다중 AZ 구성',
            description='RDS 인스턴스의 다중 AZ 구성을 검사하여 고가용성 수준을 평가합니다. 프로덕션 환경에서 다중 AZ가 구성되지 않은 인스턴스를 식별하고 개선 방안을 제시합니다.',
            function=multi_az.run,
            category='고가용성',
            severity='medium'
        )
        
        # 암호화 설정 검사
        self.register_check(
            check_id='rds-encryption',
            name='암호화 설정',
            description='RDS 인스턴스의 저장 데이터 암호화 설정을 검사합니다. 암호화되지 않은 인스턴스를 식별하고 데이터 보호를 위한 암호화 활성화 방안을 제시합니다.',
            function=encryption_check.run,
            category='보안',
            severity='high'
        )
        
        # 공개 액세스 설정 검사
        self.register_check(
            check_id='rds-public-access',
            name='공개 액세스 설정',
            description='RDS 인스턴스의 공개 액세스 설정을 검사합니다. 공개적으로 액세스 가능한 인스턴스를 식별하고 보안 강화를 위한 개선 방안을 제시합니다.',
            function=public_access_check.run,
            category='보안',
            severity='high'
        )
        
        # 인스턴스 크기 최적화 검사
        self.register_check(
            check_id='rds-instance-sizing',
            name='인스턴스 크기 최적화',
            description='RDS 인스턴스의 리소스 사용률을 분석하여 크기 최적화 기회를 식별합니다. 과다 프로비저닝되거나 부족한 리소스를 가진 인스턴스에 대한 개선 방안을 제시합니다.',
            function=instance_sizing_check.run,
            category='비용 최적화',
            severity='medium'
        )