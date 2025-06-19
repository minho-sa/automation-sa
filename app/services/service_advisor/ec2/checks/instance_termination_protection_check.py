import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class InstanceTerminationProtectionCheck(BaseEC2Check):
    """EC2 인스턴스 종료 보호 설정 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_termination_protection_check'
    
    def collect_data(self) -> Dict[str, Any]:
        ec2_client = create_boto3_client('ec2')
        instances = ec2_client.describe_instances()
        
        # 각 인스턴스의 종료 보호 설정 확인
        instance_protections = {}
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] != 'terminated':
                    try:
                        attr = ec2_client.describe_instance_attribute(
                            InstanceId=instance['InstanceId'],
                            Attribute='disableApiTermination'
                        )
                        instance_protections[instance['InstanceId']] = attr['DisableApiTermination']['Value']
                    except:
                        instance_protections[instance['InstanceId']] = False
        
        return {
            'reservations': instances['Reservations'],
            'protections': instance_protections
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        for reservation in collected_data['reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                
                if instance_state == 'terminated':
                    continue
                
                instance_name = 'N/A'
                environment = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                    elif tag['Key'] == 'Environment':
                        environment = tag['Value']
                
                protected = collected_data['protections'].get(instance_id, False)
                is_production = environment.lower() in ['prod', 'production', 'prd']
                
                if is_production and not protected:
                    status = RESOURCE_STATUS_WARNING
                    advice = '프로덕션 인스턴스에 종료 보호가 설정되지 않았습니다. 실수로 인한 종료를 방지하기 위해 활성화하세요.'
                    status_text = '보호 없음'
                    problem_count += 1
                elif protected:
                    status = RESOURCE_STATUS_PASS
                    advice = '종료 보호가 활성화되어 있습니다.'
                    status_text = '보호됨'
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = '개발/테스트 환경으로 종료 보호가 필요하지 않습니다.'
                    status_text = '보호 불필요'
                
                resources.append(create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    instance_name=instance_name,
                    environment=environment,
                    protected=protected,
                    is_production=is_production
                ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = []
        recommendations = [
            '프로덕션 인스턴스에 종료 보호를 활성화하세요.',
            'Environment 태그로 환경을 구분하세요.',
            'IAM 정책으로 종료 권한을 제한하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{problems}개의 프로덕션 인스턴스에 종료 보호가 설정되지 않았습니다.'
        else:
            return '모든 프로덕션 인스턴스에 적절한 종료 보호가 설정되어 있습니다.'