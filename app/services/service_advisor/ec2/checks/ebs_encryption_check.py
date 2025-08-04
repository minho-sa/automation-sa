import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class EBSEncryptionCheck(BaseEC2Check):
    """EBS 볼륨 암호화 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_ebs_encryption_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        ec2_client = create_boto3_client('ec2', role_arn=role_arn)
        volumes = ec2_client.describe_volumes()
        return {'volumes': volumes['Volumes']}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        for volume in collected_data['volumes']:
            volume_id = volume['VolumeId']
            encrypted = volume.get('Encrypted', False)
            
            # Name 태그 추출
            volume_name = None
            for tag in volume.get('Tags', []):
                if tag['Key'] == 'Name':
                    volume_name = tag['Value']
                    break
            
            if not encrypted:
                status = RESOURCE_STATUS_FAIL
                advice = 'EBS 볼륨이 암호화되지 않았습니다. 데이터 보호를 위해 암호화를 활성화하세요.'
                status_text = '암호화 안됨'
                problem_count += 1
            else:
                status = RESOURCE_STATUS_PASS
                advice = 'EBS 볼륨이 암호화되어 있습니다.'
                status_text = '암호화됨'
            
            resources.append(create_resource_result(
                resource_id=volume_id,
                status=status,
                advice=advice,
                status_text=status_text,
                name=volume_name,
                volume_id=volume_id,
                size=volume.get('Size', 0),
                volume_type=volume.get('VolumeType', 'N/A'),
                encrypted=encrypted
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = []
        recommendations = [
            '모든 EBS 볼륨에 암호화를 활성화하세요.',
            '계정 수준에서 기본 암호화를 설정하세요.',
            'KMS로 암호화 키를 관리하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 EBS 볼륨 중 {problems}개가 암호화되지 않았습니다.'
        else:
            return f'모든 EBS 볼륨({total}개)이 암호화되어 있습니다.'