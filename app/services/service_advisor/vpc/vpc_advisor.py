"""
VPC 서비스 어드바이저 클래스
"""
import boto3
from typing import Dict, List, Any, Optional
from app.services.service_advisor.common.base_advisor import BaseAdvisor
from app.services.service_advisor.common.aws_client import AWSClient

class VPCAdvisor(BaseAdvisor):
    """
    VPC 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        VPC 어드바이저 초기화
        
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
        print(f"VPCAdvisor: 검사 항목 등록 - {check_id}, {name}")
        self.checks[check_id] = {
            'id': check_id,
            'name': name,
            'description': description,
            'function': function,
            'category': category,
            'severity': severity
        }
    
    def _register_checks(self) -> None:
        """VPC 서비스에 대한 검사 항목을 등록합니다."""
        print("VPCAdvisor: _register_checks 메서드 호출됨")
        
        try:
            # 미사용 탄력적 IP 검사
            from app.services.service_advisor.vpc.checks.unused_eip_check import UnusedEIPCheck
            unused_eip_check = UnusedEIPCheck()
            self.register_check(
                check_id=unused_eip_check.check_id,
                name='사용하지 않는 탄력적 IP 검사',
                description='연결되지 않은 Elastic IP 주소를 검사합니다. 인스턴스나 네트워크 인터페이스에 연결되지 않은 EIP는 시간당 요금이 부과되므로 불필요한 비용을 발생시킵니다.',
                function=unused_eip_check.run,
                category='비용 최적화',
                severity='medium'
            )
            
            # 비활성 NAT Gateway 검사
            from app.services.service_advisor.vpc.checks.unused_nat_gateway_check import UnusedNATGatewayCheck
            unused_nat_gw_check = UnusedNATGatewayCheck()
            self.register_check(
                check_id=unused_nat_gw_check.check_id,
                name='비활성 NAT Gateway 검사',
                description='비활성 상태의 NAT Gateway를 검사합니다. Failed, Deleting 상태의 NAT Gateway는 불필요한 비용을 발생시킬 수 있으므로 정리가 필요합니다.',
                function=unused_nat_gw_check.run,
                category='비용 최적화',
                severity='medium'
            )
            
            # 비활성 VPC Endpoint 검사
            from app.services.service_advisor.vpc.checks.unused_vpc_endpoint_check import UnusedVPCEndpointCheck
            unused_vpc_endpoint_check = UnusedVPCEndpointCheck()
            self.register_check(
                check_id=unused_vpc_endpoint_check.check_id,
                name='비활성 VPC Endpoint 검사',
                description='비활성 상태의 VPC Endpoint를 검사합니다. Failed, Rejected 상태의 VPC Endpoint는 불필요한 비용을 발생시킬 수 있으므로 정리가 필요합니다. Interface 타입의 경우 시간당 요금이 부과됩니다.',
                function=unused_vpc_endpoint_check.run,
                category='비용 최적화',
                severity='medium'
            )
            
            print(f"VPCAdvisor: 검사 항목 등록 완료, 총 {len(self.checks)}개 항목")
        except Exception as e:
            print(f"VPCAdvisor: 검사 항목 등록 중 오류 발생 - {str(e)}")
    
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