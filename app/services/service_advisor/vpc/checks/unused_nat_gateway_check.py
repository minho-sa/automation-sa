import boto3
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.vpc.checks.base_vpc_check import BaseVPCCheck

class UnusedNATGatewayCheck(BaseVPCCheck):
    """비활성 NAT Gateway 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'vpc_unused_nat_gateway_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        """
        특정 리전의 NAT Gateway 데이터를 수집합니다.
        """
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            
            # NAT Gateway 조회
            nat_gateways = ec2_client.describe_nat_gateways()
            region_nat_gateways = []
            for nat_gw in nat_gateways['NatGateways']:
                nat_gw['Region'] = region
                region_nat_gateways.append(nat_gw)
            
            return {
                'nat_gateways': region_nat_gateways
            }
        except Exception as e:
            print(f"리전 {region}에서 NAT Gateway 데이터 수집 중 오류: {str(e)}")
            return {'nat_gateways': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        # 모든 리전 목록 가져오기
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_nat_gateways = []
        
        # 병렬 처리로 리전별 데이터 수집 (10개 리전 동시 처리)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_nat_gateways.extend(result['nat_gateways'])
        
        return {
            'nat_gateways': all_nat_gateways
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        # NAT Gateway 검사
        for nat_gw in collected_data['nat_gateways']:
            nat_gw_id = nat_gw.get('NatGatewayId', 'N/A')
            state = nat_gw.get('State', 'unknown')
            
            # NAT Gateway 이름 태그 찾기
            nat_gw_name = '-'
            for tag in nat_gw.get('Tags', []):
                if tag['Key'] == 'Name':
                    nat_gw_name = tag['Value']
                    break
            
            # 상태별 분석
            if state == 'available':
                status = RESOURCE_STATUS_PASS
                advice = f'NAT Gateway({nat_gw_id})가 정상적으로 사용 가능한 상태입니다.'
                status_text = '사용 가능'
            elif state in ['failed', 'deleting', 'deleted']:
                status = RESOURCE_STATUS_WARNING
                advice = f'NAT Gateway({nat_gw_id})가 {state} 상태입니다. 불필요한 비용이 발생할 수 있습니다.'
                status_text = f'{state.title()}'
                problem_count += 1
            elif state == 'pending':
                status = RESOURCE_STATUS_PASS
                advice = f'NAT Gateway({nat_gw_id})가 생성 중입니다.'
                status_text = '생성 중'
            else:
                status = RESOURCE_STATUS_WARNING
                advice = f'NAT Gateway({nat_gw_id})의 상태를 확인해주세요.'
                status_text = state
                problem_count += 1
            
            resources.append(create_resource_result(
                resource_id=nat_gw_id,
                status=status,
                advice=advice,
                status_text=status_text,
                nat_gw_name=nat_gw_name,
                nat_gw_id=nat_gw_id,
                resource_type='NAT Gateway',
                state=state,
                vpc_id=nat_gw.get('VpcId', 'N/A'),
                subnet_id=nat_gw.get('SubnetId', 'N/A'),
                region=nat_gw.get('Region', 'N/A')
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '사용하지 않는 NAT Gateway를 삭제하세요.',
            'Failed 상태의 NAT Gateway를 정리하세요.',
            '정기적으로 NAT Gateway 사용 현황을 점검하세요.',
            'NAT Gateway 대신 NAT Instance 사용을 고려해보세요 (비용 절약).'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{problems}개의 비활성 NAT Gateway가 발견되어 불필요한 비용이 발생하고 있습니다.'
        else:
            return '모든 NAT Gateway가 적절히 관리되고 있습니다.'