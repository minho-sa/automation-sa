import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    IAM User에 대한 전반적인 확인 (User 비번, Credential, 활동기록 등 오래된 것들 정리)
    """
    try:
        iam_client = create_boto3_client('iam', role_arn=role_arn)
        
        # 자격 증명 보고서 생성 및 가져오기
        try:
            iam_client.generate_credential_report()
            import time
            time.sleep(5)  # 보고서 생성 대기
            report = iam_client.get_credential_report()
            import csv
            import io
            
            csv_content = report['Content'].decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            credential_data = list(csv_reader)
        except Exception:
            credential_data = []
        
        users = iam_client.list_users()
        user_analysis = []
        now = datetime.utcnow()
        
        for user in users.get('Users', []):
            user_name = user['UserName']
            user_issues = []
            user_status = RESOURCE_STATUS_PASS
            
            # 자격 증명 보고서에서 사용자 정보 찾기
            user_cred_data = next((u for u in credential_data if u['user'] == user_name), {})
            
            # 1. 비밀번호 관련 검사
            password_enabled = user_cred_data.get('password_enabled', 'false') == 'true'
            password_last_used = user_cred_data.get('password_last_used', 'N/A')
            password_last_changed = user_cred_data.get('password_last_changed', 'N/A')
            
            if password_enabled:
                if password_last_used != 'N/A' and password_last_used != 'no_information':
                    try:
                        last_used_date = datetime.strptime(password_last_used.split('+')[0], '%Y-%m-%dT%H:%M:%S')
                        days_since_used = (now - last_used_date).days
                        if days_since_used > 90:
                            user_issues.append(f'비밀번호를 {days_since_used}일 동안 사용하지 않음')
                            user_status = RESOURCE_STATUS_WARNING
                    except:
                        pass
                
                if password_last_changed != 'N/A':
                    try:
                        changed_date = datetime.strptime(password_last_changed.split('+')[0], '%Y-%m-%dT%H:%M:%S')
                        days_since_changed = (now - changed_date).days
                        if days_since_changed > 90:
                            user_issues.append(f'비밀번호를 {days_since_changed}일 동안 변경하지 않음')
                            user_status = RESOURCE_STATUS_WARNING
                    except:
                        pass
            
            # 2. 액세스 키 검사
            access_keys = iam_client.list_access_keys(UserName=user_name)
            old_keys = []
            
            for key in access_keys.get('AccessKeyMetadata', []):
                key_age = (now - key['CreateDate'].replace(tzinfo=None)).days
                key_last_used = user_cred_data.get(f'access_key_{key["AccessKeyId"][-4:]}_last_used_date', 'N/A')
                
                if key_age > 90:
                    old_keys.append(f'{key["AccessKeyId"]} ({key_age}일)')
                    user_status = RESOURCE_STATUS_WARNING
            
            if old_keys:
                user_issues.append(f'오래된 액세스 키: {", ".join(old_keys)}')
            
            # 3. MFA 설정 검사
            mfa_enabled = user_cred_data.get('mfa_active', 'false') == 'true'
            if not mfa_enabled and password_enabled:
                user_issues.append('MFA가 설정되지 않음')
                user_status = RESOURCE_STATUS_WARNING
            
            # 4. 사용자 생성일 검사
            user_age = (now - user['CreateDate'].replace(tzinfo=None)).days
            if user_age > 365 and not user_issues:  # 1년 이상 된 사용자인데 활동이 없는 경우
                if password_last_used == 'N/A' or password_last_used == 'no_information':
                    user_issues.append('장기간 미사용 계정')
                    user_status = RESOURCE_STATUS_WARNING
            
            # 결과 생성
            if not user_issues:
                advice = '사용자 계정이 적절히 관리되고 있습니다.'
                status_text = '정상'
            else:
                advice = f'개선 필요: {"; ".join(user_issues)}'
                status_text = '개선 필요'
                if user_status == RESOURCE_STATUS_PASS:
                    user_status = RESOURCE_STATUS_WARNING
            
            user_analysis.append(create_resource_result(
                resource_id=user_name,
                status=user_status,
                advice=advice,
                status_text=status_text,
                user_name=user_name,
                password_enabled=password_enabled,
                mfa_enabled=mfa_enabled,
                access_keys_count=len(access_keys.get('AccessKeyMetadata', [])),
                issues=user_issues,
                user_age_days=user_age
            ))
        
        # 결과 분류
        warning_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_WARNING]
        passed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_PASS]
        
        # 권장사항 생성
        recommendations = [
            '오래된 비밀번호와 액세스 키를 교체하세요.',
            '모든 사용자에게 MFA를 설정하세요.',
            '미사용 계정을 정기적으로 검토하세요.'
        ]
        
        # 전체 상태 결정
        if warning_users:
            message = f'{len(user_analysis)}명의 사용자 중 {len(warning_users)}명에게 개선이 필요합니다.'
            status = STATUS_WARNING
        else:
            message = f'모든 사용자({len(passed_users)}명)가 적절히 관리되고 있습니다.'
            status = STATUS_OK
        
        return create_unified_check_result(
            status=status,
            message=message,
            resources=user_analysis,
            recommendations=recommendations
        )
    
    except Exception as e:
        return create_error_result(f'IAM 사용자 종합 검사 중 오류가 발생했습니다: {str(e)}')