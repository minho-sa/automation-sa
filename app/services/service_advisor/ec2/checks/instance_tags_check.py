import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class InstanceTagsCheck(BaseEC2Check):
    """EC2 인스턴스 태그 관리 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_instance_tags_check'
    
    def collect_data(self) -> Dict[str, Any]:
        ec2_client = create_boto3_client('ec2')
        instances = ec2_client.describe_instances()
        return {'reservations': instances['Reservations']}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        # 필수 태그 정의
        required_tags = ['Name', 'Environment', 'Owner']
        
        for reservation in collected_data['reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                
                if instance_state == 'terminated':
                    continue
                
                # 현재 태그 확인
                current_tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                missing_tags = [tag for tag in required_tags if tag not in current_tags]
                
                if missing_tags:
                    status = RESOURCE_STATUS_WARNING
                    advice = f'필수 태그가 누락되었습니다: {", ".join(missing_tags)}'
                    status_text = '태그 부족'
                    problem_count += 1
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = '모든 필수 태그가 설정되어 있습니다.'
                    status_text = '태그 완료'
                
                resources.append(create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    instance_name=current_tags.get('Name', 'N/A'),
                    tags_count=len(current_tags),
                    missing_tags=missing_tags,
                    has_name_tag='Name' in current_tags
                ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = []
        if analysis_result['problem_count'] > 0:
            recommendations.append('모든 인스턴스에 Name, Environment, Owner 태그를 설정하세요.')
            recommendations.append('태그 정책을 수립하여 일관된 태그 관리를 하세요.')
        recommendations.append('비용 할당을 위해 Project, CostCenter 태그도 고려하세요.')
        recommendations.append('AWS Config를 사용하여 태그 규정 준수를 자동화하세요.')
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 인스턴스 중 {problems}개에 필수 태그가 누락되었습니다.'
        else:
            return f'모든 인스턴스({total}개)에 필수 태그가 설정되어 있습니다.'