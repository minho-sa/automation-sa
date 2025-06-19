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
    
    def register_check(self, check_id, name, description, function, category, severity):
        """
        검사 항목을 등록합니다.
        
        Args:
            check_id: 검사 ID
            name: 검사 이름
            description: 검사 설명
            function: 검사 실행 함수
            category: 검사 카테고리
            severity: 심각도
        """
        print(f"EC2Advisor: 검사 항목 등록 - {check_id}, {name}")
        self.checks[check_id] = {
            'id': check_id,
            'name': name,
            'description': description,
            'function': function,
            'category': category,
            'severity': severity
        }
    
    def _register_checks(self) -> None:
        """EC2 서비스에 대한 검사 항목을 등록합니다."""
        print("EC2Advisor: _register_checks 메서드 호출됨")
        
        try:
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
            

            
            # EC2 퍼블릭 인스턴스 검사
            from app.services.service_advisor.ec2.checks.public_instance_check import PublicInstanceCheck
            public_instance_check = PublicInstanceCheck()
            self.register_check(
                check_id=public_instance_check.check_id,
                name='EC2 퍼블릭 인스턴스 검사',
                description='EC2 인스턴스의 퍼블릭 IP 할당 상태를 검사합니다. 불필요하게 퍼블릭 액세스가 허용된 인스턴스를 식별하고 보안 강화를 위한 네트워크 구성 개선 방안을 제시합니다.',
                function=public_instance_check.run,
                category='보안',
                severity='medium'
            )
            
            # EBS 암호화 검사
            from app.services.service_advisor.ec2.checks.ebs_encryption_check import EBSEncryptionCheck
            ebs_encryption_check = EBSEncryptionCheck()
            self.register_check(
                check_id=ebs_encryption_check.check_id,
                name='EBS 볼륨 암호화 검사',
                description='EBS 볼륨의 암호화 설정을 검사합니다. 암호화되지 않은 볼륨을 식별하고 데이터 보호를 위한 암호화 활성화 방안을 제시합니다.',
                function=ebs_encryption_check.run,
                category='보안',
                severity='high'
            )
            
            # 미사용 리소스 검사
            from app.services.service_advisor.ec2.checks.unused_resources_check import UnusedResourcesCheck
            unused_resources_check = UnusedResourcesCheck()
            self.register_check(
                check_id=unused_resources_check.check_id,
                name='미사용 리소스 검사',
                description='사용되지 않는 Elastic IP와 EBS 볼륨을 검사합니다. 불필요한 비용을 발생시키는 미사용 리소스를 식별하고 비용 최적화 방안을 제시합니다.',
                function=unused_resources_check.run,
                category='비용 최적화',
                severity='medium'
            )
            
            # 인스턴스 모니터링 검사
            from app.services.service_advisor.ec2.checks.instance_monitoring_check import InstanceMonitoringCheck
            monitoring_check = InstanceMonitoringCheck()
            self.register_check(
                check_id=monitoring_check.check_id,
                name='인스턴스 모니터링 설정 검사',
                description='EC2 인스턴스의 CloudWatch 모니터링 설정을 검사합니다. 상세 모니터링 활성화 여부를 확인하고 성능 모니터링 개선 방안을 제시합니다.',
                function=monitoring_check.run,
                category='운영',
                severity='low'
            )
            
            # 인스턴스 태그 검사
            from app.services.service_advisor.ec2.checks.instance_tags_check import InstanceTagsCheck
            tags_check = InstanceTagsCheck()
            self.register_check(
                check_id=tags_check.check_id,
                name='인스턴스 태그 관리 검사',
                description='EC2 인스턴스의 태그 설정을 검사합니다. 필수 태그(Name, Environment, Owner) 누락을 확인하고 리소스 관리 개선 방안을 제시합니다.',
                function=tags_check.run,
                category='거버넌스',
                severity='low'
            )
            
            # 인스턴스 생명주기 검사
            from app.services.service_advisor.ec2.checks.instance_lifecycle_check import InstanceLifecycleCheck
            lifecycle_check = InstanceLifecycleCheck()
            self.register_check(
                check_id=lifecycle_check.check_id,
                name='인스턴스 생명주기 검사',
                description='오래된 EC2 인스턴스를 식별합니다. 1년 이상 실행된 인스턴스를 찾아 업데이트나 교체 필요성을 평가하고 보안 및 성능 개선 방안을 제시합니다.',
                function=lifecycle_check.run,
                category='운영',
                severity='medium'
            )
            
            # 인스턴스 백업 검사
            from app.services.service_advisor.ec2.checks.instance_backup_check import InstanceBackupCheck
            backup_check = InstanceBackupCheck()
            self.register_check(
                check_id=backup_check.check_id,
                name='인스턴스 백업 상태 검사',
                description='EC2 인스턴스의 백업(스냅샷) 상태를 검사합니다. 최근 7일 내 백업이 없는 인스턴스를 식별하고 데이터 보호를 위한 백업 정책 수립 방안을 제시합니다.',
                function=backup_check.run,
                category='데이터 보호',
                severity='high'
            )
            
            # 종료 보호 검사
            from app.services.service_advisor.ec2.checks.instance_termination_protection_check import InstanceTerminationProtectionCheck
            protection_check = InstanceTerminationProtectionCheck()
            self.register_check(
                check_id=protection_check.check_id,
                name='인스턴스 종료 보호 검사',
                description='프로덕션 환경의 EC2 인스턴스 종료 보호 설정을 검사합니다. 중요한 인스턴스의 실수로 인한 종료를 방지하기 위한 보호 설정 방안을 제시합니다.',
                function=protection_check.run,
                category='보안',
                severity='medium'
            )
            
            # 인스턴스 세대 검사
            from app.services.service_advisor.ec2.checks.instance_generation_check import InstanceGenerationCheck
            generation_check = InstanceGenerationCheck()
            self.register_check(
                check_id=generation_check.check_id,
                name='인스턴스 세대 검사',
                description='구세대 EC2 인스턴스 타입을 식별합니다. 성능과 비용 효율성 향상을 위해 최신 세대 인스턴스로의 업그레이드 필요성을 평가하고 개선 방안을 제시합니다.',
                function=generation_check.run,
                category='성능 최적화',
                severity='medium'
            )
            
            print(f"EC2Advisor: 검사 항목 등록 완료, 총 {len(self.checks)}개 항목")
        except Exception as e:
            print(f"EC2Advisor: 검사 항목 등록 중 오류 발생 - {str(e)}")
    
    # 추상 메서드 구현
    def collect_data(self) -> Dict[str, Any]:
        """
        AWS에서 필요한 데이터를 수집합니다.
        
        Returns:
            Dict[str, Any]: 수집된 데이터
        """
        return {}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        수집된 데이터를 분석하여 결과를 생성합니다.
        
        Args:
            collected_data: 수집된 데이터
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        return {}
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        분석 결과를 바탕으로 권장사항을 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            List[str]: 권장사항 목록
        """
        return []
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """
        분석 결과를 바탕으로 메시지를 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            str: 결과 메시지
        """
        return ""