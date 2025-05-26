import boto3

def assume_role(role_arn, region, session_name="AssumedRoleSession", duration_seconds=3600, 
              aws_access_key=None, aws_secret_key=None, aws_session_token=None):
    """
    지정된 IAM 역할을 수임하여 임시 자격 증명을 반환합니다.
    
    Args:
        role_arn: 수임할 역할의 ARN
        region: AWS 리전 이름
        session_name: 세션 이름 (기본값: "AssumedRoleSession")
        duration_seconds: 세션 유효 기간 (초, 기본값: 3600)
        aws_access_key: AWS 액세스 키 (선택 사항)
        aws_secret_key: AWS 시크릿 키 (선택 사항)
        aws_session_token: AWS 세션 토큰 (선택 사항)
        
    Returns:
        임시 자격 증명 딕셔너리 (access_key, secret_key, session_token)
    """
    # 명시적 자격 증명이 제공된 경우 사용
    if aws_access_key and aws_secret_key:
        sts_client = boto3.client(
            'sts', 
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_session_token=aws_session_token
        )
    else:
        # 기본 자격 증명 공급자 체인 사용
        from config import Config
        sts_client = boto3.client(
            'sts', 
            region_name=region,
            aws_access_key_id=Config.AWS_ACCESS_KEY,
            aws_secret_access_key=Config.AWS_SECRET_KEY
        )
    
    # 역할 수임
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        DurationSeconds=duration_seconds
    )
    
    # 임시 자격 증명 반환
    credentials = response['Credentials']
    return {
        'access_key': credentials['AccessKeyId'],
        'secret_key': credentials['SecretAccessKey'],
        'session_token': credentials['SessionToken']
    }

def create_boto3_client(service_name, region, auth_type='access_key', **auth_params):
    """
    인증 유형에 따라 boto3 클라이언트를 생성합니다.
    
    Args:
        service_name: AWS 서비스 이름 (예: 's3', 'ec2', 'iam' 등)
        region: AWS 리전 이름
        auth_type: 인증 유형 ('access_key' 또는 'role_arn')
        **auth_params: 인증 유형에 따른 추가 파라미터
            - access_key 인증: aws_access_key, aws_secret_key, aws_session_token(선택)
            - role_arn 인증: role_arn, aws_access_key, aws_secret_key, aws_session_token(선택)
        
    Returns:
        boto3 클라이언트 객체
    """
    client_kwargs = {'region_name': region}
    
    if auth_type == 'access_key':
        # 직접 액세스 키로 인증
        client_kwargs['aws_access_key_id'] = auth_params.get('aws_access_key')
        client_kwargs['aws_secret_access_key'] = auth_params.get('aws_secret_key')
        if 'aws_session_token' in auth_params and auth_params['aws_session_token']:
            client_kwargs['aws_session_token'] = auth_params['aws_session_token']
    
    elif auth_type == 'role_arn':
        # 역할 수임하여 임시 자격 증명 획득
        temp_credentials = assume_role(
            role_arn=auth_params.get('role_arn'),
            region=region,
            aws_access_key=auth_params.get('aws_access_key'),
            aws_secret_key=auth_params.get('aws_secret_key'),
            aws_session_token=auth_params.get('aws_session_token')
        )
        
        # 임시 자격 증명으로 클라이언트 설정
        client_kwargs['aws_access_key_id'] = temp_credentials['access_key']
        client_kwargs['aws_secret_access_key'] = temp_credentials['secret_key']
        client_kwargs['aws_session_token'] = temp_credentials['session_token']
    
    else:
        raise ValueError(f"Unsupported authentication type: {auth_type}")
    
    # boto3 클라이언트 생성 및 반환
    return boto3.client(service_name, **client_kwargs)