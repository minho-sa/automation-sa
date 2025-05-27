import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    Lambda 함수의 VPC 구성이 적절한지 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        ec2_client = create_boto3_client('ec2')
        
        # Lambda 함수 목록 가져오기
        functions = lambda_client.list_functions()
        
        # VPC 구성 검사가 필요한 함수 목록
        vpc_issues = []
        
        # 모든 서브넷 정보 가져오기
        subnets_response = ec2_client.describe_subnets()
        subnets = {subnet['SubnetId']: subnet for subnet in subnets_response['Subnets']}
        
        # 모든 보안 그룹 정보 가져오기
        security_groups_response = ec2_client.describe_security_groups()
        security_groups = {sg['GroupId']: sg for sg in security_groups_response['SecurityGroups']}
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            vpc_config = function.get('VpcConfig', {})
            
            # VPC 구성이 없는 경우
            if not vpc_config or not vpc_config.get('SubnetIds'):
                vpc_issues.append({
                    'function_name': function_name,
                    'vpc_enabled': False,
                    'subnet_count': 0,
                    'security_group_count': 0,
                    'has_nat_gateway': False,
                    'status': "VPC 없음",
                    'recommendation': "VPC 내부 리소스에 접근하지 않는 경우 적절합니다. VPC 내부 리소스에 접근해야 한다면 VPC 구성을 추가하세요."
                })
                continue
            
            subnet_ids = vpc_config.get('SubnetIds', [])
            security_group_ids = vpc_config.get('SecurityGroupIds', [])
            
            # 서브넷 정보 분석
            subnet_azs = set()
            has_public_subnet = False
            has_nat_gateway = False  # 실제로는 NAT 게이트웨이 확인이 복잡하므로 간소화
            
            for subnet_id in subnet_ids:
                if subnet_id in subnets:
                    subnet = subnets[subnet_id]
                    subnet_azs.add(subnet['AvailabilityZone'])
                    if subnet.get('MapPublicIpOnLaunch', False):
                        has_public_subnet = True
            
            # 보안 그룹 정보 분석
            has_outbound_rule = False
            for sg_id in security_group_ids:
                if sg_id in security_groups:
                    sg = security_groups[sg_id]
                    if sg.get('IpPermissionsEgress'):
                        has_outbound_rule = True
            
            status = "적절"
            recommendation = "현재 VPC 구성이 적절합니다."
            
            # 단일 AZ에만 배포된 경우
            if len(subnet_azs) < 2:
                status = "위험"
                recommendation = "고가용성을 위해 여러 가용 영역의 서브넷을 사용하세요."
            
            # 보안 그룹이 없는 경우
            if not security_group_ids:
                status = "위험"
                recommendation = "Lambda 함수에 보안 그룹을 연결하여 네트워크 액세스를 제어하세요."
            
            # 아웃바운드 규칙이 없는 경우
            if not has_outbound_rule:
                status = "위험"
                recommendation += " 아웃바운드 트래픽을 허용하는 보안 그룹 규칙을 추가하세요."
            
            vpc_issues.append({
                'function_name': function_name,
                'vpc_enabled': True,
                'subnet_count': len(subnet_ids),
                'security_group_count': len(security_group_ids),
                'availability_zones': len(subnet_azs),
                'has_public_subnet': has_public_subnet,
                'has_outbound_rule': has_outbound_rule,
                'status': status,
                'recommendation': recommendation
            })
        
        # 결과 생성
        if vpc_issues:
            # 위험 상태인 함수 수 계산
            risky_count = sum(1 for func in vpc_issues if func['status'] == "위험")
            
            status = 'warning' if risky_count > 0 else 'info'
            
            return {
                'status': status,
                'data': {
                    'functions': vpc_issues
                },
                'recommendations': [
                    'Lambda 함수를 여러 가용 영역에 배포하여 고가용성을 확보하세요.',
                    'VPC 내부 리소스에 접근하는 Lambda 함수는 적절한 보안 그룹을 구성하세요.',
                    'VPC 내부 Lambda 함수가 외부 서비스에 접근해야 하는 경우 NAT 게이트웨이 또는 VPC 엔드포인트를 구성하세요.'
                ],
                'message': f'{len(vpc_issues)}개의 Lambda 함수 중 {risky_count}개가 VPC 구성 문제가 있습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {},
                'recommendations': [],
                'message': 'Lambda 함수가 없거나 모든 함수의 VPC 구성이 적절합니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'VPC 구성 검사 중 오류가 발생했습니다: {str(e)}'
        }