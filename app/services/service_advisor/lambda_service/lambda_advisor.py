import boto3
from typing import Dict, List, Any, Optional
from app.services.service_advisor.common.base_advisor import BaseAdvisor
from app.services.service_advisor.common.aws_client import AWSClient
from app.services.service_advisor.lambda_service.checks import (
    memory_size_check,
    timeout_check,
    runtime_check,
    provisioned_concurrency_check,
    code_signing_check,
    least_privilege_check
)

class LambdaAdvisor(BaseAdvisor):
    """
    Lambda 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        Lambda 어드바이저 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        super().__init__(session)
        self.aws_client = AWSClient(session)
    
    def _register_checks(self) -> None:
        """Lambda 서비스에 대한 검사 항목을 등록합니다."""
        
        # 메모리 크기 최적화 검사
        self.register_check(
            check_id='lambda-memory-size',
            name='메모리 크기 최적화',
            description='CloudWatch 지표를 분석하여 Lambda 함수의 메모리 사용량을 확인하고, 과다 프로비저닝되거나 부족한 메모리를 식별합니다. 메모리 사용률이 낮은 경우 다운사이징을, 높은 경우 업그레이드를 권장하여 비용 효율성과 성능을 최적화합니다.',
            function=memory_size_check.run,
            category='비용 최적화',
            severity='medium'
        )
        
        # 타임아웃 설정 검사
        self.register_check(
            check_id='lambda-timeout',
            name='타임아웃 설정 최적화',
            description='Lambda 함수의 실행 시간과 타임아웃 설정을 분석하여 최적화가 필요한 함수를 식별합니다. 실행 시간이 타임아웃에 근접하거나 타임아웃이 과도하게 설정된 경우 개선 방안을 제시합니다.',
            function=timeout_check.run,
            category='성능',
            severity='medium'
        )
        
        # 런타임 버전 검사
        self.register_check(
            check_id='lambda-runtime',
            name='런타임 버전 최적화',
            description='Lambda 함수의 런타임 버전을 검사하여 오래된 버전을 사용하는 함수를 식별합니다. 최신 런타임 버전으로 업그레이드하여 보안 및 성능을 개선할 수 있는 방안을 제시합니다.',
            function=runtime_check.run,
            category='보안',
            severity='high'
        )
        

        
        # 프로비저닝된 동시성 검사
        self.register_check(
            check_id='lambda-provisioned-concurrency',
            name='프로비저닝된 동시성 최적화',
            description='Lambda 함수의 호출 패턴을 분석하여 프로비저닝된 동시성 설정이 필요한 함수를 식별합니다. 호출 빈도가 높은 함수에 프로비저닝된 동시성을 설정하여 콜드 스타트 지연 시간을 줄이고 성능을 개선하는 방안을 제시합니다.',
            function=provisioned_concurrency_check.run,
            category='성능',
            severity='medium'
        )
        
        # 코드 서명 검사
        self.register_check(
            check_id='lambda-code-signing',
            name='코드 서명 구성',
            description='Lambda 함수의 코드 서명 구성을 검사하여 프로덕션 환경에서 코드 무결성과 보안을 강화할 수 있는 방안을 제시합니다. 코드 서명을 통해 승인된 코드만 배포되도록 하여 보안을 강화합니다.',
            function=code_signing_check.run,
            category='보안',
            severity='medium'
        )
        
        # 최소 권한 원칙 검사
        self.register_check(
            check_id='lambda-least-privilege',
            name='최소 권한 원칙 준수',
            description='Lambda 함수의 실행 역할(IAM Role)이 최소 권한 원칙을 따르는지 검사합니다. 과도하게 넓은 권한이 부여된 역할을 식별하고, 필요한 권한만 부여하도록 IAM 정책을 수정하는 방안을 제시합니다.',
            function=least_privilege_check.run,
            category='보안',
            severity='high'
        )