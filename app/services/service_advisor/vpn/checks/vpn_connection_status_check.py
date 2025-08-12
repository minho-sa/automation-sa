import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta

RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_FAIL = 'fail'

from app.services.service_advisor.vpn.checks.base_vpn_check import BaseVPNCheck

class VPNConnectionStatusCheck(BaseVPNCheck):
    """VPN 연결 상태 검사"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.check_id = 'vpn_connection_status_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """VPN 연결 데이터 수집"""
        try:
            vpn_connections = []
            
            # 모든 리전에서 VPN 연결 조회
            if role_arn:
                sts_client = self.session.client('sts')
                assumed_role = sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName='VPNConnectionStatusCheck'
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
                    
                    # VPN 연결 조회
                    response = regional_ec2.describe_vpn_connections()
                    
                    for vpn in response['VpnConnections']:
                        vpn_connections.append({
                            'VpnConnectionId': vpn['VpnConnectionId'],
                            'State': vpn['State'],
                            'Type': vpn['Type'],
                            'CustomerGatewayId': vpn.get('CustomerGatewayId', 'N/A'),
                            'VpnGatewayId': vpn.get('VpnGatewayId', 'N/A'),
                            'TransitGatewayId': vpn.get('TransitGatewayId', 'N/A'),
                            'Region': region,
                            'VgwTelemetry': vpn.get('VgwTelemetry', []),
                            'Tags': vpn.get('Tags', [])
                        })
                        
                except Exception as e:
                    print(f"리전 {region} VPN 조회 실패: {str(e)}")
                    continue
            
            return {'vpn_connections': vpn_connections}
            
        except Exception as e:
            print(f"VPN 데이터 수집 중 오류 발생: {str(e)}")
            return {'vpn_connections': []}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        vpn_connections = collected_data.get('vpn_connections', [])
        
        if not vpn_connections:
            return {
                'resources': [],
                'problem_count': 0,
                'total_resources': 0
            }
        
        for vpn in vpn_connections:
            vpn_id = vpn.get('VpnConnectionId', '')
            state = vpn.get('State', 'unknown')
            vpn_type = vpn.get('Type', 'N/A')
            region = vpn.get('Region', 'N/A')
            
            resource_status = RESOURCE_STATUS_PASS
            status_text = '정상'
            advice = 'VPN 연결이 정상 상태입니다.'
            issues = []
            
            # 상태 검사
            if state == 'pending':
                resource_status = RESOURCE_STATUS_WARNING
                status_text = '연결 중'
                issues.append('VPN 연결이 아직 설정 중입니다.')
            elif state == 'deleting':
                resource_status = RESOURCE_STATUS_WARNING
                status_text = '삭제 중'
                issues.append('VPN 연결이 삭제 중입니다.')
            elif state == 'deleted':
                resource_status = RESOURCE_STATUS_FAIL
                status_text = '삭제됨'
                issues.append('VPN 연결이 삭제되었습니다.')
                problem_count += 1
            elif state != 'available':
                resource_status = RESOURCE_STATUS_FAIL
                status_text = '연결 실패'
                issues.append(f'VPN 연결 상태가 {state}입니다.')
                problem_count += 1
            
            # 터널 상태 검사
            tunnel_status = []
            for telemetry in vpn.get('VgwTelemetry', []):
                tunnel_state = telemetry.get('Status', 'unknown')
                tunnel_ip = telemetry.get('OutsideIpAddress', 'N/A')
                
                if tunnel_state == 'UP':
                    tunnel_status.append(f"터널 {tunnel_ip}: 정상")
                else:
                    tunnel_status.append(f"터널 {tunnel_ip}: {tunnel_state}")
                    if resource_status == RESOURCE_STATUS_PASS:
                        resource_status = RESOURCE_STATUS_WARNING
                        status_text = '터널 이상'
                    issues.append(f'터널 {tunnel_ip}이 {tunnel_state} 상태입니다.')
            
            if issues:
                advice = f'다음 문제가 발견되었습니다: {" ".join(issues)}'
            
            # 태그에서 이름 찾기
            vpn_name = vpn_id
            for tag in vpn.get('Tags', []):
                if tag.get('Key') == 'Name':
                    vpn_name = tag.get('Value', vpn_id)
                    break
            
            resources.append({
                'id': vpn_id,
                'status': resource_status,
                'advice': advice,
                'status_text': status_text,
                'vpn_connection_id': vpn_id,
                'vpn_name': vpn_name,
                'vpn_state': state,
                'vpn_type': vpn_type,
                'region': region,
                'customer_gateway_id': vpn.get('CustomerGatewayId', 'N/A'),
                'vpn_gateway_id': vpn.get('VpnGatewayId', 'N/A'),
                'transit_gateway_id': vpn.get('TransitGatewayId', 'N/A'),
                'tunnel_status': tunnel_status
            })
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        return [
            'VPN 연결 상태를 정기적으로 모니터링하세요.',
            '터널 이중화를 통해 고가용성을 확보하세요.',
            'VPN 연결 로그를 활성화하여 문제를 추적하세요.',
            '네트워크 성능을 모니터링하고 최적화하세요.'
        ]
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        
        if total == 0:
            return 'VPN 연결이 없습니다.'
        elif problems > 0:
            return f'{total}개 VPN 연결 중 {problems}개에 문제가 있습니다.'
        else:
            return f'모든 VPN 연결({total}개)이 정상 상태입니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """VPN 연결 상태 검사를 실행합니다."""
    import boto3
    session = boto3.Session()
    check = VPNConnectionStatusCheck(session=session)
    return check.run(role_arn=role_arn)