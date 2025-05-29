import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run() -> Dict[str, Any]:
    """
    Lambda 함수의 프로비저닝된 동시성 설정을 검사하고 최적화 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        cloudwatch = create_boto3_client('cloudwatch')
        
        # Lambda 함수 정보 수집
        functions = lambda_client.list_functions()
        
        # 함수 분석 결과
        function_analysis = []
        
        # 현재 시간 설정
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=14)  # 2주 데이터 분석
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            
            # 프로비저닝된 동시성 설정 확인
            try:
                provisioned_config = lambda_client.get_function_concurrency(
                    FunctionName=function_name
                )
                provisioned_concurrency = provisioned_config.get('ReservedConcurrentExecutions')
            except Exception:
                provisioned_concurrency = None
            
            # 호출 지표 데이터 가져오기
            try:
                invocation_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1시간 간격
                    Statistics=['Sum']
                )
                
                concurrent_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='ConcurrentExecutions',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1시간 간격
                    Statistics=['Maximum']
                )
                
                invocation_datapoints = invocation_response.get('Datapoints', [])
                concurrent_datapoints = concurrent_response.get('Datapoints', [])
                
                if invocation_datapoints and concurrent_datapoints:
                    # 시간당 평균 호출 수 계산
                    total_invocations = sum(point['Sum'] for point in invocation_datapoints)
                    hours = len(invocation_datapoints)
                    avg_invocations_per_hour = total_invocations / hours if hours > 0 else 0
                    
                    # 최대 동시 실행 수
                    max_concurrent = max(point['Maximum'] for point in concurrent_datapoints) if concurrent_datapoints else 0
                    
                    # 프로비저닝된 동시성 최적화 분석
                    status = RESOURCE_STATUS_PASS  # 기본값은 통과
                    advice = None
                    status_text = None
                    
                    # 호출 빈도가 높고 프로비저닝된 동시성이 없는 경우
                    if avg_invocations_per_hour > 100 and max_concurrent > 10 and not provisioned_concurrency:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '최적화 필요'
                        advice = f'호출 빈도가 높지만(시간당 평균: {round(avg_invocations_per_hour, 2)}, 최대 동시 실행: {round(max_concurrent, 2)}) 프로비저닝된 동시성이 설정되어 있지 않습니다. 콜드 스타트 지연 시간을 줄이기 위해 프로비저닝된 동시성을 설정하세요.'
                    else:
                        status_text = '최적화됨'
                        advice = f'현재 함수의 호출 패턴(시간당 평균: {round(avg_invocations_per_hour, 2)}, 최대 동시 실행: {round(max_concurrent, 2)})에 따르면 프로비저닝된 동시성 설정이 필요하지 않거나 이미 적절하게 구성되어 있습니다.'
                    
                    # 표준화된 리소스 결과 생성
                    function_result = create_resource_result(
                        resource_id=function_name,
                        status=status,
                        advice=advice,
                        status_text=status_text,
                        function_name=function_name,
                        provisioned_concurrency=provisioned_concurrency,
                        avg_invocations_per_hour=round(avg_invocations_per_hour, 2),
                        max_concurrent_executions=round(max_concurrent, 2)
                    )
                    
                    function_analysis.append(function_result)
                else:
                    # 표준화된 리소스 결과 생성 (데이터 없음)
                    status_text = '데이터 부족'
                    advice = '충분한 CloudWatch 메트릭 데이터가 없습니다. 최소 14일 이상의 데이터가 수집된 후 다시 검사하세요.'
                    
                    function_result = create_resource_result(
                        resource_id=function_name,
                        status=RESOURCE_STATUS_UNKNOWN,
                        advice=advice,
                        status_text=status_text,
                        function_name=function_name,
                        provisioned_concurrency=provisioned_concurrency,
                        avg_invocations_per_hour='N/A',
                        max_concurrent_executions='N/A'
                    )
                    
                    function_analysis.append(function_result)
                    
            except Exception as e:
                # 표준화된 리소스 결과 생성 (오류)
                status_text = '오류'
                advice = f'CloudWatch 메트릭 액세스 권한을 확인하고 다시 시도하세요.'
                
                function_result = create_resource_result(
                    resource_id=function_name,
                    status='error',
                    advice=advice,
                    status_text=status_text,
                    function_name=function_name,
                    provisioned_concurrency=provisioned_concurrency,
                    avg_invocations_per_hour='Error',
                    max_concurrent_executions='Error'
                )
                
                function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        unknown_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_UNKNOWN or f['status'] == 'error']
        
        # 최적화 필요 함수 카운트
        optimization_needed_count = len(failed_functions)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 프로비저닝된 동시성 설정이 필요한 함수 찾기
        if failed_functions:
            recommendations.append(f'호출 빈도가 높은 {len(failed_functions)}개 함수에 프로비저닝된 동시성을 설정하여 콜드 스타트 지연 시간을 줄이세요. (영향받는 함수: {", ".join([f["function_name"] for f in failed_functions])})')
        
        # 데이터 준비
        data = {
            'functions': function_analysis,
            'passed_functions': passed_functions,
            'failed_functions': failed_functions,
            'unknown_functions': unknown_functions,
            'optimization_needed_count': optimization_needed_count,
            'total_functions_count': len(function_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if optimization_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {optimization_needed_count}개가 프로비저닝된 동시성 설정이 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 함수({len(passed_functions)}개)가 적절한 프로비저닝된 동시성 설정을 가지고 있거나 필요하지 않습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Lambda 프로비저닝된 동시성 검사 중 오류가 발생했습니다: {str(e)}')