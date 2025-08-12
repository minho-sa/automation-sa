import boto3
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class InstanceGenerationCheck(BaseEC2Check):
    """EC2 인스턴스 세대 및 타입 최신성 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_instance_generation_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            instances = ec2_client.describe_instances()
            
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance['Region'] = region
            
            return {'reservations': instances['Reservations']}
        except Exception as e:
            print(f"리전 {region}에서 데이터 수집 중 오류: {str(e)}")
            return {'reservations': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_reservations = []
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_reservations.extend(result['reservations'])
        
        return {'reservations': all_reservations}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        # 구세대 인스턴스 타입 정의
        old_generations = {
            't1', 't2', 'm1', 'm2', 'm3', 'c1', 'c3', 'r3', 'i2', 'd2', 'g2'
        }
        
        for reservation in collected_data['reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                
                if instance_state == 'terminated':
                    continue
                
                instance_type = instance.get('InstanceType', '')
                instance_family = instance_type.split('.')[0] if '.' in instance_type else instance_type
                
                instance_name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                if instance_family in old_generations:
                    status = RESOURCE_STATUS_WARNING
                    advice = f'구세대 인스턴스 타입({instance_type})을 사용하고 있습니다. 최신 세대로 업그레이드를 고려하세요.'
                    status_text = '구세대'
                    problem_count += 1
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = f'최신 세대 인스턴스 타입({instance_type})을 사용하고 있습니다.'
                    status_text = '최신 세대'
                
                resources.append(create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    instance_name=instance_name,
                    region=instance.get('Region', 'N/A'),
                    instance_type=instance_type,
                    instance_family=instance_family,
                    is_old_generation=instance_family in old_generations
                ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = []
        recommendations = [
            '구세대 인스턴스를 최신 세대로 업그레이드하세요.',
            '업그레이드 전 성능 테스트를 수행하세요.',
            'Compute Optimizer로 최적 타입을 확인하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 인스턴스 중 {problems}개가 구세대 인스턴스 타입을 사용하고 있습니다.'
        else:
            return f'모든 인스턴스({total}개)가 최신 세대 인스턴스 타입을 사용하고 있습니다.'