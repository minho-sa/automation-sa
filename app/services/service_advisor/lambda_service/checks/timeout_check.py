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
    Lambda 함수의 타임아웃 설정이 적절한지 검사하고 최적화 방안을 제안합니다.
    
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
                    avg_duration_ms = sum(point['Average'] for point in datapoints) / len(datapoints)
                    max_duration_ms = max(point['Maximum'] for point in datapoints) if datapoints else 0
                    
                    # 밀리초를 초로 변환
                    avg_duration = avg_duration_ms / 1000
                    max_duration = max_duration_ms / 1000
                    
                    # 타임아웃 설정 최적화 분석
                    status = RESOURCE_STATUS_PASS  # 기본값은 통과
                    advice = None
                    status_text = None
                    
                    # 타임아웃 여유 비율 계산 (최대 실행 시간 대비 타임아웃 설정)
                    if max_duration > 0:
                        timeout_margin = (timeout - max_duration) / timeout * 100
                    else:
                        timeout_margin = 100
                    
                    if max_duration > timeout * 0.9:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '타임아웃 위험'
                        advice = f'최대 실행 시간({round(max_duration, 2)}초)이 타임아웃 설정({timeout}초)에 근접합니다. 타임아웃을 늘리거나 함수 성능을 개선하세요.'
                    elif timeout > max_duration * 5 and timeout > 30:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '과도한 타임아웃'
                        advice = f'타임아웃 설정({timeout}초)이 최대 실행 시간({round(max_duration, 2)}초)보다 과도하게 높습니다. 타임아웃을 {max(round(max_duration * 2), 10)}초로 줄이는 것이 좋습니다.'
                    else:
                        status_text = '최적화됨'
                        advice = f'현재 타임아웃 설정({timeout}초)은 실행 시간(평균: {round(avg_duration, 2)}초, 최대: {round(max_duration, 2)}초)에 적절합니다.'
                    
                    # 표준화된 리소스 결과 생성
                    function_result = create_resource_result(
                        resource_id=function_name,
                        status=status,
                        advice=advice,
                        status_text=status_text,
                        function_name=function_name,
                        timeout=timeout,
                        avg_duration=round(avg_duration, 2),
                        max_duration=round(max_duration, 2),
                        timeout_margin=round(timeout_margin, 2) if timeout_margin <= 100 else 100
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
                        timeout=timeout,
                        avg_duration='N/A',
                        max_duration='N/A',
                        timeout_margin='N/A'
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
                    timeout=timeout,
                    avg_duration='Error',
                    max_duration='Error',
                    timeout_margin='Error'
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
        
        # 타임아웃 위험 함수 찾기
        timeout_risk_functions = [f for f in function_analysis if f.get('max_duration') != 'N/A' and f.get('max_duration') != 'Error' and f.get('timeout') < f.get('max_duration') * 1.2]
        if timeout_risk_functions:
            recommendations.append(f'타임아웃 위험이 있는 {len(timeout_risk_functions)}개 함수는 타임아웃 설정을 늘리거나 성능을 개선하세요. (영향받는 함수: {", ".join([f["function_name"] for f in timeout_risk_functions])})')
            
        # 과도한 타임아웃 함수 찾기
        excessive_timeout_functions = [f for f in function_analysis if f.get('max_duration') != 'N/A' and f.get('max_duration') != 'Error' and f.get('timeout') > f.get('max_duration') * 5 and f.get('timeout') > 30]
        if excessive_timeout_functions:
            recommendations.append(f'과도한 타임아웃이 설정된 {len(excessive_timeout_functions)}개 함수는 타임아웃을 줄여 설정을 최적화하세요. (영향받는 함수: {", ".join([f["function_name"] for f in excessive_timeout_functions])})')
        
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
            message = f'{len(function_analysis)}개 함수 중 {optimization_needed_count}개가 타임아웃 설정 최적화가 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 함수({len(passed_functions)}개)가 적절한 타임아웃 설정으로 구성되어 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Lambda 타임아웃 설정 검사 중 오류가 발생했습니다: {str(e)}')