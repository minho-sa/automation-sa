import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client

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
                        recommendation = None
                        if avg_cpu < 10 and max_cpu < 40:
                            recommendation = '다운사이징 권장'
                        elif avg_cpu > 80 or max_cpu > 90:
                            recommendation = '업그레이드 권장'
                        else:
                            recommendation = '적절한 크기'
                        
                        instance_analysis.append({
                            'instance_id': instance_id,
                            'instance_type': instance_type,
                            'avg_cpu': round(avg_cpu, 2),
                            'max_cpu': round(max_cpu, 2),
                            'recommendation': recommendation
                        })
                    else:
                        instance_analysis.append({
                            'instance_id': instance_id,
                            'instance_type': instance_type,
                            'avg_cpu': 'N/A',
                            'max_cpu': 'N/A',
                            'recommendation': '데이터 부족'
                        })
                        
                except Exception as e:
                    instance_analysis.append({
                        'instance_id': instance_id,
                        'instance_type': instance_type,
                        'avg_cpu': 'Error',
                        'max_cpu': 'Error',
                        'recommendation': f'데이터 수집 오류: {str(e)}'
                    })
        
        # 결과 생성
        downsizing_count = sum(1 for item in instance_analysis if item['recommendation'] == '다운사이징 권장')
        upgrade_count = sum(1 for item in instance_analysis if item['recommendation'] == '업그레이드 권장')
        
        if downsizing_count > 0 or upgrade_count > 0:
            status = 'warning'
            message = f'{len(instance_analysis)}개 인스턴스 중 {downsizing_count}개는 다운사이징, {upgrade_count}개는 업그레이드가 권장됩니다.'
        else:
            status = 'ok'
            message = '모든 인스턴스가 적절한 크기로 구성되어 있습니다.'
        
        return {
            'status': status,
            'data': {
                'instances': instance_analysis,
                'downsizing_count': downsizing_count,
                'upgrade_count': upgrade_count
            },
            'recommendations': [
                '사용률이 낮은 인스턴스는 더 작은 인스턴스 타입으로 변경하여 비용을 절감하세요.',
                '사용률이 높은 인스턴스는 더 큰 인스턴스 타입으로 변경하여 성능을 개선하세요.',
                '예약 인스턴스 또는 Savings Plans를 고려하여 비용을 절감하세요.'
            ],
            'message': message
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'인스턴스 타입 검사 중 오류가 발생했습니다: {str(e)}'
        }