import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL,
    create_unified_check_result, create_resource_result, create_error_result
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    Lambda 함수의 런타임 버전을 검사합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda', role_arn=role_arn)
        
        # Lambda 함수 정보 수집
        functions = lambda_client.list_functions()
        
        # 함수 분석 결과
        function_analysis = []
        
        # 지원 종료된 런타임 목록 (AWS 공식 발표 기준)
        deprecated_runtimes = [
            'nodejs10.x', 'nodejs8.10', 'nodejs6.10', 'nodejs4.3',
            'python2.7', 'python3.6', 'python3.7',
            'ruby2.5', 'ruby2.7',
            'dotnetcore2.1', 'dotnetcore1.0', 'dotnetcore3.1',
            'java8',
            'go1.x'  # go1.x는 2024년 지원 종료 예정
        ]
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            runtime = function['Runtime']
            
            # 런타임 분석
            status = RESOURCE_STATUS_PASS  # 기본값은 통과
            advice = None
            status_text = None
            
            if runtime in deprecated_runtimes:
                status = RESOURCE_STATUS_FAIL
                status_text = '지원 종료'
                advice = f'런타임 {runtime}은 지원 종료되었거나 곧 지원 종료될 예정입니다. 지원되는 런타임으로 업그레이드하세요.'
            else:
                status_text = '지원 중'
                advice = f'런타임 {runtime}은 현재 지원되고 있습니다.'
            
            # 표준화된 리소스 결과 생성
            function_result = create_resource_result(
                resource_id=function_name,
                status=status,
                status_text=status_text,
                advice=advice,
                function_name=function_name
            )
            
            function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        
        # 지원 종료 함수 카운트
        deprecated_count = len(failed_functions)
        
        # 권장사항 생성
        recommendations = [
            '지원 종료된 런타임만 업그레이드가 필요합니다.',
            '지원 중인 런타임은 안정적으로 사용 가능합니다.',
            '런타임 업그레이드 시 코드 호환성을 테스트하세요.'
        ]
        
        # 전체 상태 결정 및 결과 생성
        if deprecated_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {deprecated_count}개가 지원 종료된 런타임을 사용하고 있습니다.'
            status = STATUS_WARNING
        else:
            message = f'모든 함수({len(passed_functions)}개)가 지원되는 런타임을 사용하고 있습니다.'
            status = STATUS_OK
        
        return create_unified_check_result(
            status=status,
            message=message,
            resources=function_analysis,
            recommendations=recommendations,
            check_id='lambda-runtime'
        )
    
    except Exception as e:
        return create_error_result(f'Lambda 런타임 검사 중 오류가 발생했습니다: {str(e)}')