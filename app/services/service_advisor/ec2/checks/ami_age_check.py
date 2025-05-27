import boto3
from typing import Dict, List, Any
from datetime import datetime, timezone
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    EC2 인스턴스가 사용 중인 AMI의 생성 시간을 확인하여 오래된 AMI를 식별합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = create_boto3_client('ec2')
        
        # 실행 중인 인스턴스 정보 수집
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        # AMI ID 목록 수집
        ami_ids = set()
        instance_ami_map = {}
        
        for reservation in instances.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_id = instance['InstanceId']
                ami_id = instance['ImageId']
                ami_ids.add(ami_id)
                
                if ami_id not in instance_ami_map:
                    instance_ami_map[ami_id] = []
                instance_ami_map[ami_id].append(instance_id)
        
        # AMI 정보 수집
        ami_details = {}
        if ami_ids:
            amis = ec2.describe_images(ImageIds=list(ami_ids))
            for ami in amis.get('Images', []):
                ami_id = ami['ImageId']
                creation_date = ami.get('CreationDate')
                if creation_date:
                    ami_details[ami_id] = {
                        'creation_date': creation_date,
                        'name': ami.get('Name', 'N/A'),
                        'description': ami.get('Description', 'N/A')
                    }
        
        # 현재 시간
        now = datetime.now(timezone.utc)
        
        # AMI 분석
        ami_analysis = []
        old_ami_count = 0
        very_old_ami_count = 0
        
        for ami_id, details in ami_details.items():
            creation_date_str = details['creation_date']
            creation_date = datetime.strptime(creation_date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            
            # AMI 생성 후 경과 일수 계산
            days_old = (now - creation_date).days
            
            # AMI 사용 중인 인스턴스 목록
            instances_using_ami = instance_ami_map.get(ami_id, [])
            
            # AMI 상태 분류
            if days_old > 365:  # 1년 이상 된 AMI
                status = "매우 오래됨"
                very_old_ami_count += 1
            elif days_old > 180:  # 6개월 이상 된 AMI
                status = "오래됨"
                old_ami_count += 1
            else:
                status = "최신"
            
            ami_analysis.append({
                'ami_id': ami_id,
                'name': details['name'],
                'creation_date': creation_date_str,
                'days_old': days_old,
                'status': status,
                'instances_count': len(instances_using_ami),
                'instances': instances_using_ami
            })
        
        # 결과 생성
        if very_old_ami_count > 0:
            status = 'warning'
            message = f'{very_old_ami_count}개의 매우 오래된 AMI와 {old_ami_count}개의 오래된 AMI가 사용 중입니다.'
        elif old_ami_count > 0:
            status = 'info'
            message = f'{old_ami_count}개의 오래된 AMI가 사용 중입니다.'
        else:
            status = 'ok'
            message = '모든 인스턴스가 최신 AMI를 사용 중입니다.'
        
        return {
            'status': status,
            'data': {
                'amis': ami_analysis,
                'old_ami_count': old_ami_count,
                'very_old_ami_count': very_old_ami_count
            },
            'recommendations': [
                '1년 이상 된 AMI는 보안 패치가 누락되었을 가능성이 높으므로 최신 AMI로 교체하세요.',
                '정기적으로 인스턴스를 최신 AMI로 업데이트하는 프로세스를 구현하세요.',
                'AMI 업데이트 전에 스냅샷을 생성하여 롤백 가능성을 확보하세요.'
            ],
            'message': message
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'AMI 검사 중 오류가 발생했습니다: {str(e)}'
        }