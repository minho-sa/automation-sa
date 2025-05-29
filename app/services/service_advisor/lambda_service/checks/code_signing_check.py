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
    Lambda 함수의 코드 서명 구성을 검사하고 보안 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        
        # Lambda 함수 정보 수집
        functions = lambda_client.list_functions()
        
        # 함수 분석 결과
        function_analysis = []
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            
            # 함수 태그 가져오기
            try:
                tags_response = lambda_client.list_tags(Resource=function['FunctionArn'])
                tags = tags_response.get('Tags', {})
            except Exception:
                tags = {}
            
            # 프로덕션 환경인지 확인
            is_production = False
            for key, value in tags.items():
                if (key.lower() in ['environment', 'env'] and 
                    value.lower() in ['prod', 'production']):
                    is_production = True
                    break
            
            # 함수 이름으로도 프로덕션 환경 확인
            if not is_production and (function_name.lower().startswith(('prod-', 'production-')) or 
                                     'prod' in function_name.lower()):
                is_production = True
            
            # 코드 서명 구성 확인
            try:
                code_signing_config = lambda_client.get_function_code_signing_config(
                    FunctionName=function_name
                ).get('CodeSigningConfigArn')
            except Exception:
                code_signing_config = None
            
            # 코드 서명 분석
            status = RESOURCE_STATUS_PASS  # 기본값은 통과
            advice = None
            status_text = None
            
            # 프로덕션 환경이지만 코드 서명이 없는 경우
            if is_production and not code_signing_config:
                status = RESOURCE_STATUS_FAIL
                status_text = '보안 개선 필요'
                advice = '이 프로덕션 Lambda 함수에 코드 서명이 구성되어 있지 않습니다. 코드 무결성과 보안을 강화하기 위해 코드 서명을 구성하세요.'
            else:
                status_text = '최적화됨'
                advice = '이 함수는 코드 서명이 적절하게 구성되어 있거나 프로덕션 환경이 아니어서 필요하지 않습니다.'
            
            # 표준화된 리소스 결과 생성
            function_result = create_resource_result(
                resource_id=function_name,
                status=status,
                advice=advice,
                status_text=status_text,
                function_name=function_name,
                is_production=is_production,
                has_code_signing=bool(code_signing_config)
            )
            
            function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        
        # 최적화 필요 함수 카운트
        security_needed_count = len(failed_functions)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 코드 서명이 필요한 함수 찾기
        if failed_functions:
            recommendations.append(f'프로덕션 환경의 {len(failed_functions)}개 함수에 코드 서명을 구성하여 코드 무결성과 보안을 강화하세요. (영향받는 함수: {", ".join([f["function_name"] for f in failed_functions])})')
        
        # 데이터 준비
        data = {
            'functions': function_analysis,
            'passed_functions': passed_functions,
            'failed_functions': failed_functions,
            'security_needed_count': security_needed_count,
            'total_functions_count': len(function_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if security_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {security_needed_count}개가 코드 서명 구성이 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 함수({len(function_analysis)}개)가 적절한 코드 서명 구성을 가지고 있거나 필요하지 않습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Lambda 코드 서명 검사 중 오류가 발생했습니다: {str(e)}')