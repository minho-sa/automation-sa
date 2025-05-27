import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    Lambda 함수의 메모리 크기가 워크로드에 적합한지 검사하고 비용 최적화 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        cloudwatch = create_boto3_client('cloudwatch')
        
        # Lambda 함수 목록 가져오기
        functions = lambda_client.list_functions()
        
        # 메모리 최적화가 필요한 함수 목록
        optimization_needed = []
        
        # 날짜 설정
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=14)  # 2주 데이터 분석
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            memory_size = function['MemorySize']
            
            # CloudWatch에서 메모리 사용량 지표 가져오기
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='MemoryUtilization',
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
                    avg_memory_utilization = sum(point['Average'] for point in datapoints) / len(datapoints)
                    max_memory_utilization = max(point['Maximum'] for point in datapoints)
                    
                    recommendation = ""
                    
                    # 메모리 사용률이 낮은 경우 (40% 미만)
                    if max_memory_utilization < 40:
                        recommendation = f"메모리 크기를 {memory_size}MB에서 {max(128, int(memory_size * 0.6))}MB로 줄이는 것을 고려하세요."
                    # 메모리 사용률이 높은 경우 (90% 이상)
                    elif max_memory_utilization > 90:
                        recommendation = f"메모리 크기를 {memory_size}MB에서 {min(10240, int(memory_size * 1.5))}MB로 늘리는 것을 고려하세요."
                    else:
                        recommendation = "현재 메모리 설정이 적절합니다."
                    
                    optimization_needed.append({
                        'function_name': function_name,
                        'memory_size': memory_size,
                        'avg_memory_utilization': round(avg_memory_utilization, 2),
                        'max_memory_utilization': round(max_memory_utilization, 2),
                        'recommendation': recommendation
                    })
                else:
                    optimization_needed.append({
                        'function_name': function_name,
                        'memory_size': memory_size,
                        'avg_memory_utilization': 0,
                        'max_memory_utilization': 0,
                        'recommendation': "메모리 사용량 데이터가 없습니다. 함수 호출 후 다시 검사하세요."
                    })
            
            except Exception as e:
                optimization_needed.append({
                    'function_name': function_name,
                    'memory_size': memory_size,
                    'avg_memory_utilization': 0,
                    'max_memory_utilization': 0,
                    'recommendation': f"메모리 사용량 데이터를 가져오는 중 오류 발생: {str(e)}"
                })
        
        # 결과 생성
        if optimization_needed:
            return {
                'status': 'info',
                'data': {
                    'functions': optimization_needed
                },
                'recommendations': [
                    '메모리 사용률이 40% 미만인 함수는 메모리 크기를 줄여 비용을 절감하세요.',
                    '메모리 사용률이 90% 이상인 함수는 메모리 크기를 늘려 성능을 개선하세요.',
                    'Lambda 함수의 메모리 크기는 CPU 할당에도 영향을 미치므로 성능과 비용을 모두 고려하세요.'
                ],
                'message': f'{len(optimization_needed)}개의 Lambda 함수에 대한 메모리 최적화 분석이 완료되었습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {},
                'recommendations': [],
                'message': 'Lambda 함수가 없거나 모든 함수의 메모리 설정이 적절합니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'메모리 크기 검사 중 오류가 발생했습니다: {str(e)}'
        }