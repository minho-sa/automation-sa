import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    IAM 계정 암호 정책을 검사하고 보안 강화 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        iam_client = create_boto3_client('iam')
        
        # 암호 정책 가져오기
        try:
            policy = iam_client.get_account_password_policy()['PasswordPolicy']
        except iam_client.exceptions.NoSuchEntityException:
            # 암호 정책이 설정되지 않은 경우
            return create_check_result(
                status=STATUS_WARNING,
                message='계정 암호 정책이 설정되지 않았습니다.',
                data={
                    'policy': None,
                    'issues': ['암호 정책이 설정되지 않음'],
                    'recommendations': [
                        '강력한 암호 정책을 설정하세요.',
                        '최소 암호 길이를 14자 이상으로 설정하세요.',
                        '대문자, 소문자, 숫자, 특수 문자를 요구하세요.',
                        '암호 재사용을 방지하세요.',
                        '최대 암호 사용 기간을 90일로 설정하세요.'
                    ]
                },
                recommendations=[
                    '강력한 암호 정책을 설정하세요.',
                    '최소 암호 길이를 14자 이상으로 설정하세요.',
                    '대문자, 소문자, 숫자, 특수 문자를 요구하세요.',
                    '암호 재사용을 방지하세요.',
                    '최대 암호 사용 기간을 90일로 설정하세요.'
                ]
            )
        
        # 정책 문제점 분석
        issues = []
        
        # 최소 암호 길이 검사
        min_length = policy.get('MinimumPasswordLength', 0)
        if min_length < 14:
            issues.append(f'최소 암호 길이가 {min_length}자로 설정되어 있습니다.')
        
        # 암호 복잡성 요구사항 검사
        if not policy.get('RequireUppercaseCharacters', False):
            issues.append('대문자 요구사항이 설정되지 않았습니다.')
        
        if not policy.get('RequireLowercaseCharacters', False):
            issues.append('소문자 요구사항이 설정되지 않았습니다.')
        
        if not policy.get('RequireNumbers', False):
            issues.append('숫자 요구사항이 설정되지 않았습니다.')
        
        if not policy.get('RequireSymbols', False):
            issues.append('특수 문자 요구사항이 설정되지 않았습니다.')
        
        # 암호 만료 검사
        if not policy.get('ExpirePasswords', False):
            issues.append('암호 만료가 설정되지 않았습니다.')
        else:
            max_age = policy.get('MaxPasswordAge', 0)
            if max_age > 90:
                issues.append(f'최대 암호 사용 기간이 {max_age}일로 설정되어 있습니다.')
        
        # 암호 재사용 방지 검사
        password_reuse_prevention = policy.get('PasswordReusePrevention', 0)
        if password_reuse_prevention < 24:
            issues.append(f'암호 재사용 방지가 {password_reuse_prevention}개로 설정되어 있습니다.')
        
        # 권장사항 생성
        recommendations = [
            '최소 14자 이상의 암호 길이를 설정하세요.',
            '대소문자, 숫자, 특수문자를 모두 요구하세요.',
            '90일 만료 및 24개 재사용 방지를 설정하세요.'
        ]
        
        # 결과 상태 결정
        if issues:
            status = STATUS_WARNING
            message = f'계정 암호 정책에 {len(issues)}개의 문제점이 있습니다.'
        else:
            status = STATUS_OK
            message = '계정 암호 정책이 모범 사례를 준수합니다.'
        
        # 데이터 준비
        data = {
            'policy': policy,
            'issues': issues,
            'recommendations': recommendations
        }
        
        # 결과 생성
        return create_check_result(
            status=status,
            message=message,
            data=data,
            recommendations=recommendations
        )
    
    except Exception as e:
        return create_error_result(f'암호 정책 검사 중 오류가 발생했습니다: {str(e)}')