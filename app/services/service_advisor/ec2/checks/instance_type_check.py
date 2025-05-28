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
    EC2 인스턴스 타입이 워크로드에 적합한지 검사하고 비용 최적화 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = create_boto3_client('ec2')
        cloudwatch = create_boto3_client('cloudwatch')
        
        # 실행 중인 인스턴스 정보 수집
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        # 인스턴스 분석 결과
        instance_analysis = []
        
        # 현재 시간 설정
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=14)  # 2주 데이터 분석
        
        for reservation in instances.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                
                # 인스턴스 이름 태그 가져오기
                instance_name = "N/A"
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                # CPU 사용률 데이터 가져오기
                try:
                    cpu_response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1시간 간격
                        Statistics=['Average', 'Maximum']
                    )
                    
                    datapoints = cpu_response.get('Datapoints', [])
                    
                    if datapoints:
                        avg_cpu = sum(point['Average'] for point in datapoints) / len(datapoints)
                        max_cpu = max(point['Maximum'] for point in datapoints) if datapoints else 0
                        
                        # 인스턴스 타입 최적화 분석
                        status = RESOURCE_STATUS_PASS  # 기본값은 통과
                        advice = None
                        status_text = None
                        
                        if avg_cpu < 10 and max_cpu < 40:
                            status = RESOURCE_STATUS_FAIL
                            status_text = '최적화 필요'
                            advice = f'CPU 사용률이 낮습니다(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%). 더 작은 인스턴스 타입으로 변경하여 비용을 절감하세요.'
                        elif avg_cpu > 80 or max_cpu > 90:
                            status = RESOURCE_STATUS_FAIL
                            status_text = '최적화 필요'
                            advice = f'CPU 사용률이 높습니다(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%). 더 큰 인스턴스 타입으로 변경하여 성능을 개선하세요.'
                        else:
                            status_text = '최적화됨'
                            advice = f'현재 인스턴스 타입은 워크로드에 적합합니다. CPU 사용률(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%)이 적절한 범위 내에 있습니다.'
                        
                        # 표준화된 리소스 결과 생성
                        instance_result = create_resource_result(
                            resource_id=instance_id,
                            status=status,
                            advice=advice,
                            status_text=status_text,
                            instance_name=instance_name,
                            instance_type=instance_type,
                            avg_cpu=round(avg_cpu, 2),
                            max_cpu=round(max_cpu, 2)
                        )
                        
                        instance_analysis.append(instance_result)
                    else:
                        # 표준화된 리소스 결과 생성 (데이터 없음)
                        status_text = '데이터 부족'
                        advice = '충분한 CloudWatch 메트릭 데이터가 없습니다. 최소 14일 이상의 데이터가 수집된 후 다시 검사하세요.'
                        
                        instance_result = create_resource_result(
                            resource_id=instance_id,
                            status=RESOURCE_STATUS_UNKNOWN,
                            advice=advice,
                            status_text=status_text,
                            instance_name=instance_name,
                            instance_type=instance_type,
                            avg_cpu='N/A',
                            max_cpu='N/A'
                        )
                        
                        instance_analysis.append(instance_result)
                        
                except Exception as e:
                    # 표준화된 리소스 결과 생성 (오류)
                    status_text = '오류'
                    advice = f'CloudWatch 메트릭 액세스 권한을 확인하고 다시 시도하세요.'
                    
                    instance_result = create_resource_result(
                        resource_id=instance_id,
                        status='error',
                        advice=advice,
                        status_text=status_text,
                        instance_name=instance_name,
                        instance_type=instance_type,
                        avg_cpu='Error',
                        max_cpu='Error'
                    )
                    
                    instance_analysis.append(instance_result)
        
        # 결과 분류
        passed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_PASS]
        failed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_FAIL]
        unknown_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_UNKNOWN or i['status'] == 'error']
        
        # 최적화 필요 인스턴스 카운트
        optimization_needed_count = len(failed_instances)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 낮은 CPU 사용률 인스턴스 찾기
        low_cpu_instances = [i for i in instance_analysis if i.get('avg_cpu') != 'N/A' and i.get('avg_cpu') != 'Error' and i.get('avg_cpu') < 10]
        if low_cpu_instances:
            recommendations.append(f'사용률이 낮은 {len(low_cpu_instances)}개 인스턴스는 더 작은 인스턴스 타입으로 변경하여 비용을 절감하세요. (영향받는 인스턴스: {", ".join([i["instance_name"] + " (" + i["id"] + ")" for i in low_cpu_instances])})')
            
        # 높은 CPU 사용률 인스턴스 찾기
        high_cpu_instances = [i for i in instance_analysis if i.get('avg_cpu') != 'N/A' and i.get('avg_cpu') != 'Error' and i.get('avg_cpu') > 80]
        if high_cpu_instances:
            recommendations.append(f'사용률이 높은 {len(high_cpu_instances)}개 인스턴스는 더 큰 인스턴스 타입으로 변경하여 성능을 개선하세요. (영향받는 인스턴스: {", ".join([i["instance_name"] + " (" + i["id"] + ")" for i in high_cpu_instances])})')
        
        if len(instance_analysis) > 0:
            recommendations.append('예약 인스턴스 또는 Savings Plans를 고려하여 비용을 절감하세요.')
        
        # 데이터 준비
        data = {
            'instances': instance_analysis,
            'passed_instances': passed_instances,
            'failed_instances': failed_instances,
            'unknown_instances': unknown_instances,
            'optimization_needed_count': optimization_needed_count,
            'total_instances_count': len(instance_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if optimization_needed_count > 0:
            message = f'{len(instance_analysis)}개 인스턴스 중 {optimization_needed_count}개가 최적화가 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 인스턴스({len(passed_instances)}개)가 적절한 크기로 구성되어 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'인스턴스 타입 검사 중 오류가 발생했습니다: {str(e)}')