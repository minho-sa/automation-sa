import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_UNKNOWN,
    create_unified_check_result, create_resource_result, create_error_result
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    Lambda 함수의 프로비저닝된 동시성 설정을 검사합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda', role_arn=role_arn)
        cloudwatch = create_boto3_client('cloudwatch', role_arn=role_arn)
        
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
                provisioned_concurrency_configs = lambda_client.list_provisioned_concurrency_configs(
                    FunctionName=function_name
                )
                has_provisioned_concurrency = len(provisioned_concurrency_configs.get('ProvisionedConcurrencyConfigs', [])) > 0
            except Exception:
                has_provisioned_concurrency = False
            
            # 호출 지표 가져오기
            try:
                invocations_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1시간 간격
                    Statistics=['Sum']
                )
                
                # 콜드 스타트 지표 가져오기
                cold_start_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Duration',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1시간 간격
                    Statistics=['Average', 'Maximum']
                )
                
                invocations_datapoints = invocations_response.get('Datapoints', [])
                cold_start_datapoints = cold_start_response.get('Datapoints', [])
                
                if invocations_datapoints:
                    # 시간당 평균 호출 수 계산
                    total_invocations = sum(point['Sum'] for point in invocations_datapoints)
                    avg_hourly_invocations = total_invocations / len(invocations_datapoints)
                    
                    # 프로비저닝된 동시성 분석
                    status = RESOURCE_STATUS_PASS  # 기본값은 통과
                    advice = None
                    status_text = None
                    
                    if avg_hourly_invocations > 10 and not has_provisioned_concurrency:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '최적화 필요'
                        advice = f'이 함수는 시간당 평균 {round(avg_hourly_invocations, 2)}회 호출되지만 프로비저닝된 동시성이 설정되어 있지 않습니다. 콜드 스타트 지연 시간을 줄이기 위해 프로비저닝된 동시성 설정을 고려하세요.'
                    elif avg_hourly_invocations < 5 and has_provisioned_concurrency:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '최적화 필요'
                        advice = f'이 함수는 시간당 평균 {round(avg_hourly_invocations, 2)}회만 호출되지만 프로비저닝된 동시성이 설정되어 있습니다. 비용 절감을 위해 프로비저닝된 동시성 설정을 제거하는 것을 고려하세요.'
                    else:
                        status_text = '최적화됨'
                        if has_provisioned_concurrency:
                            advice = f'이 함수는 시간당 평균 {round(avg_hourly_invocations, 2)}회 호출되며 프로비저닝된 동시성이 적절하게 설정되어 있습니다.'
                        else:
                            advice = f'이 함수는 시간당 평균 {round(avg_hourly_invocations, 2)}회 호출되며 프로비저닝된 동시성이 필요하지 않습니다.'
                    
                    # 표준화된 리소스 결과 생성
                    function_result = create_resource_result(
                        resource_id=function_name,
                        status=status,
                        status_text=status_text,
                        advice=advice,
                        function_name=function_name
                    )
                    
                    function_analysis.append(function_result)
                else:
                    # 표준화된 리소스 결과 생성 (데이터 없음)
                    status_text = '데이터 부족'
                    advice = '충분한 CloudWatch 메트릭 데이터가 없습니다. 최소 14일 이상의 데이터가 수집된 후 다시 검사하세요.'
                    
                    function_result = create_resource_result(
                        resource_id=function_name,
                        status=RESOURCE_STATUS_UNKNOWN,
                        status_text=status_text,
                        advice=advice,
                        function_name=function_name
                    )
                    
                    function_analysis.append(function_result)
                    
            except Exception as e:
                # 표준화된 리소스 결과 생성 (오류)
                status_text = '오류'
                advice = f'CloudWatch 메트릭 액세스 권한을 확인하고 다시 시도하세요.'
                
                function_result = create_resource_result(
                    resource_id=function_name,
                    status=RESOURCE_STATUS_UNKNOWN,
                    status_text=status_text,
                    advice=advice,
                    function_name=function_name
                )
                
                function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        unknown_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_UNKNOWN]
        
        # 최적화 필요 함수 카운트
        optimization_needed_count = len(failed_functions)
        unknown_count = len(unknown_functions)
        
        # 권장사항 생성
        recommendations = [
            '호출 빈도가 높은 함수에 프로비저닝된 동시성을 설정하여 콜드 스타트 지연 시간을 줄이세요.',
            '호출 빈도가 낮은 함수에는 프로비저닝된 동시성을 설정하지 마세요.',
            '프로비저닝된 동시성은 추가 비용이 발생하므로 비용과 성능 사이의 균형을 고려하세요.',
            '정기적으로 함수의 호출 패턴을 분석하여 프로비저닝된 동시성 설정을 최적화하세요.'
        ]
        
        # 전체 상태 결정 및 결과 생성
        if optimization_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {optimization_needed_count}개가 프로비저닝된 동시성 설정 최적화가 필요합니다.'
            status = STATUS_WARNING
        elif unknown_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {unknown_count}개가 데이터 부족으로 검사가 불가능합니다.'
            status = STATUS_WARNING
        else:
            message = f'모든 함수({len(passed_functions)}개)가 적절한 프로비저닝된 동시성 설정으로 구성되어 있습니다.'
            status = STATUS_OK
        
        return create_unified_check_result(
            status=status,
            message=message,
            resources=function_analysis,
            recommendations=recommendations,
            check_id='lambda-provisioned-concurrency'
        )
    
    except Exception as e:
        return create_error_result(f'Lambda 프로비저닝된 동시성 검사 중 오류가 발생했습니다: {str(e)}')