import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL,
    create_unified_check_result, create_resource_result, create_error_result
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    Lambda 함수의 코드 서명 구성을 검사합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda', role_arn=role_arn)
        
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
            
            # 환경 태그 확인
            environment = tags.get('Environment', '').lower()
            is_production = environment in ['prod', 'production']
            
            # 코드 서명 구성 확인
            try:
                code_signing_config = lambda_client.get_function_code_signing_config(
                    FunctionName=function_name
                )
                has_code_signing = 'CodeSigningConfigArn' in code_signing_config
            except Exception:
                has_code_signing = False
            
            # 코드 서명 분석
            status = RESOURCE_STATUS_PASS  # 기본값은 통과
            advice = None
            status_text = None
            
            if is_production and not has_code_signing:
                status = RESOURCE_STATUS_FAIL
                status_text = '보안 위험'
                advice = f'이 함수는 프로덕션 환경에서 실행되지만 코드 서명이 구성되어 있지 않습니다. 코드 무결성을 보장하기 위해 코드 서명을 활성화하세요.'
            elif not is_production and has_code_signing:
                status_text = '최적화됨'
                advice = f'이 함수는 프로덕션 환경이 아니지만 코드 서명이 구성되어 있습니다. 보안 모범 사례를 따르고 있습니다.'
            elif is_production and has_code_signing:
                status_text = '최적화됨'
                advice = f'이 함수는 프로덕션 환경에서 실행되며 코드 서명이 적절하게 구성되어 있습니다.'
            else:
                status_text = '최적화됨'
                advice = f'이 함수는 프로덕션 환경이 아니므로 코드 서명이 필요하지 않습니다.'
            
            # 표준화된 리소스 결과 생성
            function_result = create_resource_result(
                resource_id=function_name,
                resource_name=function_name,
                status=status,
                status_text=status_text,
                advice=advice
            )
            
            function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        
        # 코드 서명 필요 함수 카운트
        code_signing_needed_count = len(failed_functions)
        
        # 권장사항 생성
        recommendations = [
            '프로덕션 환경의 모든 Lambda 함수에 코드 서명을 구성하세요.',
            '코드 서명을 통해 승인된 코드만 배포되도록 하여 보안을 강화하세요.',
            'AWS Signer를 사용하여 코드 서명 인증서를 관리하세요.',
            '코드 서명 정책을 구현하여 모든 프로덕션 배포에 서명을 요구하세요.'
        ]
        
        # 전체 상태 결정 및 결과 생성
        if code_signing_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {code_signing_needed_count}개가 코드 서명 구성이 필요합니다.'
            status = STATUS_WARNING
        else:
            message = f'모든 함수({len(passed_functions)}개)가 적절한 코드 서명 구성으로 설정되어 있습니다.'
            status = STATUS_OK
        
        return create_unified_check_result(
            status=status,
            message=message,
            resources=function_analysis,
            recommendations=recommendations,
            check_id='lambda-code-signing'
        )
    
    except Exception as e:
        return create_error_result(f'Lambda 코드 서명 검사 중 오류가 발생했습니다: {str(e)}')