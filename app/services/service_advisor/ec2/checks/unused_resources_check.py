import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class UnusedResourcesCheck(BaseEC2Check):
    """미사용 EC2 리소스 검사 (EIP, 볼륨 등)"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_unused_resources_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        ec2_client = create_boto3_client('ec2', role_arn=role_arn)
        
        # Elastic IP 조회
        eips = ec2_client.describe_addresses()
        
        # 사용되지 않는 볼륨 조회
        volumes = ec2_client.describe_volumes(
            Filters=[{'Name': 'status', 'Values': ['available']}]
        )
        
        return {
            'elastic_ips': eips['Addresses'],
            'unused_volumes': volumes['Volumes']
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        # 미사용 Elastic IP 검사
        for eip in collected_data['elastic_ips']:
            allocation_id = eip.get('AllocationId', 'N/A')
            public_ip = eip.get('PublicIp', 'N/A')
            
            # EIP 이름 태그 찾기
            eip_name = '-'
            for tag in eip.get('Tags', []):
                if tag['Key'] == 'Name':
                    eip_name = tag['Value']
                    break
            
            # EIP 사용 상태 확인 (인스턴스, NAT Gateway, 네트워크 인터페이스 등)
            is_in_use = any([
                'InstanceId' in eip,
                'NetworkInterfaceId' in eip,
                'AssociationId' in eip
            ])
            
            if not is_in_use:
                status = RESOURCE_STATUS_WARNING
                advice = f'Elastic IP({public_ip})가 어떤 리소스에도 연결되지 않아 비용이 발생합니다.'
                status_text = '미사용'
                problem_count += 1
            else:
                status = RESOURCE_STATUS_PASS
                if 'InstanceId' in eip:
                    advice = f'Elastic IP({public_ip})가 EC2 인스턴스에 연결되어 있습니다.'
                elif 'NetworkInterfaceId' in eip:
                    advice = f'Elastic IP({public_ip})가 네트워크 인터페이스(NAT Gateway 등)에 연결되어 있습니다.'
                else:
                    advice = f'Elastic IP({public_ip})가 사용 중입니다.'
                status_text = '사용 중'
            
            resources.append(create_resource_result(
                resource_id=allocation_id,
                status=status,
                advice=advice,
                status_text=status_text,
                eip_name=eip_name,
                allocation_id=allocation_id,
                resource_type='Elastic IP',
                public_ip=public_ip,
                instance_id=eip.get('InstanceId', 'N/A')
            ))
        
        # 미사용 볼륨 검사
        for volume in collected_data['unused_volumes']:
            volume_id = volume['VolumeId']
            size = volume.get('Size', 0)
            
            # 볼륨 이름 태그 찾기
            volume_name = '-'
            for tag in volume.get('Tags', []):
                if tag['Key'] == 'Name':
                    volume_name = tag['Value']
                    break
            
            resources.append(create_resource_result(
                resource_id=volume_id,
                status=RESOURCE_STATUS_WARNING,
                advice=f'사용되지 않는 EBS 볼륨({size}GB)으로 불필요한 비용이 발생합니다.',
                status_text='미사용',
                volume_name=volume_name,
                volume_id=volume_id,
                resource_type='EBS Volume',
                size=size,
                volume_type=volume.get('VolumeType', 'N/A')
            ))
            problem_count += 1
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = []
        recommendations = [
            '미사용 Elastic IP를 해제하세요.',
            '사용되지 않는 EBS 볼륨을 정리하세요.',
            '정기적으로 미사용 리소스를 점검하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{problems}개의 미사용 리소스가 발견되어 불필요한 비용이 발생하고 있습니다.'
        else:
            return '모든 리소스가 적절히 사용되고 있습니다.'