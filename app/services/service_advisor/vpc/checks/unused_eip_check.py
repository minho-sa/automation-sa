import boto3
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.vpc.checks.base_vpc_check import BaseVPCCheck

class UnusedEIPCheck(BaseVPCCheck):
    """사용하지 않는 탄력적 IP 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'vpc_unused_eip_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        """
        특정 리전의 EIP 데이터를 수집합니다.
        """
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            
            # Elastic IP 조회
            eips = ec2_client.describe_addresses()
            region_eips = []
            for eip in eips['Addresses']:
                eip['Region'] = region
                region_eips.append(eip)
            
            return {
                'eips': region_eips
            }
        except Exception as e:
            print(f"리전 {region}에서 EIP 데이터 수집 중 오류: {str(e)}")
            return {'eips': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        # 모든 리전 목록 가져오기
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_eips = []
        
        # 병렬 처리로 리전별 데이터 수집 (10개 리전 동시 처리)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_eips.extend(result['eips'])
        
        return {
            'elastic_ips': all_eips
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
                instance_id=eip.get('InstanceId', 'N/A'),
                region=eip.get('Region', 'N/A')
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '미사용 Elastic IP를 해제하세요.',
            '정기적으로 Elastic IP 사용 현황을 점검하세요.',
            'NAT Gateway나 Load Balancer 등에 연결되지 않은 EIP는 즉시 해제하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{problems}개의 미사용 Elastic IP가 발견되어 불필요한 비용이 발생하고 있습니다.'
        else:
            return '모든 Elastic IP가 적절히 사용되고 있습니다.'