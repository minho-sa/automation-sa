"""
IAM 사용자의 MFA 설정 상태를 검사하는 모듈
"""
import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

class MFACheck:
    """IAM 사용자의 MFA 설정 상태를 검사하는 클래스"""
    
    check_id = 'iam-mfa-check'
    
    def collect_data(self) -> Dict[str, Any]:
        """
        IAM 사용자 및 MFA 설정 데이터를 수집합니다.
        
        Returns:
            Dict[str, Any]: 수집된 데이터
        """
        iam_client = create_boto3_client('iam', role_arn=role_arn)
        
        # IAM 사용자 목록 가져오기
        users = iam_client.list_users()
        
        # 사용자별 상세 정보 수집
        user_details = []
        
        for user in users.get('Users', []):
            user_name = user['UserName']
            user_info = {'user': user}
            
            try:
                # 로그인 프로필 확인 (콘솔 액세스 가능 여부)
                try:
                    login_profile = iam_client.get_login_profile(UserName=user_name)
                    user_info['has_console_access'] = True
                except iam_client.exceptions.NoSuchEntityException:
                    user_info['has_console_access'] = False
                
                # MFA 디바이스 확인
                mfa_devices = iam_client.list_mfa_devices(UserName=user_name)
                user_info['mfa_devices'] = mfa_devices.get('MFADevices', [])
                
                # 사용자 권한 확인 (관리자 권한 여부)
                attached_policies = iam_client.list_attached_user_policies(UserName=user_name)
                user_info['attached_policies'] = attached_policies.get('AttachedPolicies', [])
                
                # 그룹 멤버십 확인
                groups = iam_client.list_groups_for_user(UserName=user_name)
                user_info['groups'] = groups.get('Groups', [])
                
                # 그룹별 정책 확인
                group_policies = []
                for group in groups.get('Groups', []):
                    group_name = group['GroupName']
                    policies = iam_client.list_attached_group_policies(GroupName=group_name)
                    group_policies.append({
                        'group_name': group_name,
                        'policies': policies.get('AttachedPolicies', [])
                    })
                user_info['group_policies'] = group_policies
                
                user_details.append(user_info)
                
            except Exception as e:
                user_info['error'] = str(e)
                user_details.append(user_info)
        
        return {'users': user_details}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        수집된 데이터를 분석하여 결과를 생성합니다.
        
        Args:
            collected_data: 수집된 데이터
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        user_details = collected_data.get('users', [])
        resources = []
        
        for user_info in user_details:
            user = user_info.get('user', {})
            user_name = user.get('UserName', '')
            
            if 'error' in user_info:
                # 오류가 있는 경우
                resources.append(create_resource_result(
                    resource_id=user_name,
                    resource_name=user_name,
                    status=RESOURCE_STATUS_UNKNOWN,
                    status_text='오류',
                    advice=f'사용자 정보를 가져오는 중 오류가 발생했습니다: {user_info["error"]}',
                    user_name=user_name,
                    has_console_access='확인 불가',
                    has_mfa='확인 불가',
                    is_admin='확인 불가',
                    groups=[]
                ))
                continue
            
            # 콘솔 액세스 여부
            has_console_access = user_info.get('has_console_access', False)
            
            # MFA 설정 여부
            mfa_devices = user_info.get('mfa_devices', [])
            has_mfa = len(mfa_devices) > 0
            
            # 관리자 권한 여부 확인
            is_admin = False
            
            # 사용자에게 직접 연결된 정책 확인
            for policy in user_info.get('attached_policies', []):
                if policy.get('PolicyName') == 'AdministratorAccess':
                    is_admin = True
                    break
            
            # 그룹을 통해 연결된 정책 확인
            if not is_admin:
                for group_policy in user_info.get('group_policies', []):
                    for policy in group_policy.get('policies', []):
                        if policy.get('PolicyName') == 'AdministratorAccess':
                            is_admin = True
                            break
                    if is_admin:
                        break
            
            # 그룹 목록
            groups = [group.get('GroupName', '') for group in user_info.get('groups', [])]
            
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
            resources.append(create_resource_result(
                resource_id=user_name,
                resource_name=user_name,
                status=status,
                status_text=status_text,
                advice=advice,
                has_console_access=has_console_access,
                has_mfa=has_mfa,
                is_admin=is_admin,
                groups=groups
            ))
        
        # 결과 분류
        passed_users = [u for u in resources if u['status'] == RESOURCE_STATUS_PASS]
        warning_users = [u for u in resources if u['status'] == RESOURCE_STATUS_WARNING]
        failed_users = [u for u in resources if u['status'] == RESOURCE_STATUS_FAIL]
        error_users = [u for u in resources if u['status'] == RESOURCE_STATUS_UNKNOWN]
        
        return {
            'resources': resources,
            'passed_users': passed_users,
            'warning_users': warning_users,
            'failed_users': failed_users,
            'error_users': error_users,
            'problem_count': len(warning_users) + len(failed_users),
            'total_count': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        분석 결과를 바탕으로 권장사항을 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            List[str]: 권장사항 목록
        """
        recommendations = []
        failed_users = analysis_result.get('failed_users', [])
        warning_users = analysis_result.get('warning_users', [])
        
        # MFA 설정 필요 사용자 찾기
        if failed_users:
            recommendations.append(f'{len(failed_users)}명의 관리자 권한을 가진 사용자에게 MFA가 설정되어 있지 않습니다. 즉시 MFA를 설정하세요. (영향받는 사용자: {", ".join([u["name"] for u in failed_users])})')
        
        if warning_users:
            recommendations.append(f'{len(warning_users)}명의 콘솔 액세스 권한이 있는 사용자에게 MFA가 설정되어 있지 않습니다. MFA를 설정하는 것이 좋습니다. (영향받는 사용자: {", ".join([u["name"] for u in warning_users])})')
        
        # 일반적인 권장사항
        recommendations.append('모든 IAM 사용자, 특히 관리자 권한이 있는 사용자에게 MFA를 설정하세요.')
        recommendations.append('가상 MFA 디바이스, U2F 보안 키 또는 하드웨어 MFA 디바이스를 사용할 수 있습니다.')
        
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """
        분석 결과를 바탕으로 메시지를 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            str: 결과 메시지
        """
        total_count = analysis_result.get('total_count', 0)
        failed_users = analysis_result.get('failed_users', [])
        warning_users = analysis_result.get('warning_users', [])
        passed_users = analysis_result.get('passed_users', [])
        
        if len(failed_users) > 0:
            return f'{total_count}명의 사용자 중 {len(failed_users)}명의 관리자 권한을 가진 사용자에게 MFA가 설정되어 있지 않습니다.'
        elif len(warning_users) > 0:
            return f'{total_count}명의 사용자 중 {len(warning_users)}명의 콘솔 액세스 권한이 있는 사용자에게 MFA가 설정되어 있지 않습니다.'
        else:
            return f'모든 사용자({len(passed_users)}명)가 MFA를 적절하게 설정했거나 MFA가 필요하지 않습니다.'
    
    def run(self, role_arn=None) -> Dict[str, Any]:
        """
        검사를 실행하고 결과를 반환합니다.
        
        Returns:
            Dict[str, Any]: 검사 결과
        """
        try:
            # 데이터 수집
            collected_data = self.collect_data()
            
            # 데이터 분석
            analysis_result = self.analyze_data(collected_data)
            
            # 권장사항 생성
            recommendations = self.generate_recommendations(analysis_result)
            
            # 메시지 생성
            message = self.create_message(analysis_result)
            
            # 상태 결정
            problem_count = analysis_result.get('problem_count', 0)
            if problem_count > 0:
                status = STATUS_WARNING
            else:
                status = STATUS_OK
            
            # 리소스 목록 가져오기
            resources = analysis_result.get('resources', [])
            
            # 통일된 결과 생성
            result = create_unified_check_result(
                status=status,
                message=message,
                resources=resources,
                recommendations=recommendations,
                check_id=self.check_id
            )
            
            return result
        except Exception as e:
            return create_error_result(f'MFA 설정 검사 중 오류가 발생했습니다: {str(e)}')

def run(role_arn=None) -> Dict[str, Any]:
    """
    IAM 사용자의 MFA(다중 인증) 설정 상태를 검사하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    check = MFACheck()
    return check.run()