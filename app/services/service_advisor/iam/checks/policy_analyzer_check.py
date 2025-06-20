import boto3
import json
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    IAM 정책의 보안 위험을 분석하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        iam_client = create_boto3_client('iam', role_arn=role_arn)
        
        # 관리형 정책 목록 가져오기
        managed_policies = []
        paginator = iam_client.get_paginator('list_policies')
        for page in paginator.paginate(Scope='Local'):  # 고객 관리형 정책만 검사
            managed_policies.extend(page['Policies'])
        
        # 정책 분석 결과
        policy_analysis = []
        
        for policy in managed_policies:
            policy_name = policy['PolicyName']
            policy_arn = policy['Arn']
            
            # 정책 문서 가져오기
            policy_version = iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=policy['DefaultVersionId']
            )
            policy_document = policy_version['PolicyVersion']['Document']
            
            # 정책 문서 분석
            risky_statements = []
            has_admin_access = False
            has_wildcard_resource = False
            has_wildcard_action = False
            
            for statement in policy_document.get('Statement', []):
                effect = statement.get('Effect')
                action = statement.get('Action', [])
                resource = statement.get('Resource', [])
                
                # 문자열을 리스트로 변환
                if isinstance(action, str):
                    action = [action]
                if isinstance(resource, str):
                    resource = [resource]
                
                # 관리자 액세스 확인
                if effect == 'Allow' and '*' in action and '*' in resource:
                    has_admin_access = True
                    risky_statements.append('관리자 액세스: 모든 작업(*) 및 모든 리소스(*) 허용')
                
                # 와일드카드 리소스 확인
                elif effect == 'Allow' and '*' in resource:
                    has_wildcard_resource = True
                    risky_statements.append(f'와일드카드 리소스: {", ".join(action)}에 대해 모든 리소스(*) 허용')
                
                # 와일드카드 작업 확인
                elif effect == 'Allow' and any('*' in a for a in action):
                    has_wildcard_action = True
                    wildcard_actions = [a for a in action if '*' in a]
                    risky_statements.append(f'와일드카드 작업: {", ".join(wildcard_actions)} 허용')
            
            # 상태 및 권장 사항 결정
            status = RESOURCE_STATUS_PASS
            advice = None
            status_text = None
            
            if has_admin_access:
                status = RESOURCE_STATUS_FAIL
                status_text = '관리자 액세스'
                advice = '이 정책은 모든 작업과 모든 리소스에 대한 액세스를 허용합니다. 최소 권한 원칙에 따라 필요한 권한만 부여하도록 정책을 수정하세요.'
            elif has_wildcard_resource:
                status = RESOURCE_STATUS_WARNING
                status_text = '와일드카드 리소스'
                advice = '이 정책은 특정 작업에 대해 모든 리소스에 액세스할 수 있습니다. 가능한 경우 특정 리소스 ARN을 지정하세요.'
            elif has_wildcard_action:
                status = RESOURCE_STATUS_WARNING
                status_text = '와일드카드 작업'
                advice = '이 정책은 와일드카드 작업을 사용합니다. 가능한 경우 필요한 특정 작업만 명시적으로 허용하세요.'
            else:
                status_text = '최적화됨'
                advice = '이 정책은 최소 권한 원칙을 준수합니다.'
            
            # 표준화된 리소스 결과 생성
            policy_result = create_resource_result(
                resource_id=policy_arn,
                status=status,
                advice=advice,
                status_text=status_text,
                policy_name=policy_name,
                policy_arn=policy_arn,
                risky_statements=risky_statements,
                has_admin_access=has_admin_access,
                has_wildcard_resource=has_wildcard_resource,
                has_wildcard_action=has_wildcard_action
            )
            
            policy_analysis.append(policy_result)
        
        # 결과 분류
        passed_policies = [p for p in policy_analysis if p['status'] == RESOURCE_STATUS_PASS]
        warning_policies = [p for p in policy_analysis if p['status'] == RESOURCE_STATUS_WARNING]
        failed_policies = [p for p in policy_analysis if p['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 정책 카운트
        improvement_needed_count = len(warning_policies) + len(failed_policies)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 관리자 액세스 정책 찾기
        if failed_policies:
            recommendations.append(f'{len(failed_policies)}개 정책이 관리자 액세스를 허용합니다. 최소 권한 원칙에 따라 수정하세요. (영향받는 정책: {", ".join([p["policy_name"] for p in failed_policies])})')
        
        # 와일드카드 사용 정책 찾기
        if warning_policies:
            recommendations.append(f'{len(warning_policies)}개 정책이 와일드카드 리소스 또는 작업을 사용합니다. 가능한 경우 특정 리소스와 작업을 지정하세요. (영향받는 정책: {", ".join([p["policy_name"] for p in warning_policies])})')
        
        # 일반적인 권장사항
        recommendations.append('최소 권한 원칙에 따라 필요한 권한만 부여하세요.')
        recommendations.append('와일드카드 대신 특정 리소스 ARN과 작업을 지정하세요.')
        recommendations.append('정기적으로 정책을 검토하고 불필요한 권한을 제거하세요.')
        
        # 데이터 준비
        data = {
            'policies': policy_analysis,
            'passed_policies': passed_policies,
            'warning_policies': warning_policies,
            'failed_policies': failed_policies,
            'improvement_needed_count': improvement_needed_count,
            'total_policies_count': len(policy_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_policies) > 0:
            message = f'{len(policy_analysis)}개 정책 중 {len(failed_policies)}개가 관리자 액세스를 허용합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_policies) > 0:
            message = f'{len(policy_analysis)}개 정책 중 {len(warning_policies)}개가 와일드카드 리소스 또는 작업을 사용합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 정책({len(passed_policies)}개)이 최소 권한 원칙을 준수합니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'정책 분석 중 오류가 발생했습니다: {str(e)}')