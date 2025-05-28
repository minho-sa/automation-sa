import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL
)

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
                    advice_items.append("SSH 접속은 특정 IP 주소로 제한하거나 VPN/배스천 호스트를 통해 접근하도록 설정하세요")
                if has_rdp:
                    advice_items.append("RDP 접속은 특정 IP 주소로 제한하고 가능하면 VPN을 통해 접근하도록 설정하세요")
                if has_db:
                    advice_items.append("데이터베이스 포트는 인터넷에 직접 노출하지 말고 내부 네트워크에서만 접근 가능하도록 설정하세요")
                if has_all:
                    advice_items.append("모든 포트를 개방하는 규칙은 제거하고 필요한 포트만 선택적으로 개방하세요")
                
                advice = ". ".join(advice_items)
            else:
                advice = "적절하게 구성되어 있습니다"
            
            # 표준화된 리소스 결과 생성
            sg_result = create_resource_result(
                resource_id=sg_id,
                status=status,
                advice=advice,
                status_text=status_text,
                sg_name=sg_name,
                vpc_id=vpc_id,
                description=description,
                risky_rules=risky_rules,
                risky_rules_count=len(risky_rules)
            )
            
            sg_analysis.append(sg_result)
        
        # 결과 분류
        passed_groups = [sg for sg in sg_analysis if sg['status'] == RESOURCE_STATUS_PASS]
        failed_groups = [sg for sg in sg_analysis if sg['status'] == RESOURCE_STATUS_FAIL]
        
        # 위험한 보안 그룹 수 계산
        risky_groups_count = len(failed_groups)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        if risky_groups_count > 0:
            # SSH 관련 권장사항
            ssh_groups = [sg for sg in failed_groups if any(r['port_range'] == '22' or (r['port_range'].find('-') > 0 and int(r['port_range'].split('-')[0]) <= 22 and int(r['port_range'].split('-')[1]) >= 22) for r in sg['risky_rules'])]
            if ssh_groups:
                recommendations.append(f'SSH 접속은 특정 IP 주소로 제한하거나 VPN/배스천 호스트를 통해 접근하도록 설정하세요. (영향받는 보안 그룹: {", ".join([sg["sg_name"] for sg in ssh_groups])})')
            
            # RDP 관련 권장사항
            rdp_groups = [sg for sg in failed_groups if any(r['port_range'] == '3389' or (r['port_range'].find('-') > 0 and int(r['port_range'].split('-')[0]) <= 3389 and int(r['port_range'].split('-')[1]) >= 3389) for r in sg['risky_rules'])]
            if rdp_groups:
                recommendations.append(f'RDP 접속은 특정 IP 주소로 제한하고 가능하면 VPN을 통해 접근하도록 설정하세요. (영향받는 보안 그룹: {", ".join([sg["sg_name"] for sg in rdp_groups])})')
            
            # 데이터베이스 포트 관련 권장사항
            db_groups = [sg for sg in failed_groups if any(r['port_range'] in ['3306', '5432'] or (r['port_range'].find('-') > 0 and ((int(r['port_range'].split('-')[0]) <= 3306 and int(r['port_range'].split('-')[1]) >= 3306) or (int(r['port_range'].split('-')[0]) <= 5432 and int(r['port_range'].split('-')[1]) >= 5432))) for r in sg['risky_rules'])]
            if db_groups:
                recommendations.append(f'데이터베이스 포트는 인터넷에 직접 노출하지 말고 내부 네트워크에서만 접근 가능하도록 설정하세요. (영향받는 보안 그룹: {", ".join([sg["sg_name"] for sg in db_groups])})')
            
            # 모든 포트 개방 관련 권장사항
            all_port_groups = [sg for sg in failed_groups if any(r['protocol'] == '-1' for r in sg['risky_rules'])]
            if all_port_groups:
                recommendations.append(f'모든 포트를 개방하는 규칙은 제거하고 필요한 포트만 선택적으로 개방하세요. (영향받는 보안 그룹: {", ".join([sg["sg_name"] for sg in all_port_groups])})')
        
        # 결과 생성
        data = {
            'security_groups': sg_analysis,
            'passed_groups': passed_groups,
            'failed_groups': failed_groups,
            'risky_groups_count': risky_groups_count,
            'total_groups_count': len(sg_analysis)
        }
        
        if risky_groups_count > 0:
            message = f'{len(sg_analysis)}개의 보안 그룹 중 {risky_groups_count}개에서 잠재적인 보안 위험이 발견되었습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = '모든 보안 그룹이 적절하게 구성되어 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=['모든 보안 그룹이 적절하게 구성되어 있습니다.']
            )
    
    except Exception as e:
        return create_error_result(f'보안 그룹 검사 중 오류가 발생했습니다: {str(e)}')