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
                        risky_ports = {
                            22: 'SSH',
                            3389: 'RDP', 
                            3306: 'MySQL',
                            5432: 'PostgreSQL',
                            1433: 'SQL Server',
                            27017: 'MongoDB',
                            6379: 'Redis',
                            5984: 'CouchDB'
                        }
                        
                        if protocol == '-1':  # 모든 프로토콜
                            risky_rules.append({
                                'cidr': cidr,
                                'protocol': protocol,
                                'port_range': 'ALL',
                                'risk': '모든 트래픽이 인터넷에 개방됨'
                            })
                        elif from_port in risky_ports:
                            risky_rules.append({
                                'cidr': cidr,
                                'protocol': protocol,
                                'port_range': str(from_port),
                                'risk': f'{risky_ports[from_port]} 포트({from_port})가 인터넷에 개방됨'
                            })
                        elif any(from_port <= port <= to_port for port in risky_ports.keys()):
                            affected_ports = [f'{risky_ports[port]}({port})' for port in risky_ports.keys() if from_port <= port <= to_port]
                            risky_rules.append({
                                'cidr': cidr,
                                'protocol': protocol,
                                'port_range': f"{from_port}-{to_port}" if from_port != to_port else str(from_port),
                                'risk': f'위험한 포트들이 인터넷에 개방됨: {", ".join(affected_ports)}'
                            })
            
            # 보안 그룹 상태 결정
            status = RESOURCE_STATUS_PASS if not risky_rules else RESOURCE_STATUS_FAIL
            status_text = '안전' if not risky_rules else '위험'
            
            # 권장 사항 설명
            if risky_rules:
                risk_descriptions = [rule['risk'] for rule in risky_rules]
                advice = f"보안 위험 발견: {'; '.join(risk_descriptions)}"
            else:
                advice = "보안 그룹이 적절히 구성되어 있습니다."
            
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
            '0.0.0.0/0 접근을 특정 IP로 제한하세요.',
            'SSH/RDP는 관리 IP에서만 허용하세요.',
            'Session Manager로 안전하게 접근하세요.'
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