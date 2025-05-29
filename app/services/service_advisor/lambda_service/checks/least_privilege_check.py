import boto3
import json
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run() -> Dict[str, Any]:
    """
    Lambda 함수의 실행 역할(IAM Role)이 최소 권한 원칙을 따르는지 검사합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        iam_client = create_boto3_client('iam')
        
        # Lambda 함수 정보 수집
        functions = lambda_client.list_functions()
        
        # 함수 분석 결과
        function_analysis = []
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            role_arn = function.get('Role', '')
            
            # 역할 이름 추출
            role_name = role_arn.split('/')[-1] if '/' in role_arn else role_arn.split(':')[-1]
            
            # 역할 정책 확인
            risky_policies = []
            try:
                # 관리형 정책 확인
                attached_policies = iam_client.list_attached_role_policies(RoleName=role_name).get('AttachedPolicies', [])
                
                for policy in attached_policies:
                    policy_name = policy.get('PolicyName', '')
                    if any(p in policy_name for p in ['AdministratorAccess', 'FullAccess', 'PowerUserAccess']):
                        risky_policies.append(policy_name)
                
                # 인라인 정책 확인
                inline_policies = iam_client.list_role_policies(RoleName=role_name).get('PolicyNames', [])
                
                for policy_name in inline_policies:
                    policy_doc = iam_client.get_role_policy(
                        RoleName=role_name,
                        PolicyName=policy_name
                    ).get('PolicyDocument', {})
                    
                    if isinstance(policy_doc, str):
                        try:
                            policy_doc = json.loads(policy_doc)
                        except:
                            continue
                    
                    statements = policy_doc.get('Statement', [])
                    if not isinstance(statements, list):
                        statements = [statements]
                        
                    for statement in statements:
                        effect = statement.get('Effect')
                        action = statement.get('Action')
                        resource = statement.get('Resource')
                        
                        # "Effect": "Allow", "Action": "*", "Resource": "*" 패턴 확인
                        if (effect == 'Allow' and 
                            (action == '*' or (isinstance(action, list) and '*' in action)) and
                            (resource == '*' or (isinstance(resource, list) and '*' in resource))):
                            risky_policies.append(f"인라인 정책: {policy_name}")
            
            except Exception as e:
                # IAM 권한 부족 등의 이유로 정책 확인 실패
                risky_policies = ['확인 불가 (IAM 권한 부족)']
            
            # 최소 권한 원칙 분석
            status = RESOURCE_STATUS_PASS  # 기본값은 통과
            advice = None
            status_text = None
            
            # 위험한 정책이 발견된 경우
            if risky_policies:
                status = RESOURCE_STATUS_FAIL
                status_text = '보안 개선 필요'
                advice = f'이 Lambda 함수의 실행 역할({role_name})에 과도하게 넓은 권한이 부여되어 있습니다. 최소 권한 원칙에 따라 필요한 권한만 부여하도록 IAM 정책을 수정하세요.'
            else:
                status_text = '최적화됨'
                advice = '이 함수의 실행 역할은 최소 권한 원칙을 따르고 있습니다.'
            
            # 표준화된 리소스 결과 생성
            function_result = create_resource_result(
                resource_id=function_name,
                status=status,
                advice=advice,
                status_text=status_text,
                function_name=function_name,
                role_name=role_name,
                risky_policies=risky_policies
            )
            
            function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        
        # 최적화 필요 함수 카운트
        security_needed_count = len(failed_functions)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 최소 권한 원칙이 필요한 함수 찾기
        if failed_functions:
            recommendations.append(f'{len(failed_functions)}개 함수의 실행 역할에 과도하게 넓은 권한이 부여되어 있습니다. 최소 권한 원칙에 따라 필요한 권한만 부여하도록 IAM 정책을 수정하세요. (영향받는 함수: {", ".join([f["function_name"] for f in failed_functions])})')
        
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
            message = f'{len(function_analysis)}개 함수 중 {security_needed_count}개가 최소 권한 원칙을 따르지 않습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 함수({len(passed_functions)}개)가 최소 권한 원칙을 따르고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Lambda 최소 권한 원칙 검사 중 오류가 발생했습니다: {str(e)}')