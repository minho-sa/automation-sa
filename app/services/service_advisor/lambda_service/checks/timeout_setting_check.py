import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    Lambda 함수의 타임아웃 설정이 적절한지 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        cloudwatch = create_boto3_client('cloudwatch')
        
        # Lambda 함수 목록 가져오기
        functions = lambda_client.list_functions()
        
        # 타임아웃 설정 검사가 필요한 함수 목록
        timeout_issues = []
        
        # 날짜 설정
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=14)  # 2주 데이터 분석
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            timeout = function['Timeout']
            
            # CloudWatch에서 함수 실행 시간 지표 가져오기
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Duration',
                    Dimensions=[
                        {
                            'Name': 'FunctionName',
                            'Value': function_name
                        }
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,  # 1일
                    Statistics=['Average', 'Maximum']
                )
                
                datapoints = response.get('Datapoints', [])
                
                if datapoints:
                    avg_duration_ms = sum(point['Average'] for point in datapoints) / len(datapoints)
                    max_duration_ms = max(point['Maximum'] for point in datapoints)
                    
                    # 타임아웃 설정을 밀리초로 변환
                    timeout_ms = timeout * 1000
                    
                    recommendation = ""
                    status = "적절"
                    
                    # 최대 실행 시간이 타임아웃에 가까운 경우 (타임아웃의 80% 이상)
                    if max_duration_ms > timeout_ms * 0.8:
                        status = "위험"
                        recommendation = f"타임아웃을 {timeout}초에서 {min(900, int(timeout * 1.5))}초로 늘리는 것을 고려하세요."
                    # 최대 실행 시간이 타임아웃의 20% 미만인 경우
                    elif max_duration_ms < timeout_ms * 0.2 and timeout > 10:
                        status = "과도"
                        recommendation = f"타임아웃을 {timeout}초에서 {max(3, int(timeout * 0.5))}초로 줄이는 것을 고려하세요."
                    else:
                        recommendation = "현재 타임아웃 설정이 적절합니다."
                    
                    timeout_issues.append({
                        'function_name': function_name,
                        'timeout': timeout,
                        'avg_duration_ms': round(avg_duration_ms, 2),
                        'max_duration_ms': round(max_duration_ms, 2),
                        'status': status,
                        'recommendation': recommendation
                    })
                else:
                    timeout_issues.append({
                        'function_name': function_name,
                        'timeout': timeout,
                        'avg_duration_ms': 0,
                        'max_duration_ms': 0,
                        'status': "데이터 없음",
                        'recommendation': "실행 시간 데이터가 없습니다. 함수 호출 후 다시 검사하세요."
                    })
            
            except Exception as e:
                timeout_issues.append({
                    'function_name': function_name,
                    'timeout': timeout,
                    'avg_duration_ms': 0,
                    'max_duration_ms': 0,
                    'status': "오류",
                    'recommendation': f"실행 시간 데이터를 가져오는 중 오류 발생: {str(e)}"
                })
        
        # 결과 생성
        if timeout_issues:
            # 위험 상태인 함수 수 계산
            risky_count = sum(1 for func in timeout_issues if func['status'] == "위험")
            
            status = 'warning' if risky_count > 0 else 'info'
            
            return {
                'status': status,
                'data': {
                    'functions': timeout_issues
                },
                'recommendations': [
                    '실행 시간이 타임아웃에 가까운 함수는 타임아웃을 늘리거나 코드를 최적화하세요.',
                    '타임아웃이 과도하게 설정된 함수는 적절한 값으로 줄여 오류 감지 시간을 단축하세요.',
                    '장시간 실행되는 함수는 Step Functions 또는 분할 처리를 고려하세요.'
                ],
                'message': f'{len(timeout_issues)}개의 Lambda 함수 중 {risky_count}개가 타임아웃 위험이 있습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {},
                'recommendations': [],
                'message': 'Lambda 함수가 없거나 모든 함수의 타임아웃 설정이 적절합니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'타임아웃 설정 검사 중 오류가 발생했습니다: {str(e)}'
        }