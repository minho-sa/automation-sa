"""
EC2 보안 그룹 설정 검사
"""
import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL,
    create_resource_result
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class SecurityGroupCheck(BaseEC2Check):
    """EC2 보안 그룹 설정 검사 클래스"""
    
    def __init__(self):
        self.check_id = 'ec2-security-group'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """
        EC2 보안 그룹 데이터를 수집합니다.
        
        Args:
            role_arn: AWS 역할 ARN (선택 사항)
            
        Returns:
            Dict[str, Any]: 수집된 데이터
        """
        try:
            ec2 = create_boto3_client('ec2', role_arn=role_arn)
            security_groups = ec2.describe_security_groups()
            
            return {
                'security_groups': security_groups['SecurityGroups']
            }
        except Exception as e:
            print(f"보안 그룹 데이터 수집 중 오류: {str(e)}")
            # 오류 발생 시 빈 데이터 반환
            return {
                'security_groups': []
            }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        수집된 데이터를 분석하여 보안 그룹 검사 결과를 생성합니다.
        
        Args:
            collected_data: 수집된 데이터
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        security_groups = collected_data['security_groups']
        
        # 모든 보안 그룹 분석 결과
        sg_analysis = []
        
        for sg in security_groups:
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
            status = RESOURCE_STATUS_PASS if not risky_rules else RESOURCE_STATUS_FAIL
            status_text = '안전' if not risky_rules else '위험'
            
            # 권장 사항 설명
            advice = None
            
            if risky_rules:
                # 위험 유형 분석
                has_ssh = any(r['port_range'] == '22' or (r['port_range'].find('-') > 0 and int(r['port_range'].split('-')[0]) <= 22 and int(r['port_range'].split('-')[1]) >= 22) for r in risky_rules)
                has_rdp = any(r['port_range'] == '3389' or (r['port_range'].find('-') > 0 and int(r['port_range'].split('-')[0]) <= 3389 and int(r['port_range'].split('-')[1]) >= 3389) for r in risky_rules)
                has_db = any(r['port_range'] in ['3306', '5432'] or (r['port_range'].find('-') > 0 and ((int(r['port_range'].split('-')[0]) <= 3306 and int(r['port_range'].split('-')[1]) >= 3306) or (int(r['port_range'].split('-')[0]) <= 5432 and int(r['port_range'].split('-')[1]) >= 5432))) for r in risky_rules)
                has_all = any(r['protocol'] == '-1' for r in risky_rules)
                
                advice_items = []
                if has_ssh:
                    advice_items.append("이 보안 그룹은 SSH 포트(22)가 모든 IP에 개방되어 있어 무차별 대입 공격에 취약합니다.")
                if has_rdp:
                    advice_items.append("이 보안 그룹은 RDP 포트(3389)가 모든 IP에 개방되어 있어 보안 위험이 높습니다.")
                if has_db:
                    advice_items.append("이 보안 그룹은 데이터베이스 포트가 인터넷에 직접 노출되어 있어 데이터 유출 위험이 있습니다.")
                if has_all:
                    advice_items.append("이 보안 그룹은 모든 포트(0-65535)가 개방되어 있어 심각한 보안 위험이 있습니다.")
                
                advice = " ".join(advice_items)
            else:
                advice = "이 보안 그룹은 모든 인바운드 규칙이 적절하게 구성되어 있습니다."
            
            # 보안 그룹 결과 생성
            sg_result = create_resource_result(
                resource_id=sg_id,
                resource_name=sg_name,
                status=status,
                status_text=status_text,
                advice=advice
            )
            
            sg_analysis.append(sg_result)
        
        # 결과 분류
        passed_groups = [sg for sg in sg_analysis if sg['status'] == RESOURCE_STATUS_PASS]
        failed_groups = [sg for sg in sg_analysis if sg['status'] == RESOURCE_STATUS_FAIL]
        
        # 위험한 보안 그룹 수 계산
        risky_groups_count = len(failed_groups)
        
        return {
            'resources': sg_analysis,
            'passed_groups': passed_groups,
            'failed_groups': failed_groups,
            'problem_count': risky_groups_count,
            'total_count': len(sg_analysis)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        분석 결과를 바탕으로 권장사항을 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            List[str]: 권장사항 목록
        """
        # 리소스 검사 결과와 상관없이 일관된 권장사항 제공
        recommendations = [
            'SSH(22) 접속은 특정 IP 주소로 제한하거나 VPN/배스천 호스트를 통해 접근하도록 설정하세요.',
            'RDP(3389) 접속은 특정 IP 주소로 제한하고 가능하면 VPN을 통해 접근하도록 설정하세요.',
            '데이터베이스 포트는 인터넷에 직접 노출하지 말고 내부 네트워크에서만 접근 가능하도록 설정하세요.',
            '모든 포트를 개방하는 규칙은 제거하고 필요한 포트만 선택적으로 개방하세요.',
            '보안 그룹 규칙을 정기적으로 검토하고 불필요한 규칙은 제거하세요.'
        ]
        
        return recommendations
        
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """
        분석 결과를 바탕으로 메시지를 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            str: 결과 메시지
        """
        risky_groups_count = analysis_result['problem_count']
        total_groups_count = analysis_result['total_count']
        
        if risky_groups_count > 0:
            return f'{total_groups_count}개의 보안 그룹 중 {risky_groups_count}개에서 잠재적인 보안 위험이 발견되었습니다.'
        else:
            return f'모든 보안 그룹({total_groups_count}개)이 적절하게 구성되어 있습니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """
    보안 그룹 설정 검사를 실행합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    check = SecurityGroupCheck()
    return check.run()