import boto3
from typing import Dict, List, Any
from app.services.service_advisor.common.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_FAIL
)
from app.services.service_advisor.alb.checks.base_alb_check import BaseALBCheck

class UnusedALBCheck(BaseALBCheck):
    """미사용 ALB 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'alb_unused_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        elbv2_client = create_boto3_client('elbv2', role_arn=role_arn)
        
        try:
            # ALB 목록 조회
            load_balancers = elbv2_client.describe_load_balancers()
            
            # 리전 정보 추가
            current_region = elbv2_client.meta.region_name
            for lb in load_balancers.get('LoadBalancers', []):
                lb['Region'] = current_region
            
            # 타겟 그룹 목록 조회
            target_groups = elbv2_client.describe_target_groups()
            
            # 각 타겟 그룹의 타겟 상태 조회
            target_health = {}
            for tg in target_groups.get('TargetGroups', []):
                tg_arn = tg['TargetGroupArn']
                try:
                    health = elbv2_client.describe_target_health(TargetGroupArn=tg_arn)
                    target_health[tg_arn] = health.get('TargetHealthDescriptions', [])
                except Exception as e:
                    print(f"타겟 그룹 {tg_arn}의 상태 조회 중 오류: {str(e)}")
                    target_health[tg_arn] = []
            
            # 리스너 정보 조회
            listeners = {}
            for lb in load_balancers.get('LoadBalancers', []):
                lb_arn = lb['LoadBalancerArn']
                try:
                    listener_response = elbv2_client.describe_listeners(LoadBalancerArn=lb_arn)
                    listeners[lb_arn] = listener_response.get('Listeners', [])
                except Exception as e:
                    print(f"로드 밸런서 {lb_arn}의 리스너 조회 중 오류: {str(e)}")
                    listeners[lb_arn] = []
            
            return {
                'load_balancers': load_balancers.get('LoadBalancers', []),
                'target_groups': target_groups.get('TargetGroups', []),
                'target_health': target_health,
                'listeners': listeners
            }
        except Exception as e:
            print(f"ALB 데이터 수집 중 오류 발생: {str(e)}")
            return {
                'load_balancers': [],
                'target_groups': [],
                'target_health': {},
                'listeners': {}
            }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        load_balancers = collected_data.get('load_balancers', [])
        target_groups = collected_data.get('target_groups', [])
        target_health = collected_data.get('target_health', {})
        listeners = collected_data.get('listeners', {})
        
        # 타겟 그룹별 ALB 매핑 생성
        tg_to_alb = {}
        for tg in target_groups:
            for lb_arn in tg.get('LoadBalancerArns', []):
                if lb_arn not in tg_to_alb:
                    tg_to_alb[lb_arn] = []
                tg_to_alb[lb_arn].append(tg)
        
        for lb in load_balancers:
            lb_arn = lb['LoadBalancerArn']
            lb_name = lb['LoadBalancerName']
            lb_state = lb.get('State', {}).get('Code', 'unknown')
            
            # ALB 상태 확인
            status = RESOURCE_STATUS_PASS
            status_text = '정상 사용 중'
            advice = 'ELB가 정상적으로 사용되고 있습니다.'
            
            # 비활성 상태 확인
            if lb_state != 'active':
                status = RESOURCE_STATUS_WARNING
                status_text = 'ELB 비활성 상태'
                advice = f'ELB가 {lb_state} 상태입니다. 상태를 확인하세요.'
                problem_count += 1
            else:
                # 리스너 확인
                lb_listeners = listeners.get(lb_arn, [])
                if not lb_listeners:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '리스너 없음'
                    advice = 'ELB에 리스너가 설정되지 않았습니다. 미사용 ELB일 가능성이 높습니다.'
                    problem_count += 1
                else:
                    # 타겟 그룹 및 타겟 확인
                    associated_tgs = tg_to_alb.get(lb_arn, [])
                    if not associated_tgs:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '타겟 그룹 없음'
                        advice = 'ELB에 연결된 타겟 그룹이 없습니다. 설정을 확인하세요.'
                        problem_count += 1
                    else:
                        # 정상 상태의 타겟이 있는지 확인
                        has_active_targets = False
                        total_targets = 0
                        active_targets = 0
                        
                        for tg in associated_tgs:
                            tg_arn = tg['TargetGroupArn']
                            targets = target_health.get(tg_arn, [])
                            total_targets += len(targets)
                            
                            for target in targets:
                                if target.get('TargetHealth', {}).get('State') == 'healthy':
                                    active_targets += 1
                                    has_active_targets = True
                        
                        if total_targets == 0:
                            status = RESOURCE_STATUS_WARNING
                            status_text = '등록된 타겟 없음'
                            advice = 'ELB의 타겟 그룹에 등록된 타겟이 없습니다. 미사용 ELB일 가능성이 있습니다.'
                            problem_count += 1
                        elif not has_active_targets:
                            status = RESOURCE_STATUS_WARNING
                            status_text = '정상 타겟 없음'
                            advice = f'ELB의 타겟 그룹에 정상 상태의 타겟이 없습니다. (총 {total_targets}개 타겟 중 정상 타겟 0개)'
                            problem_count += 1
                        else:
                            advice = f'ELB가 정상적으로 사용되고 있습니다. (총 {total_targets}개 타겟 중 정상 타겟 {active_targets}개)'
            
            resources.append(create_resource_result(
                resource_id=lb_name,
                status=status,
                advice=advice,
                status_text=status_text,
                alb_name=lb_name,
                region=lb.get('Region', 'N/A'),
                alb_arn=lb_arn,
                state=lb_state,
                listener_count=len(listeners.get(lb_arn, [])),
                target_group_count=len(tg_to_alb.get(lb_arn, []))
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '미사용 ELB는 삭제하여 비용을 절약하세요.',
            '리스너가 없는 ELB는 설정을 완료하거나 삭제하세요.',
            '타겟이 없는 타겟 그룹은 정리하세요.',
            '비정상 상태의 타겟은 상태를 점검하고 수정하세요.',
            '정기적으로 ELB 사용 현황을 모니터링하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 ELB 중 {problems}개가 미사용이거나 문제가 있습니다.'
        else:
            return f'모든 ELB({total}개)가 정상적으로 사용되고 있습니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """
    미사용 ELB 검사를 실행합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    check = UnusedALBCheck()
    return check.run(role_arn=role_arn)