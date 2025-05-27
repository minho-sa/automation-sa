import boto3
from typing import Dict, List, Any
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.lambda_service.checks import (
    memory_size_check,
    runtime_version_check,
    timeout_setting_check,
    vpc_configuration_check,
    xray_tracing_check
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
            description='CloudWatch 지표를 분석하여 Lambda 함수의 메모리 사용률을 확인하고, 최적의 메모리 설정을 제안합니다. 메모리 사용률이 40% 미만인 함수는 메모리 크기를 줄여 비용을 절감하고, 90% 이상인 함수는 메모리를 늘려 성능을 개선합니다. Lambda 함수의 메모리 설정은 CPU 할당에도 영향을 미치므로 성능과 비용을 모두 고려한 최적화 방안을 제시합니다.',
            function=memory_size_check.run,
            category='비용 최적화',
            severity='medium'
        )
        
        # 런타임 버전 검사
        self.register_check(
            check_id='lambda-runtime-version',
            name='런타임 버전 검사',
            description='Lambda 함수가 최신 런타임 버전을 사용하고 있는지 확인합니다. 지원 종료 예정인 런타임(Node.js 18.x, Python 3.9 등)을 사용하는 함수를 식별하고, 보안 업데이트 및 성능 향상을 위해 최신 버전(Node.js 22.x, Python 3.13 등)으로 업그레이드하는 방안을 제안합니다. Amazon Linux 2023 기반 런타임은 더 긴 지원 기간을 제공하므로 우선적으로 고려하세요.',
            function=runtime_version_check.run,
            category='보안',
            severity='high'
        )
        
        # 타임아웃 설정 검사
        self.register_check(
            check_id='lambda-timeout-setting',
            name='타임아웃 설정 검사',
            description='CloudWatch 지표를 분석하여 Lambda 함수의 실행 시간을 확인하고, 타임아웃 설정의 적절성을 평가합니다. 최대 실행 시간이 타임아웃의 80% 이상인 함수는 타임아웃 증가 또는 코드 최적화가 필요하며, 타임아웃의 20% 미만만 사용하는 함수는 타임아웃을 줄여 오류 감지 시간을 단축하는 방안을 제안합니다. 장시간 실행되는 함수는 Step Functions 또는 분할 처리를 고려하도록 권장합니다.',
            function=timeout_setting_check.run,
            category='성능',
            severity='medium'
        )
        
        # VPC 구성 검사
        self.register_check(
            check_id='lambda-vpc-configuration',
            name='VPC 구성 검사',
            description='Lambda 함수의 VPC 구성을 검사하여 고가용성, 보안, 네트워크 액세스 측면에서 최적화 방안을 제안합니다. 단일 가용 영역에만 배포된 함수, 보안 그룹이 없거나 아웃바운드 규칙이 없는 함수를 식별하고, 여러 가용 영역 사용, 적절한 보안 그룹 구성, NAT 게이트웨이 또는 VPC 엔드포인트 설정 등을 권장합니다. VPC 내부 리소스에 접근하지 않는 함수는 VPC 구성을 제거하여 콜드 스타트 시간을 단축하는 방안도 제시합니다.',
            function=vpc_configuration_check.run,
            category='네트워크',
            severity='medium'
        )
        
        # X-Ray 추적 검사
        self.register_check(
            check_id='lambda-xray-tracing',
            name='X-Ray 추적 검사',
            description='Lambda 함수에 AWS X-Ray 추적이 활성화되어 있는지 확인합니다. X-Ray를 통해 함수 실행 시간, 오류, 다운스트림 서비스 호출 등을 모니터링하고 성능 병목 현상을 식별할 수 있습니다. X-Ray가 비활성화된 함수에 대해 활성화 방법을 안내하고, X-Ray SDK를 사용하여 상세한 추적 정보를 수집하는 방법과 서비스 맵을 통한 애플리케이션 구성 요소 간 관계 시각화 방안을 제안합니다.',
            function=xray_tracing_check.run,
            category='모니터링',
            severity='low'
        )