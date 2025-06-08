import boto3
import csv
import io
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    IAM 사용자의 자격 증명 보고서를 분석하고 보안 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        iam_client = create_boto3_client('iam')
        
        # 자격 증명 보고서 생성
        try:
            iam_client.generate_credential_report()
        except Exception as e:
            return create_error_result(f'자격 증명 보고서 생성 중 오류가 발생했습니다: {str(e)}')
        
        # 자격 증명 보고서 가져오기
        try:
            response = iam_client.get_credential_report()
            report_content = response['Content'].decode('utf-8')
        except Exception as e:
            return create_error_result(f'자격 증명 보고서 가져오기 중 오류가 발생했습니다: {str(e)}')
        
        # CSV 파싱
        reader = csv.DictReader(io.StringIO(report_content))
        users = list(reader)
        
        # 현재 시간
        now = datetime.now(timezone.utc)
        
        # 사용자 분석 결과
        user_analysis = []
        
        for user in users:
            user_name = user['user']
            
            # 루트 계정은 별도로 처리
            if user_name == '<root_account>':
                continue
            
            # 분석 항목
            issues = []
            
            # 콘솔 액세스 확인
            has_console_access = user['password_enabled'] == 'true'
            
            # 액세스 키 확인
            has_access_key_1 = user['access_key_1_active'] == 'true'
            has_access_key_2 = user['access_key_2_active'] == 'true'
            
            # 마지막 활동 시간 확인
            last_activity = None
            activity_dates = []
            
            if user['password_last_used'] != 'N/A' and user['password_last_used'] != 'no_information':
                try:
                    password_last_used = datetime.fromisoformat(user['password_last_used'].replace('Z', '+00:00'))
                    activity_dates.append(password_last_used)
                except:
                    pass
            
            if user['access_key_1_last_used_date'] != 'N/A' and user['access_key_1_last_used_date'] != 'no_information':
                try:
                    key1_last_used = datetime.fromisoformat(user['access_key_1_last_used_date'].replace('Z', '+00:00'))
                    activity_dates.append(key1_last_used)
                except:
                    pass
            
            if user['access_key_2_last_used_date'] != 'N/A' and user['access_key_2_last_used_date'] != 'no_information':
                try:
                    key2_last_used = datetime.fromisoformat(user['access_key_2_last_used_date'].replace('Z', '+00:00'))
                    activity_dates.append(key2_last_used)
                except:
                    pass
            
            if activity_dates:
                last_activity = max(activity_dates)
            
            # 비활성 사용자 확인 (90일 이상 미사용)
            is_inactive = False
            inactive_days = None
            
            if last_activity:
                inactive_days = (now - last_activity).days
                if inactive_days > 90:
                    is_inactive = True
                    issues.append(f'사용자가 {inactive_days}일 동안 활동이 없습니다.')
            
            # MFA 확인
            has_mfa = user['mfa_active'] == 'true'
            
            if has_console_access and not has_mfa:
                issues.append('콘솔 액세스가 가능하지만 MFA가 활성화되어 있지 않습니다.')
            
            # 오래된 액세스 키 확인 (90일 이상)
            if has_access_key_1:
                try:
                    key1_created = datetime.fromisoformat(user['access_key_1_last_rotated'].replace('Z', '+00:00'))
                    key1_age = (now - key1_created).days
                    if key1_age > 90:
                        issues.append(f'액세스 키 1이 {key1_age}일 동안 교체되지 않았습니다.')
                except:
                    pass
            
            if has_access_key_2:
                try:
                    key2_created = datetime.fromisoformat(user['access_key_2_last_rotated'].replace('Z', '+00:00'))
                    key2_age = (now - key2_created).days
                    if key2_age > 90:
                        issues.append(f'액세스 키 2가 {key2_age}일 동안 교체되지 않았습니다.')
                except:
                    pass
            
            # 상태 및 권장 사항 결정
            status = RESOURCE_STATUS_PASS
            advice = None
            status_text = None
            
            if issues:
                if is_inactive or (has_console_access and not has_mfa):
                    status = RESOURCE_STATUS_FAIL
                    status_text = '보안 위험'
                    advice = '이 사용자에게 보안 위험이 있습니다: ' + ', '.join(issues)
                else:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '개선 필요'
                    advice = '이 사용자에게 개선이 필요한 항목이 있습니다: ' + ', '.join(issues)
            else:
                status_text = '최적화됨'
                advice = '이 사용자는 보안 모범 사례를 준수합니다.'
            
            # 표준화된 리소스 결과 생성
            user_result = create_resource_result(
                resource_id=user_name,
                status=status,
                advice=advice,
                status_text=status_text,
                user_name=user_name,
                has_console_access=has_console_access,
                has_mfa=has_mfa,
                has_access_key_1=has_access_key_1,
                has_access_key_2=has_access_key_2,
                last_activity=last_activity.strftime('%Y-%m-%d') if last_activity else 'N/A',
                inactive_days=inactive_days if inactive_days else 'N/A',
                issues=issues
            )
            
            user_analysis.append(user_result)
        
        # 결과 분류
        passed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_PASS]
        warning_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_WARNING]
        failed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 사용자 카운트
        improvement_needed_count = len(warning_users) + len(failed_users)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 보안 위험이 있는 사용자 찾기
        if failed_users:
            recommendations.append(f'{len(failed_users)}명의 사용자에게 중요한 보안 위험이 있습니다. (영향받는 사용자: {", ".join([u["user_name"] for u in failed_users])})')
        
        # 개선이 필요한 사용자 찾기
        if warning_users:
            recommendations.append(f'{len(warning_users)}명의 사용자에게 개선이 필요한 항목이 있습니다. (영향받는 사용자: {", ".join([u["user_name"] for u in warning_users])})')
        
        # 일반적인 권장사항
        recommendations.append('콘솔 액세스가 가능한 모든 사용자에게 MFA를 활성화하세요.')
        recommendations.append('액세스 키를 90일마다 교체하세요.')
        recommendations.append('90일 이상 활동이 없는 사용자를 비활성화하거나 삭제하세요.')
        
        # 데이터 준비
        data = {
            'users': user_analysis,
            'passed_users': passed_users,
            'warning_users': warning_users,
            'failed_users': failed_users,
            'improvement_needed_count': improvement_needed_count,
            'total_users_count': len(user_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_users) > 0:
            message = f'{len(user_analysis)}명의 사용자 중 {len(failed_users)}명에게 중요한 보안 위험이 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_users) > 0:
            message = f'{len(user_analysis)}명의 사용자 중 {len(warning_users)}명에게 개선이 필요한 항목이 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 사용자({len(passed_users)}명)가 보안 모범 사례를 준수합니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'자격 증명 보고서 분석 중 오류가 발생했습니다: {str(e)}')