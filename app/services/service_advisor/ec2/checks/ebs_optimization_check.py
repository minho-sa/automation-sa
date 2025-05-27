import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    EBS 볼륨의 사용량과 성능을 분석하여 최적화 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = create_boto3_client('ec2')
        cloudwatch = create_boto3_client('cloudwatch')
        
        # EBS 볼륨 정보 수집
        volumes = ec2.describe_volumes()
        
        # 현재 시간 설정
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=14)  # 2주 데이터 분석
        
        # 볼륨 분석 결과
        volume_analysis = []
        
        for volume in volumes.get('Volumes', []):
            volume_id = volume['VolumeId']
            volume_type = volume['VolumeType']
            volume_size = volume['Size']
            volume_state = volume['State']
            
            # 볼륨이 연결된 인스턴스 확인
            attachments = volume.get('Attachments', [])
            instance_id = attachments[0].get('InstanceId') if attachments else 'Not Attached'
            
            # 볼륨 사용량 데이터 가져오기
            try:
                if volume_state == 'in-use':
                    # IOPS 사용량
                    iops_response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/EBS',
                        MetricName='VolumeReadOps',
                        Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1시간 간격
                        Statistics=['Average']
                    )
                    
                    read_ops = iops_response.get('Datapoints', [])
                    
                    iops_response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/EBS',
                        MetricName='VolumeWriteOps',
                        Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1시간 간격
                        Statistics=['Average']
                    )
                    
                    write_ops = iops_response.get('Datapoints', [])
                    
                    # 평균 IOPS 계산
                    avg_read_iops = sum(point['Average'] for point in read_ops) / len(read_ops) if read_ops else 0
                    avg_write_iops = sum(point['Average'] for point in write_ops) / len(write_ops) if write_ops else 0
                    avg_total_iops = avg_read_iops + avg_write_iops
                    
                    # 볼륨 타입별 최적화 분석
                    recommendation = None
                    if volume_type == 'gp2':
                        if avg_total_iops < 100:
                            recommendation = 'gp3로 변경 권장 (비용 절감)'
                        elif avg_total_iops > 3000:
                            recommendation = 'io1/io2로 변경 권장 (성능 향상)'
                        else:
                            recommendation = '적절한 볼륨 타입'
                    elif volume_type == 'io1' or volume_type == 'io2':
                        if avg_total_iops < 3000:
                            recommendation = 'gp3로 변경 권장 (비용 절감)'
                        else:
                            recommendation = '적절한 볼륨 타입'
                    elif volume_type == 'standard':
                        recommendation = 'gp3로 변경 권장 (성능 향상)'
                    else:
                        recommendation = '적절한 볼륨 타입'
                    
                    volume_analysis.append({
                        'volume_id': volume_id,
                        'volume_type': volume_type,
                        'volume_size': volume_size,
                        'instance_id': instance_id,
                        'avg_read_iops': round(avg_read_iops, 2),
                        'avg_write_iops': round(avg_write_iops, 2),
                        'avg_total_iops': round(avg_total_iops, 2),
                        'recommendation': recommendation
                    })
                else:
                    # 연결되지 않은 볼륨
                    volume_analysis.append({
                        'volume_id': volume_id,
                        'volume_type': volume_type,
                        'volume_size': volume_size,
                        'instance_id': instance_id,
                        'avg_read_iops': 'N/A',
                        'avg_write_iops': 'N/A',
                        'avg_total_iops': 'N/A',
                        'recommendation': '미사용 볼륨 삭제 권장'
                    })
            except Exception as e:
                volume_analysis.append({
                    'volume_id': volume_id,
                    'volume_type': volume_type,
                    'volume_size': volume_size,
                    'instance_id': instance_id,
                    'avg_read_iops': 'Error',
                    'avg_write_iops': 'Error',
                    'avg_total_iops': 'Error',
                    'recommendation': f'데이터 수집 오류: {str(e)}'
                })
        
        # 결과 생성
        unused_volumes = [v for v in volume_analysis if v['instance_id'] == 'Not Attached']
        optimize_volumes = [v for v in volume_analysis if v['recommendation'] not in ['적절한 볼륨 타입', '데이터 수집 오류']]
        
        if unused_volumes or optimize_volumes:
            return {
                'status': 'warning',
                'data': {
                    'volumes': volume_analysis,
                    'unused_count': len(unused_volumes),
                    'optimize_count': len(optimize_volumes)
                },
                'recommendations': [
                    '미사용 볼륨은 스냅샷을 생성한 후 삭제하여 비용을 절감하세요.',
                    '사용량이 낮은 gp2 볼륨은 gp3로 변경하여 비용을 절감하세요.',
                    '사용량이 높은 gp2 볼륨은 io1/io2로 변경하여 성능을 향상시키세요.',
                    'Standard 볼륨은 gp3로 변경하여 성능을 향상시키세요.'
                ],
                'message': f'{len(unused_volumes)}개의 미사용 볼륨과 {len(optimize_volumes)}개의 최적화 가능한 볼륨이 있습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {
                    'volumes': volume_analysis,
                    'unused_count': 0,
                    'optimize_count': 0
                },
                'recommendations': [],
                'message': '모든 EBS 볼륨이 적절하게 구성되어 있습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'EBS 볼륨 검사 중 오류가 발생했습니다: {str(e)}'
        }