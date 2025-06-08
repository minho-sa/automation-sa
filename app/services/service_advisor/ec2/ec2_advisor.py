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