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
    Lambda 함수의 타임아웃 설정이 적절한지 검사합니다.
    
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
            timeout = function['Timeout']
            
            # 함수 태그 가져오기
            try:
                tags_response = lambda_client.list_tags(Resource=function['FunctionArn'])
                tags = tags_response.get('Tags', {})
            except Exception:
                tags = {}
            
            # 실행 시간 데이터 가져오기
            try:
                duration_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Duration',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1시간 간격
                    Statistics=['Average', 'Maximum']
                )
                
                datapoints = duration_response.get('Datapoints', [])
                
                if datapoints:
                    avg_duration = sum(point['Average'] for point in datapoints) / len(datapoints)
                    max_duration = max(point['Maximum'] for point in datapoints) if datapoints else 0
                    
                    # 타임아웃 설정 최적화 분석
                    status = RESOURCE_STATUS_PASS  # 기본값은 통과
                    advice = None
                    status_text = None
                    
                    # 타임아웃 대비 실행 시간 비율 계산
                    timeout_ms = timeout * 1000  # 타임아웃을 밀리초로 변환
                    max_duration_ratio = (max_duration / timeout_ms) * 100 if timeout_ms > 0 else 0
                    
                    if max_duration_ratio > 80:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '위험'
                        advice = f'최대 실행 시간({round(max_duration, 2)}ms)이 타임아웃({timeout}초)에 근접합니다. 타임아웃을 늘리는 것을 고려하세요.'
                    elif max_duration_ratio < 10 and timeout > 10:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '최적화 필요'
                        advice = f'최대 실행 시간({round(max_duration, 2)}ms)이 타임아웃({timeout}초)보다 훨씬 짧습니다. 타임아웃을 줄이는 것을 고려하세요.'
                    else:
                        status_text = '최적화됨'
                        advice = f'타임아웃 설정이 적절합니다. 최대 실행 시간({round(max_duration, 2)}ms)이 타임아웃({timeout}초) 대비 적절한 범위 내에 있습니다.'
                    
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
            'Lambda 함수의 타임아웃 설정을 실제 실행 시간에 맞게 조정하세요.',
            '타임아웃이 너무 짧으면 함수가 중간에 종료될 수 있습니다.',
            '타임아웃이 너무 길면 오류 발생 시 불필요한 대기 시간이 발생할 수 있습니다.',
            '실행 시간이 길어지는 함수는 코드 최적화를 고려하세요.'
        ]
        
        # 전체 상태 결정 및 결과 생성
        if optimization_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {optimization_needed_count}개가 타임아웃 설정 최적화가 필요합니다.'
            status = STATUS_WARNING
        elif unknown_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {unknown_count}개가 데이터 부족으로 검사가 불가능합니다.'
            status = STATUS_WARNING
        else:
            message = f'모든 함수({len(passed_functions)}개)가 적절한 타임아웃 설정으로 구성되어 있습니다.'
            status = STATUS_OK
        
        return create_unified_check_result(
            status=status,
            message=message,
            resources=function_analysis,
            recommendations=recommendations,
            check_id='lambda-timeout'
        )
    
    except Exception as e:
        return create_error_result(f'Lambda 타임아웃 설정 검사 중 오류가 발생했습니다: {str(e)}')