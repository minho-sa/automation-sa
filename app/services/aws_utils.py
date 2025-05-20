import boto3
from typing import Dict, Optional, Tuple

def get_credentials_from_access_key(access_key: str, secret_key: str) -> Dict:
    """
    액세스 키와 시크릿 키로부터 AWS 자격 증명을 반환합니다.
    """
    return {
        'aws_access_key_id': access_key,
        'aws_secret_access_key': secret_key
    }

def get_credentials_from_role_arn(role_arn: str, session_name: str = "AssumeRoleSession") -> Dict:
    """
    ARN을 사용하여 STS를 통해 역할을 수임하고 임시 자격 증명을 반환합니다.
    
    Args:
        role_arn: 수임할 역할의 ARN
        session_name: 세션 이름 (기본값: "AssumeRoleSession")
        
    Returns:
        임시 자격 증명을 포함하는 딕셔너리
    """
    try:
        # 기본 자격 증명 공급자 체인 사용
        sts_client = boto3.client('sts')
            
        assumed_role = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=session_name
        )
        
        credentials = assumed_role['Credentials']
        return {
            'aws_access_key_id': credentials['AccessKeyId'],
            'aws_secret_access_key': credentials['SecretAccessKey'],
            'aws_session_token': credentials['SessionToken']
        }
    except Exception as e:
        raise Exception(f"역할 수임 중 오류 발생: {str(e)}")

def get_aws_credentials(access_key: Optional[str] = None, 
                       secret_key: Optional[str] = None, 
                       role_arn: Optional[str] = None) -> Dict:
    """
    제공된 인증 방식에 따라 AWS 자격 증명을 반환합니다.
    
    Args:
        access_key: AWS 액세스 키 ID (선택 사항)
        secret_key: AWS 시크릿 액세스 키 (선택 사항)
        role_arn: 수임할 역할의 ARN (선택 사항)
        
    Returns:
        AWS 자격 증명을 포함하는 딕셔너리
    
    Raises:
        ValueError: 유효한 자격 증명 조합이 제공되지 않은 경우
    """
    if role_arn:
        # 역할 ARN으로 자격 증명 획득
        return get_credentials_from_role_arn(role_arn)
    elif access_key and secret_key:
        return get_credentials_from_access_key(access_key, secret_key)
    else:
        raise ValueError("유효한 AWS 자격 증명이 제공되지 않았습니다. 액세스 키와 시크릿 키 또는 역할 ARN을 제공하세요.")