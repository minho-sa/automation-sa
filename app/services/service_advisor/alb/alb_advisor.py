import boto3
from typing import Dict, List, Any, Optional
from app.services.service_advisor.common.base_advisor import BaseAdvisor
from app.services.service_advisor.common.aws_client import AWSClient
from app.services.service_advisor.alb.checks import (
    unused_alb_check,
    ssl_certificate_check
)

class ALBAdvisor(BaseAdvisor):
    """
    ALB 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        ALB 어드바이저 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        super().__init__(session)
        self.aws_client = AWSClient(session)
        print(f"ALB 어드바이저 초기화 완료. 등록된 검사 항목 수: {len(self.checks)}")
        print(f"등록된 검사 항목: {list(self.checks.keys())}")
    
    def _register_checks(self) -> None:
        """ALB 서비스에 대한 검사 항목을 등록합니다."""
        print("ALB 검사 항목 등록 시작")
        
        # 미사용 ELB 검사
        self.register_check(
            check_id='alb-unused',
            name='미사용 ELB 검사',
            description='사용되지 않는 Elastic Load Balancer를 식별합니다. 리스너가 없거나, 타겟 그룹이 연결되지 않았거나, 정상 상태의 타겟이 없는 ELB를 찾아 비용 최적화 기회를 제공합니다.',
            function=unused_alb_check.run,
            category='비용 최적화',
            severity='medium'
        )
        print("미사용 ELB 검사 등록 완료")
        
        # ELB SSL 인증서 검사
        self.register_check(
            check_id='alb-ssl-certificate',
            name='SSL 인증서 검사',
            description='ELB의 SSL 인증서 설정을 검사합니다. HTTPS 사용 여부, 인증서 만료일, SSL 정책 버전, HTTP에서 HTTPS 리다이렉트 설정 등을 확인하여 보안 강화 방안을 제시합니다.',
            function=ssl_certificate_check.run,
            category='보안',
            severity='high'
        )
        print("SSL 인증서 검사 등록 완료")
        print(f"총 {len(self.checks)}개 검사 항목 등록 완료")
    
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