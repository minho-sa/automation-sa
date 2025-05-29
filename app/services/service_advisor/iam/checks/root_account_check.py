import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run() -> Dict[str, Any]:
    """
    AWS 계정의 루트 사용자 보안 설정을 검사하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        iam_client = create_boto3_client('iam')
        
        # 계정 요약 정보 가져오기
        account_summary = iam_client.get_account_summary()
        
        # 루트 계정 보안 설정 확인
        root_mfa_enabled = account_summary.get('SummaryMap', {}).get('AccountMFAEnabled', 0) == 1
        
        # 루트 액세스 키 확인
        credential_report = None
        try:
            # 보고서 생성
            iam_client.generate_credential_report()
            
            # 보고서 가져오기
            report_response = iam_client.get_credential_report()
            report_content = report_response['Content'].decode('utf-8')
            
            # 보고서 파싱
            report_lines = report_content.split('\n')
            headers = report_lines[0].split(',')
            
            for line in report_lines[1:]:
                if not line:
                    continue
                    
                values = line.split(',')
                user_data = dict(zip(headers, values))
                
                if user_data.get('user') == '<root_account>':
                    credential_report = user_data
                    break
        except Exception:
            credential_report = None
        
        # 루트 액세스 키 상태
        has_root_access_key = False
        if credential_report:
            has_root_access_key = (
                credential_report.get('access_key_1_active', 'false').lower() == 'true' or
                credential_report.get('access_key_2_active', 'false').lower() == 'true'
            )
        
        # 분석 결과
        analysis_items = []
        
        # MFA 설정 분석
        mfa_status = RESOURCE_STATUS_PASS if root_mfa_enabled else RESOURCE_STATUS_FAIL
        mfa_status_text = '설정됨' if root_mfa_enabled else '설정되지 않음'
        mfa_advice = '루트 계정에 MFA가 적절하게 설정되어 있습니다.' if root_mfa_enabled else '루트 계정에 MFA를 즉시 설정하세요. 이는 계정 보안의 가장 중요한 요소입니다.'
        
        mfa_result = create_resource_result(
            resource_id='root-mfa',
            status=mfa_status,
            advice=mfa_advice,
            status_text=mfa_status_text,
            check_name='루트 계정 MFA',
            value=mfa_status_text
        )
        analysis_items.append(mfa_result)
        
        # 액세스 키 분석
        if credential_report:
            key_status = RESOURCE_STATUS_FAIL if has_root_access_key else RESOURCE_STATUS_PASS
            key_status_text = '발견됨' if has_root_access_key else '없음'
            key_advice = '루트 계정에 액세스 키가 있습니다. 즉시 삭제하고 필요한 경우 적절한 권한을 가진 IAM 사용자를 사용하세요.' if has_root_access_key else '루트 계정에 액세스 키가 없습니다. 이는 좋은 보안 관행입니다.'
            
            key_result = create_resource_result(
                resource_id='root-access-key',
                status=key_status,
                advice=key_advice,
                status_text=key_status_text,
                check_name='루트 계정 액세스 키',
                value=key_status_text
            )
            analysis_items.append(key_result)
        
        # 결과 분류
        passed_items = [item for item in analysis_items if item['status'] == RESOURCE_STATUS_PASS]
        failed_items = [item for item in analysis_items if item['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 항목 카운트
        improvement_needed_count = len(failed_items)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        if not root_mfa_enabled:
            recommendations.append('루트 계정에 MFA를 즉시 설정하세요. 가상 MFA 디바이스, U2F 보안 키 또는 하드웨어 MFA 디바이스를 사용할 수 있습니다.')
        
        if has_root_access_key:
            recommendations.append('루트 계정의 액세스 키를 즉시 삭제하세요. 프로그래밍 방식 액세스가 필요한 경우 적절한 권한을 가진 IAM 사용자를 사용하세요.')
        
        # 일반적인 권장사항
        recommendations.append('루트 계정은 AWS 계정 생성 및 특정 관리 작업에만 사용하고, 일상적인 작업에는 IAM 사용자를 사용하세요.')
        recommendations.append('루트 계정 이메일 주소와 연결된 이메일 계정에도 강력한 보안 조치를 적용하세요.')
        
        # 데이터 준비
        data = {
            'items': analysis_items,
            'passed_items': passed_items,
            'failed_items': failed_items,
            'improvement_needed_count': improvement_needed_count,
            'total_items_count': len(analysis_items),
            'root_mfa_enabled': root_mfa_enabled,
            'has_root_access_key': has_root_access_key
        }
        
        # 전체 상태 결정 및 결과 생성
        if improvement_needed_count > 0:
            message = f'루트 계정 보안 설정에 {improvement_needed_count}개의 개선이 필요한 항목이 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = '루트 계정 보안 설정이 모범 사례를 준수하고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'루트 계정 보안 설정 검사 중 오류가 발생했습니다: {str(e)}')