import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
import pytz
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run() -> Dict[str, Any]:
    """
    IAM 사용자의 활동 상태를 검사하고 비활성 사용자에 대한 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        iam_client = create_boto3_client('iam')
        
        # IAM 사용자 목록 가져오기
        users = iam_client.list_users()
        
        # 사용자 분석 결과
        user_analysis = []
        
        # 현재 시간 (UTC 타임존 정보 포함)
        now = datetime.now(pytz.UTC)
        
        # 경고 및 실패 기준 (90일 이상은 경고, 180일 이상은 실패)
        warning_threshold = now - timedelta(days=90)
        fail_threshold = now - timedelta(days=180)
        
        for user in users.get('Users', []):
            user_name = user['UserName']
            create_date = user.get('CreateDate')
            password_last_used = user.get('PasswordLastUsed')
            
            try:
                # 액세스 키 목록 가져오기
                access_keys = iam_client.list_access_keys(UserName=user_name)
                
                # 액세스 키 마지막 사용 시간 확인
                access_key_last_used = None
                for key in access_keys.get('AccessKeyMetadata', []):
                    if key['Status'] == 'Active':
                        key_id = key['AccessKeyId']
                        try:
                            key_last_used = iam_client.get_access_key_last_used(AccessKeyId=key_id)
                            last_used_date = key_last_used.get('AccessKeyLastUsed', {}).get('LastUsedDate')
                            
                            if last_used_date and (access_key_last_used is None or last_used_date > access_key_last_used):
                                access_key_last_used = last_used_date
                        except Exception:
                            pass
                
                # 마지막 활동 시간 결정
                last_activity = None
                
                if password_last_used and access_key_last_used:
                    last_activity = max(password_last_used, access_key_last_used)
                elif password_last_used:
                    last_activity = password_last_used
                elif access_key_last_used:
                    last_activity = access_key_last_used
                
                # 활동 상태 분석
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                inactive_days = None
                
                if last_activity:
                    inactive_days = (now - last_activity).days
                    
                    if last_activity < fail_threshold:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '비활성 사용자'
                        advice = f'이 사용자는 {inactive_days}일 동안 활동이 없습니다. 계정을 비활성화하거나 삭제하는 것이 좋습니다.'
                    elif last_activity < warning_threshold:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '낮은 활동'
                        advice = f'이 사용자는 {inactive_days}일 동안 활동이 없습니다. 계정이 여전히 필요한지 확인하세요.'
                    else:
                        status = RESOURCE_STATUS_PASS
                        status_text = '활성 사용자'
                        advice = f'이 사용자는 최근 {inactive_days}일 이내에 활동했습니다.'
                elif create_date and create_date < warning_threshold:
                    # 활동 기록이 없고 생성된 지 오래된 경우
                    inactive_days = (now - create_date).days
                    
                    if create_date < fail_threshold:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '미사용 계정'
                        advice = f'이 사용자는 생성된 지 {inactive_days}일이 지났지만 활동 기록이 없습니다. 계정을 삭제하는 것이 좋습니다.'
                    else:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '미사용 계정'
                        advice = f'이 사용자는 생성된 지 {inactive_days}일이 지났지만 활동 기록이 없습니다. 계정이 필요한지 확인하세요.'
                else:
                    # 최근에 생성된 계정
                    status = RESOURCE_STATUS_PASS
                    status_text = '신규 계정'
                    advice = '이 사용자는 최근에 생성되었습니다.'
                    if create_date:
                        inactive_days = (now - create_date).days
                
                # 표준화된 리소스 결과 생성
                user_result = create_resource_result(
                    resource_id=user_name,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    user_name=user_name,
                    create_date=create_date.strftime('%Y-%m-%d') if create_date else 'N/A',
                    last_activity=last_activity.strftime('%Y-%m-%d') if last_activity else 'N/A',
                    inactive_days=inactive_days if inactive_days is not None else 'N/A'
                )
                
                user_analysis.append(user_result)
                
            except Exception as e:
                # 표준화된 리소스 결과 생성 (오류)
                user_result = create_resource_result(
                    resource_id=user_name,
                    status='error',
                    advice=f'사용자 활동 정보를 가져오는 중 오류가 발생했습니다: {str(e)}',
                    status_text='오류',
                    user_name=user_name,
                    create_date=create_date.strftime('%Y-%m-%d') if create_date else 'N/A',
                    last_activity='확인 불가',
                    inactive_days='확인 불가'
                )
                
                user_analysis.append(user_result)
        
        # 결과 분류
        passed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_PASS]
        warning_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_WARNING]
        failed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_FAIL]
        error_users = [u for u in user_analysis if u['status'] == 'error']
        
        # 비활성 사용자 카운트
        inactive_users_count = len(warning_users) + len(failed_users)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 비활성 사용자 찾기
        if failed_users:
            recommendations.append(f'{len(failed_users)}명의 사용자가 180일 이상 활동이 없습니다. 계정을 비활성화하거나 삭제하는 것이 좋습니다. (영향받는 사용자: {", ".join([u["user_name"] for u in failed_users])})')
        
        if warning_users:
            recommendations.append(f'{len(warning_users)}명의 사용자가 90일 이상 활동이 없습니다. 계정이 여전히 필요한지 확인하세요. (영향받는 사용자: {", ".join([u["user_name"] for u in warning_users])})')
        
        # 일반적인 권장사항
        recommendations.append('정기적으로 비활성 사용자를 검토하고 불필요한 계정은 삭제하세요.')
        recommendations.append('사용자 계정 수명 주기 관리 정책을 수립하여 퇴사자 계정을 즉시 비활성화하세요.')
        
        # 데이터 준비
        data = {
            'users': user_analysis,
            'passed_users': passed_users,
            'warning_users': warning_users,
            'failed_users': failed_users,
            'error_users': error_users,
            'inactive_users_count': inactive_users_count,
            'total_users_count': len(user_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_users) > 0:
            message = f'{len(user_analysis)}명의 사용자 중 {len(failed_users)}명이 장기간 비활성 상태입니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_users) > 0:
            message = f'{len(user_analysis)}명의 사용자 중 {len(warning_users)}명이 비활성 상태입니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 사용자({len(passed_users)}명)가 활성 상태이거나 최근에 생성되었습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'비활성 사용자 검사 중 오류가 발생했습니다: {str(e)}')