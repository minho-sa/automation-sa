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
    Lambda 함수의 실행 역할이 최소 권한 원칙을 따르는지 검사합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda', role_arn=role_arn)
        iam_client = create_boto3_client('iam', role_arn=role_arn)
        
        # Lambda 함수 정보 수집
        functions = lambda_client.list_functions()
        
        # 함수 분석 결과
        function_analysis = []
        
        # 과도한 권한을 가진 관리형 정책 목록
        overly_permissive_policies = [
            'arn:aws:iam::aws:policy/AdministratorAccess',
            'arn:aws:iam::aws:policy/PowerUserAccess',
            'arn:aws:iam::aws:policy/AmazonS3FullAccess',
            'arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess',
            'arn:aws:iam::aws:policy/AmazonRDSFullAccess',
            'arn:aws:iam::aws:policy/AmazonEC2FullAccess'
        ]
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            role_name = function['Role'].split('/')[-1]  # ARN에서 역할 이름 추출
            
            # 역할에 연결된 정책 가져오기
            try:
                attached_policies = iam_client.list_attached_role_policies(
                    RoleName=role_name
                )
                
                # 인라인 정책 가져오기
                inline_policies = iam_client.list_role_policies(
                    RoleName=role_name
                )
                
                # 과도한 권한 확인
                has_overly_permissive_policy = False
                problematic_policies = []
                
                for policy in attached_policies.get('AttachedPolicies', []):
                    if policy['PolicyArn'] in overly_permissive_policies:
                        has_overly_permissive_policy = True
                        problematic_policies.append(policy['PolicyName'])
                
                # 최소 권한 분석
                status = RESOURCE_STATUS_PASS  # 기본값은 통과
                advice = None
                status_text = None
                
                if has_overly_permissive_policy:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '과도한 권한'
                    advice = f'이 함수의 실행 역할에 과도한 권한이 부여되어 있습니다: {", ".join(problematic_policies)}. 최소 권한 원칙에 따라 필요한 권한만 부여하세요.'
                else:
                    status_text = '적절한 권한'
                    advice = f'이 함수의 실행 역할은 최소 권한 원칙을 따르고 있습니다.'
                
            except Exception as e:
                # IAM 역할 액세스 오류
                status = RESOURCE_STATUS_FAIL
                status_text = '확인 불가'
                advice = f'IAM 역할 정보를 가져올 수 없습니다. IAM 권한을 확인하세요.'
            
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
        
        # 권한 수정 필요 함수 카운트
        permission_fix_needed_count = len(failed_functions)
        
        # 권장사항 생성
        recommendations = [
            'Lambda 함수의 실행 역할에 최소 권한 원칙을 적용하세요.',
            '과도하게 넓은 권한(예: AdministratorAccess, PowerUserAccess)을 사용하지 마세요.',
            '함수가 필요로 하는 특정 리소스와 작업에 대한 권한만 부여하세요.',
            'AWS IAM Access Analyzer를 사용하여 사용되지 않는 권한을 식별하세요.'
        ]
        
        # 전체 상태 결정 및 결과 생성
        if permission_fix_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {permission_fix_needed_count}개가 권한 수정이 필요합니다.'
            status = STATUS_WARNING
        else:
            message = f'모든 함수({len(passed_functions)}개)가 최소 권한 원칙을 따르고 있습니다.'
            status = STATUS_OK
        
        return create_unified_check_result(
            status=status,
            message=message,
            resources=function_analysis,
            recommendations=recommendations,
            check_id='lambda-least-privilege'
        )
    
    except Exception as e:
        return create_error_result(f'Lambda 최소 권한 원칙 검사 중 오류가 발생했습니다: {str(e)}')