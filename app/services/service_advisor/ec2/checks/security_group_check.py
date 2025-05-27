import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    EC2 인스턴스의 보안 그룹 설정을 검사하여 과도하게 개방된 포트가 있는지 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = create_boto3_client('ec2')
        security_groups = ec2.describe_security_groups()
        
        # 모든 보안 그룹 분석 결과
        sg_analysis = []
        
        for sg in security_groups['SecurityGroups']:
            sg_id = sg['GroupId']
            sg_name = sg['GroupName']
            vpc_id = sg.get('VpcId', 'N/A')
            description = sg.get('Description', '')
            
            # 위험한 규칙 찾기
            risky_rules = []
            
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
                            risky_rules.append({
                                'cidr': cidr,
                                'protocol': protocol,
                                'port_range': f"{from_port}-{to_port}" if from_port != to_port else str(from_port),
                                'risk': '모든 IP에 대해 위험한 포트가 개방되어 있습니다.'
                            })
                        elif any(from_port <= port <= to_port for port in risky_ports):
                            risky_rules.append({
                                'cidr': cidr,
                                'protocol': protocol,
                                'port_range': f"{from_port}-{to_port}" if from_port != to_port else str(from_port),
                                'risk': '모든 IP에 대해 위험한 포트가 개방되어 있습니다.'
                            })
            
            # 보안 그룹 상태 결정
            status = '안전' if not risky_rules else '위험'
            status_code = 'ok' if not risky_rules else 'warning'
            
            sg_analysis.append({
                'sg_id': sg_id,
                'sg_name': sg_name,
                'vpc_id': vpc_id,
                'description': description,
                'risky_rules': risky_rules,
                'risky_rules_count': len(risky_rules),
                'status': status,
                'status_code': status_code
            })
        
        # 위험한 보안 그룹 수 계산
        risky_groups_count = sum(1 for sg in sg_analysis if sg['status_code'] == 'warning')
        
        # 결과 생성
        if risky_groups_count > 0:
            return {
                'status': 'warning',
                'data': {
                    'security_groups': sg_analysis,
                    'risky_groups_count': risky_groups_count,
                    'total_groups_count': len(sg_analysis)
                },
                'recommendations': [
                    '보안 그룹 규칙을 특정 IP 주소나 CIDR 범위로 제한하세요.',
                    '필요한 경우에만 포트를 개방하고, 사용하지 않는 포트는 닫으세요.',
                    'SSH 접속은 VPN이나 배스천 호스트를 통해 접근하도록 설정하세요.'
                ],
                'message': f'{len(sg_analysis)}개의 보안 그룹 중 {risky_groups_count}개에서 잠재적인 보안 위험이 발견되었습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {
                    'security_groups': sg_analysis,
                    'risky_groups_count': 0,
                    'total_groups_count': len(sg_analysis)
                },
                'recommendations': [],
                'message': '모든 보안 그룹이 적절하게 구성되어 있습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'보안 그룹 검사 중 오류가 발생했습니다: {str(e)}'
        }