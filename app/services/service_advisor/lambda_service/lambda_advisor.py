import boto3
from typing import Dict, List, Any
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.lambda_service.checks import (
    memory_size_check,
    timeout_check,
    runtime_check,
    tag_check
)

class LambdaAdvisor(BaseAdvisor):
    """
    Lambda 서비스에 대한 어드바이저 클래스입니다.
    """
    
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
            category='성능 최적화',
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
        
        # 태그 관리 검사
        self.register_check(
            check_id='lambda-tags',
            name='태그 관리',
            description='Lambda 함수의 태그 관리 상태를 검사하여 태그가 없거나 부족한 함수를 식별합니다. 리소스 관리 및 비용 할당을 위한 적절한 태그 추가 방안을 제시합니다.',
            function=tag_check.run,
            category='거버넌스',
            severity='low'
        )