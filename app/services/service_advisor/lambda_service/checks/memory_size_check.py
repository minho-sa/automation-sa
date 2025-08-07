import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.aws_client import get_all_regions
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    Lambda 함수의 메모리 크기가 워크로드에 적합한지 검사하고 비용 최적화 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # 모든 리전에서 Lambda 함수 정보 수집
        regions = get_all_regions('lambda')
        function_analysis = []
        
        # 현재 시간 설정
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=14)  # 2주 데이터 분석
        
        for region in regions:
            try:
                lambda_client = create_boto3_client('lambda', region_name=region, role_arn=role_arn)
                cloudwatch = create_boto3_client('cloudwatch', region_name=region, role_arn=role_arn)
                
                # Lambda 함수 정보 수집
                functions = lambda_client.list_functions()
                
                if not functions.get('Functions'):
                    continue  # 해당 리전에 함수가 없으면 다음 리전으로
                
            except Exception as e:
                # 리전 접근 실패 시 다음 리전으로 계속
                continue
        
            for function in functions.get('Functions', []):
                function_name = function['FunctionName']
                memory_size = function['MemorySize']
                
                # 함수 태그 가져오기
                try:
                    tags_response = lambda_client.list_tags(Resource=function['FunctionArn'])
                    tags = tags_response.get('Tags', {})
                except Exception:
                    tags = {}
                
                # 메모리 사용률 데이터 가져오기
                try:
                    memory_response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/Lambda',
                        MetricName='MemoryUtilization',
                        Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1시간 간격
                        Statistics=['Average', 'Maximum']
                    )
                    
                    datapoints = memory_response.get('Datapoints', [])
                    
                    if datapoints:
                        avg_memory = sum(point['Average'] for point in datapoints) / len(datapoints)
                        max_memory = max(point['Maximum'] for point in datapoints) if datapoints else 0
                        
                        # 메모리 크기 최적화 분석
                        status = RESOURCE_STATUS_PASS  # 기본값은 통과
                        advice = None
                        status_text = None
                        
                        if avg_memory < 20 and max_memory < 50:
                            status = RESOURCE_STATUS_FAIL
                            status_text = '최적화 필요'
                            advice = f'메모리 사용률이 낮습니다(평균: {round(avg_memory, 2)}%, 최대: {round(max_memory, 2)}%). 메모리 크기를 줄여 비용을 절감하세요.'
                        elif max_memory > 90:
                            status = RESOURCE_STATUS_FAIL
                            status_text = '최적화 필요'
                            advice = f'메모리 사용률이 높습니다(평균: {round(avg_memory, 2)}%, 최대: {round(max_memory, 2)}%). 메모리 크기를 늘려 성능을 개선하세요.'
                        else:
                            status_text = '최적화됨'
                            advice = f'현재 메모리 크기는 워크로드에 적합합니다. 메모리 사용률(평균: {round(avg_memory, 2)}%, 최대: {round(max_memory, 2)}%)이 적절한 범위 내에 있습니다.'
                        
                        # 표준화된 리소스 결과 생성 (리전 정보 포함)
                        function_result = create_resource_result(
                            resource_id=f"{function_name} ({region})",
                            status=status,
                            advice=advice,
                            status_text=status_text,
                            function_name=function_name,
                            region=region,
                            memory_size=memory_size,
                            avg_memory=round(avg_memory, 2),
                            max_memory=round(max_memory, 2)
                        )
                        
                        function_analysis.append(function_result)
                    else:
                        # 표준화된 리소스 결과 생성 (데이터 없음)
                        status_text = '데이터 부족'
                        advice = '충분한 CloudWatch 메트릭 데이터가 없습니다. 최소 14일 이상의 데이터가 수집된 후 다시 검사하세요.'
                        
                        function_result = create_resource_result(
                            resource_id=f"{function_name} ({region})",
                            status=RESOURCE_STATUS_UNKNOWN,
                            advice=advice,
                            status_text=status_text,
                            function_name=function_name,
                            region=region,
                            memory_size=memory_size,
                            avg_memory='N/A',
                            max_memory='N/A'
                        )
                        
                        function_analysis.append(function_result)
                        
                except Exception as e:
                    # 표준화된 리소스 결과 생성 (오류)
                    status_text = '오류'
                    advice = f'CloudWatch 메트릭 액세스 권한을 확인하고 다시 시도하세요.'
                    
                    function_result = create_resource_result(
                        resource_id=f"{function_name} ({region})",
                        status='error',
                        advice=advice,
                        status_text=status_text,
                        function_name=function_name,
                        region=region,
                        memory_size=memory_size,
                        avg_memory='Error',
                        max_memory='Error'
                    )
                    
                    function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        unknown_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_UNKNOWN or f['status'] == 'error']
        
        # 최적화 필요 함수 카운트
        optimization_needed_count = len(failed_functions)
        unknown_count = len(unknown_functions)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = [
            '메모리 사용률에 맞게 함수 메모리를 조정하세요.',
            '성능 테스트를 통해 최적 메모리 크기를 찾으세요.',
            'CloudWatch 메트릭을 정기적으로 모니터링하세요.'
        ]
        
        # 전체 상태 결정 및 결과 생성
        if optimization_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {optimization_needed_count}개가 최적화가 필요합니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=function_analysis,
                recommendations=recommendations
            )
        elif unknown_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {unknown_count}개가 데이터 부족으로 검사가 불가능합니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=function_analysis,
                recommendations=recommendations
            )
        else:
            message = f'모든 함수({len(passed_functions)}개)가 적절한 메모리 크기로 구성되어 있습니다.'
            return create_unified_check_result(
                status=STATUS_OK,
                message=message,
                resources=function_analysis,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Lambda 메모리 크기 검사 중 오류가 발생했습니다: {str(e)}')