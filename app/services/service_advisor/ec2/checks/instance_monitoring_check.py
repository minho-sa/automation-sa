import boto3
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class InstanceMonitoringCheck(BaseEC2Check):
    """EC2 인스턴스 모니터링 설정 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_instance_monitoring_check'
    
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
        
        for reservation in collected_data['reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                
                if instance_state == 'terminated':
                    continue
                
                # 상세 모니터링 설정 확인
                monitoring = instance.get('Monitoring', {})
                detailed_monitoring = monitoring.get('State') == 'enabled'
                
                # 인스턴스 이름 찾기
                instance_name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                if not detailed_monitoring:
                    status = RESOURCE_STATUS_WARNING
                    advice = '상세 모니터링이 비활성화되어 있습니다. 성능 문제 감지를 위해 활성화를 고려하세요.'
                    status_text = '기본 모니터링'
                    problem_count += 1
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = '상세 모니터링이 활성화되어 있습니다.'
                    status_text = '상세 모니터링'
                
                resources.append(create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    instance_name=instance_name,
                    region=instance.get('Region', 'N/A'),
                    instance_type=instance.get('InstanceType', 'N/A'),
                    detailed_monitoring=detailed_monitoring
                ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = []
        recommendations = [
            '중요한 인스턴스에 상세 모니터링을 활성화하세요.',
            'CloudWatch 알람을 설정하세요.',
            'CloudWatch Logs 에이전트를 설치하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 인스턴스 중 {problems}개가 기본 모니터링만 사용하고 있습니다.'
        else:
            return f'모든 인스턴스({total}개)에 상세 모니터링이 활성화되어 있습니다.'