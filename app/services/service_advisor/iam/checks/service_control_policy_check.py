import boto3
import json
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    AWS Organizations의 서비스 제어 정책(SCP)을 분석하고 보안 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # Organizations 클라이언트 생성
        org_client = create_boto3_client('organizations',role_arn=role_arn)
        
        # 조직 정보 확인
        try:
            org_info = org_client.describe_organization()
            org_id = org_info['Organization']['Id']
            
            # 기능 활성화 여부 확인
            try:
                features = org_client.list_aws_service_access_for_organization()
                service_names = [service['ServicePrincipal'] for service in features['EnabledServicePrincipals']]
                scp_enabled = 'service-control-policy.amazonaws.com' in service_names
            except org_client.exceptions.AccessDeniedException:
                # 권한이 없는 경우 SCP 활성화 여부를 확인할 수 없음
                return create_check_result(
                    status=STATUS_WARNING,
                    message='서비스 제어 정책(SCP) 확인 권한이 없습니다.',
                    data={
                        'org_id': org_id,
                        'permission_error': True
                    },
                    recommendations=[
                        'AWS Organizations API에 대한 적절한 권한을 부여하세요. (organizations:ListAWSServiceAccessForOrganization)',
                        'SCP 분석을 위해서는 Organizations 서비스에 대한 읽기 권한이 필요합니다.',
                        '권한이 있는 계정으로 다시 시도하거나, AWS Organizations 콘솔에서 직접 SCP 설정을 확인하세요.'
                    ]
                )
            
            if not scp_enabled:
                return create_check_result(
                    status=STATUS_WARNING,
                    message='서비스 제어 정책(SCP)이 활성화되어 있지 않습니다.',
                    data={
                        'org_id': org_id,
                        'scp_enabled': False
                    },
                    recommendations=[
                        'AWS Organizations에서 서비스 제어 정책(SCP)을 활성화하여 계정 전체에 대한 권한 가드레일을 설정하세요.',
                        'SCP를 사용하여 중요한 리소스 삭제, 특정 리전 사용, 특정 서비스 사용 등을 제한할 수 있습니다.',
                        'SCP는 계정 내 모든 사용자(루트 사용자 포함)에게 적용됩니다.'
                    ]
                )
            
            # 정책 목록 가져오기
            policies = []
            paginator = org_client.get_paginator('list_policies')
            for page in paginator.paginate(Filter='SERVICE_CONTROL_POLICY'):
                policies.extend(page['Policies'])
            
            # 정책 분석 결과
            policy_analysis = []
            
            # 권장 SCP 목록
            recommended_scps = {
                'deny-root-actions': '루트 사용자 제한',
                'deny-leaving-organizations': '조직 탈퇴 방지',
                'deny-regions': '특정 리전 제한',
                'require-encryption': '암호화 요구',
                'deny-public-access': '퍼블릭 액세스 제한'
            }
            
            # 권장 SCP 구현 여부 확인
            implemented_scps = {key: False for key in recommended_scps.keys()}
            
            for policy in policies:
                policy_name = policy['Name']
                policy_id = policy['Id']
                policy_arn = policy['Arn']
                
                # 정책 문서 가져오기
                policy_content = org_client.describe_policy(PolicyId=policy_id)
                policy_document = policy_content['Policy']['Content']
                policy_json = json.loads(policy_document)
                
                # 정책 분석
                statements = policy_json.get('Statement', [])
                if not isinstance(statements, list):
                    statements = [statements]
                
                # 권장 SCP 구현 여부 확인
                has_root_restriction = False
                has_leave_org_restriction = False
                has_region_restriction = False
                has_encryption_requirement = False
                has_public_access_restriction = False
                
                for statement in statements:
                    effect = statement.get('Effect')
                    action = statement.get('Action', [])
                    resource = statement.get('Resource', [])
                    condition = statement.get('Condition', {})
                    
                    # 문자열을 리스트로 변환
                    if isinstance(action, str):
                        action = [action]
                    if isinstance(resource, str):
                        resource = [resource]
                    
                    # 루트 사용자 제한 확인
                    if (effect == 'Deny' and 
                        any('*' in a for a in action) and 
                        condition and 
                        condition.get('StringLike', {}).get('aws:PrincipalArn') == 'arn:aws:iam::*:root'):
                        has_root_restriction = True
                        implemented_scps['deny-root-actions'] = True
                    
                    # 조직 탈퇴 방지 확인
                    if (effect == 'Deny' and 
                        'organizations:LeaveOrganization' in action):
                        has_leave_org_restriction = True
                        implemented_scps['deny-leaving-organizations'] = True
                    
                    # 리전 제한 확인
                    if (effect == 'Deny' and 
                        condition and 
                        condition.get('StringNotEquals', {}).get('aws:RequestedRegion')):
                        has_region_restriction = True
                        implemented_scps['deny-regions'] = True
                    
                    # 암호화 요구 확인
                    if (effect == 'Deny' and 
                        any('kms:' in a for a in action) and 
                        condition and 
                        (condition.get('Bool', {}).get('aws:SecureTransport') == 'false' or 
                         condition.get('Null', {}).get('s3:x-amz-server-side-encryption') == 'true')):
                        has_encryption_requirement = True
                        implemented_scps['require-encryption'] = True
                    
                    # 퍼블릭 액세스 제한 확인
                    if (effect == 'Deny' and 
                        any('s3:' in a for a in action) and 
                        condition and 
                        condition.get('Bool', {}).get('s3:PublicAccessBlock:IgnorePublicAcls') == 'false'):
                        has_public_access_restriction = True
                        implemented_scps['deny-public-access'] = True
                
                # 상태 및 권장 사항 결정
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                # 표준화된 리소스 결과 생성
                policy_result = create_resource_result(
                    resource_id=policy_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    policy_name=policy_name,
                    policy_id=policy_id,
                    policy_arn=policy_arn,
                    has_root_restriction=has_root_restriction,
                    has_leave_org_restriction=has_leave_org_restriction,
                    has_region_restriction=has_region_restriction,
                    has_encryption_requirement=has_encryption_requirement,
                    has_public_access_restriction=has_public_access_restriction
                )
                
                policy_analysis.append(policy_result)
            
            # 권장 SCP 구현 결과
            scp_implementation_results = []
            
            for scp_key, scp_name in recommended_scps.items():
                implemented = implemented_scps[scp_key]
                
                status = RESOURCE_STATUS_PASS if implemented else RESOURCE_STATUS_WARNING
                status_text = '구현됨' if implemented else '미구현'
                
                if implemented:
                    advice = f'{scp_name} SCP가 구현되어 있습니다.'
                else:
                    advice = f'{scp_name} SCP를 구현하여 보안을 강화하세요.'
                
                scp_result = create_resource_result(
                    resource_id=scp_key,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    scp_name=scp_name,
                    implemented=implemented
                )
                
                scp_implementation_results.append(scp_result)
            
            # 결과 분류
            passed_scps = [s for s in scp_implementation_results if s['status'] == RESOURCE_STATUS_PASS]
            warning_scps = [s for s in scp_implementation_results if s['status'] == RESOURCE_STATUS_WARNING]
            
            # 개선 필요 SCP 카운트
            improvement_needed_count = len(warning_scps)
            
            # 권장사항 생성 (문자열 배열)
            recommendations = []
            
            # 미구현 SCP 찾기
            if warning_scps:
                recommendations.append(f'{len(warning_scps)}개의 권장 SCP가 구현되어 있지 않습니다. (미구현 SCP: {", ".join([s["scp_name"] for s in warning_scps])})')
            
            # 일반적인 권장사항
            recommendations.append('루트 사용자 작업을 제한하는 SCP를 구현하세요.')
            recommendations.append('조직 탈퇴를 방지하는 SCP를 구현하세요.')
            recommendations.append('사용하지 않는 리전에 대한 액세스를 제한하는 SCP를 구현하세요.')
            recommendations.append('암호화를 요구하는 SCP를 구현하세요.')
            recommendations.append('퍼블릭 액세스를 제한하는 SCP를 구현하세요.')
            
            # 데이터 준비
            data = {
                'org_id': org_id,
                'scp_enabled': scp_enabled,
                'policies': policy_analysis,
                'scp_implementation_results': scp_implementation_results,
                'passed_scps': passed_scps,
                'warning_scps': warning_scps,
                'improvement_needed_count': improvement_needed_count,
                'total_scps_count': len(recommended_scps)
            }
            
            # 전체 상태 결정 및 결과 생성
            if improvement_needed_count > 0:
                message = f'{len(recommended_scps)}개의 권장 SCP 중 {improvement_needed_count}개가 구현되어 있지 않습니다.'
                return create_check_result(
                    status=STATUS_WARNING,
                    message=message,
                    data=data,
                    recommendations=recommendations
                )
            else:
                message = f'모든 권장 SCP({len(passed_scps)}개)가 구현되어 있습니다.'
                return create_check_result(
                    status=STATUS_OK,
                    message=message,
                    data=data,
                    recommendations=recommendations
                )
        
        except org_client.exceptions.AWSOrganizationsNotInUseException:
            # AWS Organizations를 사용하지 않는 경우
            return create_check_result(
                status=STATUS_WARNING,
                message='AWS Organizations가 활성화되어 있지 않습니다.',
                data={
                    'org_enabled': False
                },
                recommendations=[
                    'AWS Organizations를 활성화하여 여러 AWS 계정을 중앙에서 관리하세요.',
                    'AWS Organizations를 사용하면 서비스 제어 정책(SCP)을 통해 계정 전체에 대한 권한 가드레일을 설정할 수 있습니다.',
                    'AWS Organizations는 통합 결제, 계정 관리, 중앙 집중식 정책 관리 등의 기능을 제공합니다.'
                ]
            )
    
    except org_client.exceptions.AccessDeniedException:
        # 권한이 없는 경우
        return create_check_result(
            status=STATUS_WARNING,
            message='서비스 제어 정책(SCP) 확인 권한이 없습니다.',
            data={
                'permission_error': True
            },
            recommendations=[
                'AWS Organizations API에 대한 적절한 권한을 부여하세요. (organizations:ListAWSServiceAccessForOrganization)',
                'SCP 분석을 위해서는 Organizations 서비스에 대한 읽기 권한이 필요합니다.',
                '권한이 있는 계정으로 다시 시도하거나, AWS Organizations 콘솔에서 직접 SCP 설정을 확인하세요.'
            ]
        )
    except Exception as e:
        return create_error_result(f'서비스 제어 정책 분석 중 오류가 발생했습니다: {str(e)}')