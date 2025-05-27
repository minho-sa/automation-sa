import boto3
from typing import Dict, List, Any
from datetime import datetime, timezone

def run() -> Dict[str, Any]:
    """
    장기간 중지된 EC2 인스턴스를 식별하여 불필요한 비용 발생을 방지합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = boto3.client('ec2')
        
        # 중지된 인스턴스 정보 수집
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}]
        )
        
        # 현재 시간
        now = datetime.now(timezone.utc)
        
        # 중지된 인스턴스 분석
        stopped_instances = []
        long_stopped_instances = []
        
        for reservation in instances.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                
                # 인스턴스 상태 변경 이력 확인
                status_history = ec2.describe_instance_status_history(
                    InstanceId=instance_id
                )
                
                # 마지막 상태 변경 시간 찾기
                last_state_change = None
                for status in status_history.get('InstanceStatusEvents', []):
                    if not last_state_change or status['NotBefore'] > last_state_change:
                        last_state_change = status['NotBefore']
                
                # 상태 변경 이력이 없는 경우 시작 시간 사용
                if not last_state_change and 'LaunchTime' in instance:
                    last_state_change = instance['LaunchTime']
                
                # 중지 기간 계산
                days_stopped = None
                if last_state_change:
                    days_stopped = (now - last_state_change).days
                
                # 태그 정보 수집
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                name = tags.get('Name', 'N/A')
                
                # 인스턴스 정보 저장
                instance_info = {
                    'instance_id': instance_id,
                    'name': name,
                    'instance_type': instance_type,
                    'days_stopped': days_stopped if days_stopped is not None else 'Unknown'
                }
                
                stopped_instances.append(instance_info)
                
                # 30일 이상 중지된 인스턴스 식별
                if days_stopped and days_stopped >= 30:
                    long_stopped_instances.append(instance_info)
        
        # 결과 생성
        if long_stopped_instances:
            return {
                'status': 'warning',
                'data': {
                    'stopped_instances': stopped_instances,
                    'long_stopped_instances': long_stopped_instances
                },
                'recommendations': [
                    '30일 이상 중지된 인스턴스는 AMI를 생성한 후 종료하는 것을 고려하세요.',
                    '필요한 경우 AMI에서 새 인스턴스를 시작할 수 있습니다.',
                    '정기적으로 사용하지 않는 인스턴스는 스케줄링 도구를 사용하여 자동으로 시작/중지하세요.'
                ],
                'message': f'{len(long_stopped_instances)}개의 인스턴스가 30일 이상 중지된 상태입니다.'
            }
        elif stopped_instances:
            return {
                'status': 'info',
                'data': {
                    'stopped_instances': stopped_instances,
                    'long_stopped_instances': []
                },
                'recommendations': [
                    '중지된 인스턴스의 EBS 볼륨에 대해서는 여전히 비용이 발생합니다.',
                    '필요하지 않은 인스턴스는 AMI를 생성한 후 종료하는 것을 고려하세요.'
                ],
                'message': f'{len(stopped_instances)}개의 중지된 인스턴스가 있지만, 장기간(30일 이상) 중지된 인스턴스는 없습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {
                    'stopped_instances': [],
                    'long_stopped_instances': []
                },
                'recommendations': [],
                'message': '중지된 인스턴스가 없습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'중지된 인스턴스 검사 중 오류가 발생했습니다: {str(e)}'
        }