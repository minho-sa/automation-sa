import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class PublicInstanceCheck(BaseEC2Check):
    """EC2 Public 유무 확인 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_public_instance_check'
    
    def collect_data(self) -> Dict[str, Any]:
        """EC2 인스턴스 데이터 수집"""
        ec2_client = create_boto3_client('ec2')
        
        instances = ec2_client.describe_instances()
        return {'reservations': instances['Reservations']}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """EC2 인스턴스 퍼블릭 액세스 분석"""
        resources = []
        problem_count = 0
        
        for reservation in collected_data['reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                
                # 종료된 인스턴스는 제외
                if instance_state == 'terminated':
                    continue
                
                # 퍼블릭 IP 확인
                public_ip = instance.get('PublicIpAddress')
                public_dns = instance.get('PublicDnsName')
                
                # 서브넷의 퍼블릭 액세스 설정 확인
                subnet_id = instance.get('SubnetId')
                vpc_id = instance.get('VpcId')
                
                # 인스턴스 태그에서 이름 찾기
                instance_name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                # 퍼블릭 액세스 여부 판단
                is_public = bool(public_ip)
                
                if is_public:
                    status = RESOURCE_STATUS_WARNING
                    advice = f'인스턴스가 퍼블릭 IP({public_ip})를 가지고 있습니다. 필요시에만 퍼블릭 액세스를 허용하세요.'
                    status_text = '퍼블릭 액세스'
                    problem_count += 1
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = '인스턴스가 프라이빗 네트워크에 위치하고 있습니다.'
                    status_text = '프라이빗'
                
                resources.append(create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    instance_name=instance_name,
                    instance_type=instance.get('InstanceType', 'N/A'),
                    instance_state=instance_state,
                    public_ip=public_ip or 'N/A',
                    private_ip=instance.get('PrivateIpAddress', 'N/A'),
                    subnet_id=subnet_id,
                    vpc_id=vpc_id,
                    is_public=is_public
                ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        if analysis_result['problem_count'] > 0:
            recommendations.append('퍼블릭 IP가 필요하지 않은 인스턴스는 프라이빗 서브넷으로 이동하세요.')
            recommendations.append('웹 서버 등 퍼블릭 액세스가 필요한 경우 ALB/NLB를 통해 접근하도록 구성하세요.')
            recommendations.append('퍼블릭 인스턴스의 보안 그룹을 엄격하게 관리하세요.')
        
        recommendations.append('NAT Gateway나 NAT Instance를 통해 프라이빗 인스턴스의 아웃바운드 인터넷 액세스를 제공하세요.')
        recommendations.append('Systems Manager Session Manager를 사용하여 프라이빗 인스턴스에 안전하게 접근하세요.')
        recommendations.append('정기적으로 네트워크 구성을 검토하고 최소 권한 원칙을 적용하세요.')
        
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """결과 메시지 생성"""
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        
        if problems > 0:
            return f'{total}개 인스턴스 중 {problems}개가 퍼블릭 액세스를 가지고 있습니다.'
        else:
            return f'모든 인스턴스({total}개)가 프라이빗 네트워크에 위치하고 있습니다.'