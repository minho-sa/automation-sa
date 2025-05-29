import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run() -> Dict[str, Any]:
    """
    IAM 액세스 키 교체 상태를 검사하고 오래된 액세스 키에 대한 교체 방안을 제안합니다.
    
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
        import pytz
        now = datetime.now(pytz.UTC)
        
        # 경고 및 실패 기준 (90일 이상은 경고, 180일 이상은 실패)
        warning_threshold = now - timedelta(days=90)
        fail_threshold = now - timedelta(days=180)
        
        for user in users.get('Users', []):
            user_name = user['UserName']
            
            # 액세스 키 목록 가져오기
            try:
                access_keys = iam_client.list_access_keys(UserName=user_name)
                
                # 사용자에게 액세스 키가 없는 경우
                if not access_keys.get('AccessKeyMetadata', []):
                    user_result = create_resource_result(
                        resource_id=user_name,
                        status=RESOURCE_STATUS_PASS,
                        advice='액세스 키가 없습니다.',
                        status_text='액세스 키 없음',
                        user_name=user_name,
                        access_keys=[]
                    )
                    user_analysis.append(user_result)
                    continue
                
                # 각 액세스 키 분석
                user_keys = []
                user_status = RESOURCE_STATUS_PASS
                user_advice = '모든 액세스 키가 최근에 교체되었습니다.'
                user_status_text = '최적화됨'
                
                for key in access_keys.get('AccessKeyMetadata', []):
                    key_id = key['AccessKeyId']
                    create_date = key['CreateDate']
                    status = key['Status']
                    
                    # 키 생성 후 경과 일수
                    days_old = (now - create_date).days
                    
                    # 키 상태 분석
                    key_status = RESOURCE_STATUS_PASS
                    key_advice = f'액세스 키가 {days_old}일 전에 생성되었습니다.'
                    
                    if create_date < fail_threshold:
                        key_status = RESOURCE_STATUS_FAIL
                        key_advice = f'액세스 키가 {days_old}일 동안 교체되지 않았습니다. 즉시 교체하세요.'
                        user_status = RESOURCE_STATUS_FAIL
                        user_advice = '오래된 액세스 키가 있습니다. 즉시 교체하세요.'
                        user_status_text = '교체 필요'
                    elif create_date < warning_threshold:
                        key_status = RESOURCE_STATUS_WARNING
                        key_advice = f'액세스 키가 {days_old}일 동안 교체되지 않았습니다. 곧 교체하세요.'
                        if user_status != RESOURCE_STATUS_FAIL:
                            user_status = RESOURCE_STATUS_WARNING
                            user_advice = '오래된 액세스 키가 있습니다. 곧 교체하세요.'
                            user_status_text = '교체 권장'
                    
                    user_keys.append({
                        'id': key_id,
                        'create_date': create_date.strftime('%Y-%m-%d'),
                        'days_old': days_old,
                        'status': status,
                        'rotation_status': key_status,
                        'advice': key_advice
                    })
                
                # 표준화된 리소스 결과 생성
                user_result = create_resource_result(
                    resource_id=user_name,
                    status=user_status,
                    advice=user_advice,
                    status_text=user_status_text,
                    user_name=user_name,
                    access_keys=user_keys
                )
                
                user_analysis.append(user_result)
                
            except Exception as e:
                # 표준화된 리소스 결과 생성 (오류)
                user_result = create_resource_result(
                    resource_id=user_name,
                    status='error',
                    advice=f'액세스 키 정보를 가져오는 중 오류가 발생했습니다: {str(e)}',
                    status_text='오류',
                    user_name=user_name,
                    access_keys=[]
                )
                
                user_analysis.append(user_result)
        
        # 결과 분류
        passed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_PASS]
        warning_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_WARNING]
        failed_users = [u for u in user_analysis if u['status'] == RESOURCE_STATUS_FAIL]
        error_users = [u for u in user_analysis if u['status'] == 'error']
        
        # 교체 필요 사용자 카운트
        rotation_needed_count = len(warning_users) + len(failed_users)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 교체 필요 사용자 찾기
        if failed_users:
            recommendations.append(f'{len(failed_users)}명의 사용자에게 180일 이상 교체되지 않은 액세스 키가 있습니다. 즉시 교체하세요. (영향받는 사용자: {", ".join([u["user_name"] for u in failed_users])})')
        
        if warning_users:
            recommendations.append(f'{len(warning_users)}명의 사용자에게 90일 이상 교체되지 않은 액세스 키가 있습니다. 곧 교체하세요. (영향받는 사용자: {", ".join([u["user_name"] for u in warning_users])})')
        
        # 일반적인 권장사항
        recommendations.append('액세스 키는 90일마다 교체하는 것이 좋습니다.')
        recommendations.append('프로그래밍 방식 액세스가 필요하지 않은 사용자에게는 액세스 키를 발급하지 마세요.')
        
        # 데이터 준비
        data = {
            'users': user_analysis,
            'passed_users': passed_users,
            'warning_users': warning_users,
            'failed_users': failed_users,
            'error_users': error_users,
            'rotation_needed_count': rotation_needed_count,
            'total_users_count': len(user_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_users) > 0:
            message = f'{len(user_analysis)}명의 사용자 중 {len(failed_users)}명에게 오래된 액세스 키가 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_users) > 0:
            message = f'{len(user_analysis)}명의 사용자 중 {len(warning_users)}명에게 곧 교체가 필요한 액세스 키가 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 사용자({len(passed_users)}명)의 액세스 키가 적절하게 관리되고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'액세스 키 교체 검사 중 오류가 발생했습니다: {str(e)}')