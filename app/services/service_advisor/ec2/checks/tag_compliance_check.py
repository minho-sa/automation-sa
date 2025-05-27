import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    EC2 리소스에 필수 태그가 적용되어 있는지 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = create_boto3_client('ec2')
        
        # 필수 태그 정의
        required_tags = ['Name', 'Environment', 'Owner', 'Project']
        
        # EC2 인스턴스 정보 수집
        instances = ec2.describe_instances()
        
        # 태그 분석 결과
        tag_analysis = []
        
        for reservation in instances.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                
                # 태그 정보 수집
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                
                # 누락된 태그 확인
                missing_tags = [tag for tag in required_tags if tag not in tags]
                
                # 인스턴스 정보 저장
                tag_analysis.append({
                    'instance_id': instance_id,
                    'state': instance_state,
                    'tags': tags,
                    'missing_tags': missing_tags,
                    'compliance': 'Compliant' if not missing_tags else 'Non-Compliant'
                })
        
        # EBS 볼륨 정보 수집
        volumes = ec2.describe_volumes()
        
        for volume in volumes.get('Volumes', []):
            volume_id = volume['VolumeId']
            volume_state = volume['State']
            
            # 태그 정보 수집
            tags = {tag['Key']: tag['Value'] for tag in volume.get('Tags', [])}
            
            # 누락된 태그 확인
            missing_tags = [tag for tag in required_tags if tag not in tags]
            
            # 볼륨 정보 저장
            tag_analysis.append({
                'resource_id': volume_id,
                'resource_type': 'EBS Volume',
                'state': volume_state,
                'tags': tags,
                'missing_tags': missing_tags,
                'compliance': 'Compliant' if not missing_tags else 'Non-Compliant'
            })
        
        # 결과 생성
        non_compliant = [item for item in tag_analysis if item['compliance'] == 'Non-Compliant']
        
        if non_compliant:
            return {
                'status': 'warning',
                'data': {
                    'resources': tag_analysis,
                    'non_compliant_count': len(non_compliant)
                },
                'recommendations': [
                    '모든 EC2 리소스에 필수 태그를 적용하세요.',
                    '태그 정책을 구현하여 태그 규정 준수를 자동화하세요.',
                    'AWS Config 규칙을 사용하여 태그 규정 준수를 모니터링하세요.'
                ],
                'message': f'{len(non_compliant)}개의 리소스가 태그 규정을 준수하지 않습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {
                    'resources': tag_analysis,
                    'non_compliant_count': 0
                },
                'recommendations': [],
                'message': '모든 리소스가 태그 규정을 준수합니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'태그 규정 준수 검사 중 오류가 발생했습니다: {str(e)}'
        }