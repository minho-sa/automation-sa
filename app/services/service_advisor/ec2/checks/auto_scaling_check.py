import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    EC2 인스턴스의 Auto Scaling 구성을 검사하여 최적화 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = create_boto3_client('ec2')
        autoscaling = create_boto3_client('autoscaling')
        
        # Auto Scaling 그룹 정보 수집
        asg_response = autoscaling.describe_auto_scaling_groups()
        
        # Auto Scaling 그룹 분석
        asg_analysis = []
        single_az_count = 0
        no_scaling_policy_count = 0
        
        for asg in asg_response.get('AutoScalingGroups', []):
            asg_name = asg['AutoScalingGroupName']
            min_size = asg['MinSize']
            max_size = asg['MaxSize']
            desired_capacity = asg['DesiredCapacity']
            
            # 가용 영역 수 확인
            availability_zones = asg.get('AvailabilityZones', [])
            az_count = len(availability_zones)
            
            # 스케일링 정책 확인
            scaling_policies = autoscaling.describe_policies(
                AutoScalingGroupName=asg_name
            ).get('ScalingPolicies', [])
            
            # 문제점 식별
            issues = []
            recommendations = []
            
            if az_count < 2:
                issues.append("단일 가용 영역")
                recommendations.append("고가용성을 위해 여러 가용 영역에 배포하세요.")
                single_az_count += 1
            
            if not scaling_policies:
                issues.append("스케일링 정책 없음")
                recommendations.append("워크로드에 맞는 스케일링 정책을 구성하세요.")
                no_scaling_policy_count += 1
            
            if min_size == max_size:
                issues.append("고정 크기 그룹")
                recommendations.append("워크로드 변동에 대응할 수 있도록 최소/최대 크기를 다르게 설정하세요.")
            
            # 분석 결과 저장
            asg_analysis.append({
                'asg_name': asg_name,
                'min_size': min_size,
                'max_size': max_size,
                'desired_capacity': desired_capacity,
                'az_count': az_count,
                'scaling_policy_count': len(scaling_policies),
                'issues': issues,
                'recommendations': recommendations
            })
        
        # 결과 생성
        if single_az_count > 0 or no_scaling_policy_count > 0:
            return {
                'status': 'warning',
                'data': {
                    'auto_scaling_groups': asg_analysis,
                    'single_az_count': single_az_count,
                    'no_scaling_policy_count': no_scaling_policy_count
                },
                'recommendations': [
                    '고가용성을 위해 Auto Scaling 그룹을 여러 가용 영역에 배포하세요.',
                    'CPU 사용률, 네트워크 트래픽 등 적절한 지표에 기반한 스케일링 정책을 구성하세요.',
                    '예측 가능한 트래픽 패턴이 있는 경우 예약된 스케일링을 고려하세요.'
                ],
                'message': f'{len(asg_analysis)}개의 Auto Scaling 그룹 중 {single_az_count}개는 단일 가용 영역에 배포되어 있고, {no_scaling_policy_count}개는 스케일링 정책이 없습니다.'
            }
        elif not asg_analysis:
            return {
                'status': 'info',
                'data': {
                    'auto_scaling_groups': []
                },
                'recommendations': [
                    '워크로드 변동이 있는 애플리케이션에 Auto Scaling을 적용하여 비용을 최적화하세요.',
                    '여러 가용 영역에 걸쳐 Auto Scaling 그룹을 구성하여 고가용성을 확보하세요.'
                ],
                'message': 'Auto Scaling 그룹이 구성되어 있지 않습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {
                    'auto_scaling_groups': asg_analysis
                },
                'recommendations': [],
                'message': '모든 Auto Scaling 그룹이 적절하게 구성되어 있습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Auto Scaling 검사 중 오류가 발생했습니다: {str(e)}'
        }