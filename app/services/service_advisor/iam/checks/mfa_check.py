import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    IAM 사용자의 MFA(다중 인증) 설정 상태를 검사하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        iam_client = create_boto3_client('iam')
        
        # IAM 사용자 목록 가져오기
        users = iam_client.list_users()
        
        # 사용자 분석 결과
        user_analysis = []
        
        for user in users.get('Users', []):
            user_name = user['UserName']
            
            try:
                # 로그인 프로필 확인 (콘솔 액세스 가능 여부)
                has_console_access = False
                try:
                    login_profile = iam_client.get_login_profile(UserName=user_name)
                    has_console_access = True
                except iam_client.exceptions.NoSuchEntityException:
                    has_console_access = False
                
                # MFA 디바이스 확인
                mfa_devices = iam_client.list_mfa_devices(UserName=user_name)
                has_mfa = len(mfa_devices.get('MFADevices', [])) > 0
                
                # 사용자 권한 확인 (관리자 권한 여부)
                attached_policies = iam_client.list_attached_user_policies(UserName=user_name)
                is_admin = False
                for policy in attached_policies.get('AttachedPolicies', []):
                    if policy['PolicyName'] == 'AdministratorAccess':
                        is_admin = True
                        break
                
                # 그룹 멤버십 확인
                groups = iam_client.list_groups_for_user(UserName=user_name)
                user_groups = [group['GroupName'] for group in groups.get('Groups', [])]
                
                # 관리자 그룹 확인
                for group_name in user_groups:
                    group_policies = iam_client.list_attached_group_policies(GroupName=group_name)
                    for policy in group_policies.get('AttachedPolicies', []):
                        if policy['PolicyName'] == 'AdministratorAccess':
                            is_admin = True
                            break
                
                # MFA 상태 분석
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if has_console_access and not has_mfa:
                    if is_admin:
                        status = RESOURCE_STATUS_FAIL
                        status_text = 'MFA 필요'
                        advice = '관리자 권한이 있는 사용자에게 MFA가 설정되어 있지 않습니다. 즉시 MFA를 설정하세요.'
                    else:
                        status = RESOURCE_STATUS_WARNING
                        status_text = 'MFA 권장'
                        advice = '콘솔 액세스가 가능한 사용자에게 MFA가 설정되어 있지 않습니다. MFA를 설정하는 것이 좋습니다.'
                else:
                    status = RESOURCE_STATUS_PASS
                    status_text = '최적화됨'
                    if not has_console_access:
                        advice = '콘솔 액세스 권한이 없어 MFA가 필요하지 않습니다.'
                    else:
                        advice = 'MFA가 적절하게 설정되어 있습니다.'
                
                # 표준화된 리소스 결과 생성
                user_result = create_resource_result(
                    resource_id=user_name,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    user_name=user_name,
                    has_console_access=has_console_access,
                    has_mfa=has_mfa,
                    is_admin=is_admin,
                    groups=user_groups
                )
                
                user_analysis.append(user_result)
                
            except Exception as e:
                # 표준화된 리소스 결과 생성 (오류)
                user_result = create_resource_result(
                    resource_id=user_name,
                    status='error',
                    advice=f'사용자 정보를 가져오는 중 오류가 발생했습니다: {str(e)}',
                    status_text='오류',
                    user_name=user_name,
                    has_console_access='확인 불가',
                    has_mfa='확인 불가',
                    is_admin='확인 불가',
                    groups=[]
                )
                
                user_analysis.append(user_result)
        
        # 결과 분류
        passed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_PASS]
        warning_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_WARNING]
        failed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_FAIL]
        error_users = [u for u in user_analysis if u['status'] == 'error']
        
        # MFA 설정 필요 사용자 카운트
        mfa_needed_count = len(warning_users) + len(failed_users)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # MFA 설정 필요 사용자 찾기
        if failed_users:
            recommendations.append(f'{len(failed_users)}명의 관리자 권한을 가진 사용자에게 MFA가 설정되어 있지 않습니다. 즉시 MFA를 설정하세요. (영향받는 사용자: {", ".join([u["user_name"] for u in failed_users])})')
        
        if warning_users:
            recommendations.append(f'{len(warning_users)}명의 콘솔 액세스 권한이 있는 사용자에게 MFA가 설정되어 있지 않습니다. MFA를 설정하는 것이 좋습니다. (영향받는 사용자: {", ".join([u["user_name"] for u in warning_users])})')
        
        # 일반적인 권장사항
        recommendations.append('모든 IAM 사용자, 특히 관리자 권한이 있는 사용자에게 MFA를 설정하세요.')
        recommendations.append('가상 MFA 디바이스, U2F 보안 키 또는 하드웨어 MFA 디바이스를 사용할 수 있습니다.')
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_users) > 0:
            message = f'{len(user_analysis)}명의 사용자 중 {len(failed_users)}명의 관리자 권한을 가진 사용자에게 MFA가 설정되어 있지 않습니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=user_analysis,
                recommendations=recommendations
            )
        elif len(warning_users) > 0:
            message = f'{len(user_analysis)}명의 사용자 중 {len(warning_users)}명의 콘솔 액세스 권한이 있는 사용자에게 MFA가 설정되어 있지 않습니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=user_analysis,
                recommendations=recommendations
            )
        else:
            message = f'모든 사용자({len(passed_users)}명)가 MFA를 적절하게 설정했거나 MFA가 필요하지 않습니다.'
            return create_unified_check_result(
                status=STATUS_OK,
                message=message,
                resources=user_analysis,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'MFA 설정 검사 중 오류가 발생했습니다: {str(e)}')