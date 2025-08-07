import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    RDS 인스턴스의 크기 최적화를 검사하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # 모든 리전에서 RDS 인스턴스 수집
        ec2_client = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
        
        # 인스턴스 분석 결과
        instance_analysis = []
        
        # 현재 시간 설정
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=14)  # 2주 데이터 분석
        
        for region in regions:
            try:
                rds_client = create_boto3_client('rds', region_name=region, role_arn=role_arn)
                cloudwatch = create_boto3_client('cloudwatch', region_name=region, role_arn=role_arn)
                instances = rds_client.describe_db_instances()
            except Exception:
                continue
                
            for instance in instances.get('DBInstances', []):
                instance_id = instance['DBInstanceIdentifier']
                engine = instance['Engine']
                instance_class = instance['DBInstanceClass']
                
                # CPU 사용률 데이터 가져오기
                try:
                    cpu_response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/RDS',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1시간 간격
                        Statistics=['Average', 'Maximum']
                    )
                    
                    # 메모리 사용률 데이터 가져오기 (일부 엔진에서만 사용 가능)
                    memory_response = None
                    try:
                        memory_response = cloudwatch.get_metric_statistics(
                            Namespace='AWS/RDS',
                            MetricName='FreeableMemory',
                            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': instance_id}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=3600,  # 1시간 간격
                            Statistics=['Average', 'Minimum']
                        )
                    except Exception:
                        pass
                    
                    # 디스크 사용률 데이터 가져오기
                    disk_response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/RDS',
                        MetricName='FreeStorageSpace',
                        Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1시간 간격
                        Statistics=['Average', 'Minimum']
                        )
                    
                    # 데이터 분석
                    cpu_datapoints = cpu_response.get('Datapoints', [])
                    memory_datapoints = memory_response.get('Datapoints', []) if memory_response else []
                    disk_datapoints = disk_response.get('Datapoints', [])
                    
                    if cpu_datapoints:
                        # CPU 사용률 계산
                        avg_cpu = sum(point['Average'] for point in cpu_datapoints) / len(cpu_datapoints)
                        max_cpu = max(point['Maximum'] for point in cpu_datapoints) if cpu_datapoints else 0
                        
                        # 메모리 사용률 계산 (가능한 경우)
                        avg_memory_free = None
                        min_memory_free = None
                        if memory_datapoints:
                            avg_memory_free = sum(point['Average'] for point in memory_datapoints) / len(memory_datapoints)
                            min_memory_free = min(point['Minimum'] for point in memory_datapoints)
                        
                        # 디스크 사용률 계산
                        avg_disk_free = None
                        min_disk_free = None
                        if disk_datapoints:
                            avg_disk_free = sum(point['Average'] for point in disk_datapoints) / len(disk_datapoints)
                            min_disk_free = min(point['Minimum'] for point in disk_datapoints)
                        
                        # 인스턴스 크기 최적화 분석
                        status = RESOURCE_STATUS_PASS
                        advice = None
                        status_text = None
                        
                        # CPU 기반 분석
                        if avg_cpu < 5 and max_cpu < 20:
                            status = RESOURCE_STATUS_FAIL
                            status_text = '다운사이징 권장'
                            advice = f'CPU 사용률이 매우 낮습니다(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%). 더 작은 인스턴스 유형으로 다운사이징하여 비용을 절감하세요.'
                        elif avg_cpu > 70 or max_cpu > 90:
                            status = RESOURCE_STATUS_FAIL
                            status_text = '업그레이드 권장'
                            advice = f'CPU 사용률이 높습니다(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%). 더 큰 인스턴스 유형으로 업그레이드하여 성능을 개선하세요.'
                        else:
                            status_text = '최적화됨'
                            advice = f'현재 인스턴스 크기는 워크로드에 적합합니다. CPU 사용률(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%)이 적절한 범위 내에 있습니다.'
                        
                        # 표준화된 리소스 결과 생성
                        instance_result = create_resource_result(
                            resource_id=instance_id,
                            status=status,
                            advice=advice,
                            status_text=status_text,
                            instance_id=instance_id,
                            region=region,
                            engine=engine,
                            instance_class=instance_class,
                            avg_cpu=round(avg_cpu, 2),
                            max_cpu=round(max_cpu, 2),
                            avg_memory_free=round(avg_memory_free / (1024 * 1024 * 1024), 2) if avg_memory_free else 'N/A',  # GB로 변환
                            min_memory_free=round(min_memory_free / (1024 * 1024 * 1024), 2) if min_memory_free else 'N/A',  # GB로 변환
                            avg_disk_free=round(avg_disk_free / (1024 * 1024 * 1024), 2) if avg_disk_free else 'N/A',  # GB로 변환
                            min_disk_free=round(min_disk_free / (1024 * 1024 * 1024), 2) if min_disk_free else 'N/A'  # GB로 변환
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
                            instance_id=instance_id,
                            region=region,
                            engine=engine,
                            instance_class=instance_class,
                            avg_cpu='N/A',
                            max_cpu='N/A',
                            avg_memory_free='N/A',
                            min_memory_free='N/A',
                            avg_disk_free='N/A',
                            min_disk_free='N/A'
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
                        instance_id=instance_id,
                        region=region,
                        engine=engine,
                        instance_class=instance_class,
                        avg_cpu='Error',
                        max_cpu='Error',
                        avg_memory_free='Error',
                        min_memory_free='Error',
                        avg_disk_free='Error',
                        min_disk_free='Error'
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
        
        # 다운사이징 권장 인스턴스 찾기
        downsizing_instances = [i for i in instance_analysis if i.get('status_text') == '다운사이징 권장']
        if downsizing_instances:
            recommendations.append(f'{len(downsizing_instances)}개 인스턴스의 CPU 사용률이 매우 낮습니다. 더 작은 인스턴스 유형으로 다운사이징하여 비용을 절감하세요. (영향받는 인스턴스: {", ".join([i["instance_id"] for i in downsizing_instances])})')
            
        # 업그레이드 권장 인스턴스 찾기
        upgrade_instances = [i for i in instance_analysis if i.get('status_text') == '업그레이드 권장']
        if upgrade_instances:
            recommendations.append(f'{len(upgrade_instances)}개 인스턴스의 CPU 사용률이 높습니다. 더 큰 인스턴스 유형으로 업그레이드하여 성능을 개선하세요. (영향받는 인스턴스: {", ".join([i["instance_id"] for i in upgrade_instances])})')
        
        # 일반적인 권장사항
        recommendations.append('인스턴스 크기를 변경하기 전에 워크로드 패턴을 분석하고 성능 요구 사항을 고려하세요.')
        recommendations.append('비용 최적화를 위해 예약 인스턴스 또는 Savings Plans 사용을 고려하세요.')
        
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
            message = f'{len(instance_analysis)}개 인스턴스 중 {optimization_needed_count}개가 크기 최적화가 필요합니다.'
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
        return create_error_result(f'인스턴스 크기 최적화 검사 중 오류가 발생했습니다: {str(e)}')