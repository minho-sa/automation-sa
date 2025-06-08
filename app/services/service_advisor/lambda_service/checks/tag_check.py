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
    Lambda 함수의 태그 관리 상태를 검사합니다.
    
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
        
        # 권장 태그 목록
        recommended_tags = ['Environment', 'Project', 'Owner', 'CostCenter']
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            
            # 함수 태그 가져오기
            try:
                tags_response = lambda_client.list_tags(Resource=function['FunctionArn'])
                tags = tags_response.get('Tags', {})
            except Exception:
                tags = {}
            
            # 태그 분석
            status = RESOURCE_STATUS_PASS  # 기본값은 통과
            advice = None
            status_text = None
            
            if not tags:
                status = RESOURCE_STATUS_FAIL
                status_text = '태그 없음'
                advice = f'이 함수에는 태그가 없습니다. 리소스 관리 및 비용 할당을 위해 태그를 추가하세요.'
            else:
                missing_tags = [tag for tag in recommended_tags if tag not in tags]
                
                if missing_tags:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '태그 부족'
                    advice = f'권장 태그가 누락되었습니다: {", ".join(missing_tags)}. 리소스 관리 및 비용 할당을 위해 이러한 태그를 추가하세요.'
                else:
                    status_text = '적절한 태그'
                    advice = f'이 함수에는 모든 권장 태그가 있습니다.'
            
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
        
        # 태그 추가 필요 함수 카운트
        tagging_needed_count = len(failed_functions)
        
        # 권장사항 생성
        recommendations = [
            '모든 Lambda 함수에 일관된 태그를 추가하세요.',
            f'권장 태그: {", ".join(recommended_tags)}',
            '태그를 사용하여 비용 할당 및 리소스 관리를 개선하세요.',
            '태그 지정 정책을 구현하여 일관된 태그 지정을 보장하세요.'
        ]
        
        # 전체 상태 결정 및 결과 생성
        if tagging_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {tagging_needed_count}개가 태그 추가가 필요합니다.'
            status = STATUS_WARNING
        else:
            message = f'모든 함수({len(passed_functions)}개)가 적절하게 태그가 지정되어 있습니다.'
            status = STATUS_OK
        
        return create_unified_check_result(
            status=status,
            message=message,
            resources=function_analysis,
            recommendations=recommendations,
            check_id='lambda-tags'
        )
    
    except Exception as e:
        return create_error_result(f'Lambda 태그 검사 중 오류가 발생했습니다: {str(e)}')