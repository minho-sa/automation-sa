import boto3
from typing import Dict, List, Any

RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_FAIL = 'fail'

from app.services.service_advisor.vpn.checks.base_vpn_check import BaseVPNCheck

class VPNServiceLimitsCheck(BaseVPNCheck):
    """VPN 서비스 한도 검사"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.check_id = 'vpn_service_limits_check'
        
        # VPN 서비스 한도 (기본값)
        self.service_limits = {
            'vpn_connections_per_region': 50,
            'customer_gateways_per_region': 50,
            'vpn_gateways_per_region': 5,
            'routes_per_vpn_connection': 100
        }
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """VPN 리소스 사용량 데이터 수집"""
        try:
            usage_data = []
            
            if role_arn:
                sts_client = self.session.client('sts')
                assumed_role = sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName='VPNServiceLimitsCheck'
                )
                credentials = assumed_role['Credentials']
                ec2_client = boto3.client(
                    'ec2',
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
            else:
                ec2_client = self.session.client('ec2')
            
            # 모든 리전 목록 가져오기
            regions_response = ec2_client.describe_regions()
            regions = [region['RegionName'] for region in regions_response['Regions']]
            
            for region in regions:
                try:
                    if role_arn:
                        regional_ec2 = boto3.client(
                            'ec2',
                            region_name=region,
                            aws_access_key_id=credentials['AccessKeyId'],
                            aws_secret_access_key=credentials['SecretAccessKey'],
                            aws_session_token=credentials['SessionToken']
                        )
                    else:
                        regional_ec2 = self.session.client('ec2', region_name=region)
                    
                    # VPN 연결 수 조회
                    vpn_connections = regional_ec2.describe_vpn_connections()
                    vpn_count = len(vpn_connections['VpnConnections'])
                    
                    # Customer Gateway 수 조회
                    customer_gateways = regional_ec2.describe_customer_gateways()
                    cgw_count = len(customer_gateways['CustomerGateways'])
                    
                    # VPN Gateway 수 조회
                    vpn_gateways = regional_ec2.describe_vpn_gateways()
                    vgw_count = len(vpn_gateways['VpnGateways'])
                    
                    usage_data.append({
                        'region': region,
                        'vpn_connections_count': vpn_count,
                        'customer_gateways_count': cgw_count,
                        'vpn_gateways_count': vgw_count
                    })
                    
                except Exception as e:
                    print(f"리전 {region} VPN 사용량 조회 실패: {str(e)}")
                    continue
            
            return {'usage_data': usage_data}
            
        except Exception as e:
            print(f"VPN 사용량 데이터 수집 중 오류 발생: {str(e)}")
            return {'usage_data': []}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        usage_data = collected_data.get('usage_data', [])
        
        if not usage_data:
            return {
                'resources': [],
                'problem_count': 0,
                'total_resources': 0
            }
        
        for region_data in usage_data:
            region = region_data.get('region', 'unknown')
            vpn_count = region_data.get('vpn_connections_count', 0)
            cgw_count = region_data.get('customer_gateways_count', 0)
            vgw_count = region_data.get('vpn_gateways_count', 0)
            
            # 각 리소스 타입별로 검사
            resource_checks = [
                {
                    'name': 'VPN 연결',
                    'current': vpn_count,
                    'limit': self.service_limits['vpn_connections_per_region'],
                    'type': 'vpn_connections'
                },
                {
                    'name': 'Customer Gateway',
                    'current': cgw_count,
                    'limit': self.service_limits['customer_gateways_per_region'],
                    'type': 'customer_gateways'
                },
                {
                    'name': 'VPN Gateway',
                    'current': vgw_count,
                    'limit': self.service_limits['vpn_gateways_per_region'],
                    'type': 'vpn_gateways'
                }
            ]
            
            for check in resource_checks:
                usage_percentage = (check['current'] / check['limit']) * 100
                
                resource_status = RESOURCE_STATUS_PASS
                status_text = '정상'
                advice = f"{check['name']} 사용량이 정상 범위입니다."
                
                if usage_percentage >= 90:
                    resource_status = RESOURCE_STATUS_FAIL
                    status_text = '한도 임박'
                    advice = f"{check['name']} 사용량이 한도의 {usage_percentage:.1f}%에 도달했습니다. 즉시 조치가 필요합니다."
                    problem_count += 1
                elif usage_percentage >= 80:
                    resource_status = RESOURCE_STATUS_WARNING
                    status_text = '주의 필요'
                    advice = f"{check['name']} 사용량이 한도의 {usage_percentage:.1f}%입니다. 모니터링이 필요합니다."
                    problem_count += 1
                
                resources.append({
                    'id': f"{region}_{check['type']}",
                    'status': resource_status,
                    'advice': advice,
                    'status_text': status_text,
                    'region': region,
                    'resource_type': check['name'],
                    'current_usage': check['current'],
                    'service_limit': check['limit'],
                    'usage_percentage': round(usage_percentage, 1)
                })
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        return [
            'VPN 리소스 사용량을 정기적으로 모니터링하세요.',
            '서비스 한도 증가가 필요한 경우 AWS 지원팀에 문의하세요.',
            '불필요한 VPN 리소스를 정리하여 한도를 확보하세요.',
            'CloudWatch 알람을 설정하여 사용량을 추적하세요.'
        ]
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        
        if total == 0:
            return 'VPN 리소스 사용량 정보가 없습니다.'
        elif problems > 0:
            return f'{total}개 리소스 중 {problems}개가 서비스 한도에 근접했습니다.'
        else:
            return f'모든 VPN 리소스({total}개)가 정상 사용량 범위입니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """VPN 서비스 한도 검사를 실행합니다."""
    import boto3
    session = boto3.Session()
    check = VPNServiceLimitsCheck(session=session)
    return check.run(role_arn=role_arn)