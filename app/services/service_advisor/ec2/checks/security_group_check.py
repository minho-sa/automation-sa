import boto3
from typing import Dict, List, Any

def run() -> Dict[str, Any]:
    """
    EC2 인스턴스의 보안 그룹 설정을 검사하여 과도하게 개방된 포트가 있는지 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = boto3.client('ec2')
        security_groups = ec2.describe_security_groups()
        
        # 위험한 보안 그룹 규칙 식별
        risky_groups = []
        for sg in security_groups['SecurityGroups']:
            sg_id = sg['GroupId']
            sg_name = sg['GroupName']
            
            # 인바운드 규칙 검사
            for rule in sg['IpPermissions']:
                for ip_range in rule.get('IpRanges', []):
                    cidr = ip_range.get('CidrIp', '')
                    
                    # 모든 IP에 대해 개방된 위험한 포트 확인
                    if cidr == '0.0.0.0/0':
                        from_port = rule.get('FromPort', 0)
                        to_port = rule.get('ToPort', 0)
                        protocol = rule.get('IpProtocol', '-1')
                        
                        # 위험한 포트 목록 (SSH, RDP, MySQL, PostgreSQL 등)
                        risky_ports = [22, 3389, 3306, 5432]
                        
                        if protocol == '-1' or (from_port <= min(risky_ports) and to_port >= max(risky_ports)):
                            risky_groups.append({
                                'sg_id': sg_id,
                                'sg_name': sg_name,
                                'cidr': cidr,
                                'protocol': protocol,
                                'port_range': f"{from_port}-{to_port}" if from_port != to_port else str(from_port),
                                'risk': '모든 IP에 대해 위험한 포트가 개방되어 있습니다.'
                            })
                        elif any(from_port <= port <= to_port for port in risky_ports):
                            risky_groups.append({
                                'sg_id': sg_id,
                                'sg_name': sg_name,
                                'cidr': cidr,
                                'protocol': protocol,
                                'port_range': f"{from_port}-{to_port}" if from_port != to_port else str(from_port),
                                'risk': '모든 IP에 대해 위험한 포트가 개방되어 있습니다.'
                            })
        
        # 결과 생성
        if risky_groups:
            return {
                'status': 'warning',
                'data': {
                    'risky_groups': risky_groups
                },
                'recommendations': [
                    '보안 그룹 규칙을 특정 IP 주소나 CIDR 범위로 제한하세요.',
                    '필요한 경우에만 포트를 개방하고, 사용하지 않는 포트는 닫으세요.',
                    'SSH 접속은 VPN이나 배스천 호스트를 통해 접근하도록 설정하세요.'
                ],
                'message': f'{len(risky_groups)}개의 보안 그룹에서 잠재적인 보안 위험이 발견되었습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {},
                'recommendations': [],
                'message': '모든 보안 그룹이 적절하게 구성되어 있습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'보안 그룹 검사 중 오류가 발생했습니다: {str(e)}'
        }