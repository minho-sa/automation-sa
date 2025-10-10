import boto3
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class StoppedInstancesCheck(BaseEC2Check):
    """중지된 EC2 인스턴스 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_stopped_instances_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        """
        특정 리전의 EC2 인스턴스 데이터를 수집합니다.
        """
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            
            # 중지된 인스턴스 조회
            instances = ec2_client.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}]
            )
            
            region_instances = []
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance['Region'] = region
                    region_instances.append(instance)
            
            return {
                'instances': region_instances
            }
        except Exception as e:
            print(f"리전 {region}에서 EC2 인스턴스 데이터 수집 중 오류: {str(e)}")
            return {'instances': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        # 모든 리전 목록 가져오기
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_instances = []
        
        # 병렬 처리로 리전별 데이터 수집 (10개 리전 동시 처리)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_instances.extend(result['instances'])
        
        return {
            'stopped_instances': all_instances
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        # 중지된 인스턴스 검사
        for instance in collected_data['stopped_instances']:
            instance_id = instance.get('InstanceId', 'N/A')
            instance_type = instance.get('InstanceType', 'N/A')
            
            # 인스턴스 이름 태그 찾기
            instance_name = '-'
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                    break
            
            # 중지된 인스턴스는 경고로 분류
            status = RESOURCE_STATUS_WARNING
            advice = f'EC2 인스턴스({instance_id})가 중지된 상태입니다. EBS 볼륨에 대한 비용이 계속 발생합니다.'
            status_text = '중지됨'
            problem_count += 1
            
            resources.append(create_resource_result(
                resource_id=instance_id,
                status=status,
                advice=advice,
                status_text=status_text,
                instance_name=instance_name,
                instance_id=instance_id,
                resource_type='EC2 Instance',
                instance_type=instance_type,
                state='stopped',
                vpc_id=instance.get('VpcId', 'N/A'),
                subnet_id=instance.get('SubnetId', 'N/A'),
                region=instance.get('Region', 'N/A')
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '장기간 사용하지 않는 중지된 인스턴스를 종료하세요.',
            'EBS 볼륨에 대한 지속적인 비용 발생을 고려하세요.',
            '필요시 AMI를 생성하고 인스턴스를 종료하세요.',
            '정기적으로 중지된 인스턴스 현황을 점검하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{problems}개의 중지된 EC2 인스턴스가 발견되어 EBS 볼륨 비용이 지속적으로 발생하고 있습니다.'
        else:
            return '중지된 EC2 인스턴스가 없습니다.'