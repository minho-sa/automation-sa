import boto3
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.common.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_FAIL
)
from app.services.service_advisor.alb.checks.base_alb_check import BaseALBCheck

class SecurityGroupCheck(BaseALBCheck):
    """ALB 보안 그룹 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'alb_security_group_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        try:
            elbv2_client = create_boto3_client('elbv2', region_name=region, role_arn=role_arn)
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            
            load_balancers = elbv2_client.describe_load_balancers()
            
            security_groups = {}
            for lb in load_balancers.get('LoadBalancers', []):
                lb['Region'] = region
                for sg_id in lb.get('SecurityGroups', []):
                    if sg_id not in security_groups:
                        try:
                            sg_response = ec2_client.describe_security_groups(GroupIds=[sg_id])
                            security_groups[sg_id] = sg_response['SecurityGroups'][0]
                        except Exception as e:
                            print(f"리전 {region}에서 보안 그룹 {sg_id} 조회 중 오류: {str(e)}")
                            security_groups[sg_id] = None
            
            return {
                'load_balancers': load_balancers.get('LoadBalancers', []),
                'security_groups': security_groups
            }
        except Exception as e:
            print(f"리전 {region}에서 ALB 데이터 수집 중 오류: {str(e)}")
            return {'load_balancers': [], 'security_groups': {}}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_load_balancers = []
        all_security_groups = {}
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_load_balancers.extend(result['load_balancers'])
                all_security_groups.update(result['security_groups'])
        
        return {
            'load_balancers': all_load_balancers,
            'security_groups': all_security_groups
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        load_balancers = collected_data.get('load_balancers', [])
        security_groups = collected_data.get('security_groups', {})
        
        for lb in load_balancers:
            lb_name = lb['LoadBalancerName']
            lb_scheme = lb.get('Scheme', 'unknown')
            lb_security_groups = lb.get('SecurityGroups', [])
            
            status = RESOURCE_STATUS_PASS
            status_text = '보안 그룹 적절'
            advice = 'ALB 보안 그룹이 적절히 설정되어 있습니다.'
            issues = []
            
            if not lb_security_groups:
                status = RESOURCE_STATUS_FAIL
                status_text = '보안 그룹 없음'
                advice = 'ALB에 보안 그룹이 설정되지 않았습니다.'
                problem_count += 1
            else:
                # 각 보안 그룹 분석
                for sg_id in lb_security_groups:
                    sg = security_groups.get(sg_id)
                    if not sg:
                        issues.append(f'보안 그룹 {sg_id}를 찾을 수 없습니다.')
                        continue
                    
                    # 인바운드 규칙 검사
                    inbound_rules = sg.get('IpPermissions', [])
                    
                    # 위험한 규칙 검사
                    for rule in inbound_rules:
                        # 0.0.0.0/0에서 모든 포트 허용 검사
                        for ip_range in rule.get('IpRanges', []):
                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                from_port = rule.get('FromPort', 0)
                                to_port = rule.get('ToPort', 65535)
                                
                                # HTTP/HTTPS가 아닌 포트에 대한 전체 개방
                                if not (from_port == 80 and to_port == 80) and not (from_port == 443 and to_port == 443):
                                    if lb_scheme == 'internet-facing':
                                        # 인터넷 대면 ALB의 경우 HTTP/HTTPS 외 포트 개방은 경고
                                        if from_port not in [80, 443] or to_port not in [80, 443]:
                                            issues.append(f'인터넷에서 {from_port}-{to_port} 포트로의 접근이 허용됩니다.')
                                    else:
                                        # 내부 ALB의 경우에도 불필요한 포트 개방 확인
                                        if from_port == 0 and to_port == 65535:
                                            issues.append('모든 포트(0-65535)가 0.0.0.0/0에 개방되어 있습니다.')
                
                if issues:
                    if any('모든 포트' in issue for issue in issues):
                        status = RESOURCE_STATUS_FAIL
                        status_text = '심각한 보안 위험'
                        problem_count += 1
                    else:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '보안 개선 필요'
                        problem_count += 1
                    
                    advice = f'보안 그룹에서 다음 문제가 발견되었습니다: {"; ".join(issues)}'
            
            resources.append(create_resource_result(
                resource_id=lb_name,
                status=status,
                advice=advice,
                status_text=status_text,
                alb_name=lb_name,
                region=lb.get('Region', 'N/A'),
                scheme=lb_scheme,
                security_group_count=len(lb_security_groups),
                issues=issues
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            'ALB 보안 그룹에서 불필요한 포트 개방을 제한하세요.',
            '인터넷 대면 ALB는 HTTP(80), HTTPS(443) 포트만 개방하세요.',
            '내부 ALB는 필요한 포트만 특정 소스에서 접근하도록 설정하세요.',
            '0.0.0.0/0 대신 특정 IP 범위나 보안 그룹을 사용하세요.',
            '정기적으로 보안 그룹 규칙을 검토하고 정리하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 ALB 중 {problems}개가 보안 그룹 개선이 필요합니다.'
        else:
            return f'모든 ALB({total}개)의 보안 그룹이 적절히 설정되어 있습니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """
    ALB 보안 그룹 검사를 실행합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    check = SecurityGroupCheck()
    return check.run(role_arn=role_arn)