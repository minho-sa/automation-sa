import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class InstanceLifecycleCheck(BaseEC2Check):
    """EC2 인스턴스 생명주기 및 오래된 인스턴스 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_instance_lifecycle_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        """특정 리전의 인스턴스 데이터를 수집합니다."""
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            instances = ec2_client.describe_instances()
            
            # 각 인스턴스에 리전 정보 추가
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance['Region'] = region
            
            return {'reservations': instances['Reservations']}
        except Exception as e:
            print(f"리전 {region}에서 데이터 수집 중 오류: {str(e)}")
            return {'reservations': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        # 모든 리전 목록 가져오기
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_reservations = []
        
        # 병렬 처리로 리전별 데이터 수집
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_reservations.extend(result['reservations'])
        
        return {'reservations': all_reservations}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        now = datetime.utcnow()
        old_threshold = now - timedelta(days=365)  # 1년
        
        for reservation in collected_data['reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                
                if instance_state == 'terminated':
                    continue
                
                launch_time = instance['LaunchTime'].replace(tzinfo=None)
                age_days = (now - launch_time).days
                
                instance_name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                if launch_time < old_threshold:
                    status = RESOURCE_STATUS_WARNING
                    advice = f'인스턴스가 {age_days}일 동안 실행되고 있습니다. 업데이트나 교체를 고려하세요.'
                    status_text = '오래된 인스턴스'
                    problem_count += 1
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = f'인스턴스가 {age_days}일 전에 시작되었습니다.'
                    status_text = '정상'
                
                resources.append(create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    instance_name=instance_name,
                    region=instance.get('Region', 'N/A'),
                    age_days=age_days,
                    launch_time=launch_time.strftime('%Y-%m-%d')
                ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = []
        recommendations = [
            '오래된 인스턴스를 최신 AMI로 교체하세요.',
            '정기적인 인스턴스 교체 계획을 수립하세요.',
            'Blue-Green 배포로 무중단 교체하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 인스턴스 중 {problems}개가 1년 이상 실행되고 있습니다.'
        else:
            return f'모든 인스턴스({total}개)가 적절한 생명주기를 유지하고 있습니다.'