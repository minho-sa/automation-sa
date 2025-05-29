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
    Lambda 함수의 태그 관리 상태를 검사하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        
        # Lambda 함수 정보 수집
        functions = lambda_client.list_functions()
        
        # 함수 분석 결과
        function_analysis = []
        
        # 필수 태그 정의
        required_tags = ['Owner', 'Environment', 'Project']
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            
            # 함수 태그 가져오기
            try:
                tags_response = lambda_client.list_tags(Resource=function['FunctionArn'])
                tags = tags_response.get('Tags', {})
            except Exception:
                tags = {}
            
            # 태그 관리 분석
            status = RESOURCE_STATUS_PASS  # 기본값은 통과
            advice = None
            status_text = None
            
            # 태그 없음
            if not tags:
                status = RESOURCE_STATUS_FAIL
                status_text = '태그 없음'
                advice = f'태그가 없습니다. 리소스 관리 및 비용 할당을 위해 {", ".join(required_tags)} 태그를 추가하세요.'
            else:
                # 누락된 필수 태그 확인
                missing_tags = [tag for tag in required_tags if tag not in tags]
                
                if missing_tags:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '태그 부족'
                    advice = f'필수 태그({", ".join(missing_tags)})가 누락되었습니다. 리소스 관리 및 비용 할당을 위해 추가하세요.'
                else:
                    status_text = '태그 완료'
                    advice = '모든 필수 태그가 적절하게 설정되어 있습니다.'
            
            # 표준화된 리소스 결과 생성
            function_result = create_resource_result(
                resource_id=function_name,
                status=status,
                advice=advice,
                status_text=status_text,
                function_name=function_name,
                existing_tags=list(tags.keys()) if tags else [],
                missing_tags=[tag for tag in required_tags if tag not in tags]
            )
            
            function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        warning_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_WARNING]
        
        # 태그 관리 필요 함수 카운트
        tag_needed_count = len(failed_functions) + len(warning_functions)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 태그 없는 함수 찾기
        if failed_functions:
            recommendations.append(f'태그가 없는 {len(failed_functions)}개 함수에 필수 태그({", ".join(required_tags)})를 추가하세요. (영향받는 함수: {", ".join([f["function_name"] for f in failed_functions])})')
        
        # 태그 부족 함수 찾기
        if warning_functions:
            recommendations.append(f'태그가 부족한 {len(warning_functions)}개 함수에 누락된 필수 태그를 추가하세요. (영향받는 함수: {", ".join([f["function_name"] for f in warning_functions])})')
        
        # 데이터 준비
        data = {
            'functions': function_analysis,
            'passed_functions': passed_functions,
            'failed_functions': failed_functions,
            'warning_functions': warning_functions,
            'tag_needed_count': tag_needed_count,
            'total_functions_count': len(function_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_functions) > 0:
            message = f'{len(function_analysis)}개 함수 중 {len(failed_functions)}개가 태그가 없고, {len(warning_functions)}개가 태그가 부족합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_functions) > 0:
            message = f'{len(function_analysis)}개 함수 중 {len(warning_functions)}개가 일부 필수 태그가 누락되었습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 함수({len(passed_functions)}개)가 적절한 태그로 관리되고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Lambda 태그 관리 검사 중 오류가 발생했습니다: {str(e)}')