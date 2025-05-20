import boto3

def create_boto3_client(service_name, region, aws_access_key=None, aws_secret_key=None, aws_session_token=None):
    """
    제공된 자격 증명을 사용하여 boto3 클라이언트를 생성합니다.
    
    Args:
        service_name: AWS 서비스 이름 (예: 's3', 'ec2', 'iam' 등)
        region: AWS 리전 이름
        aws_access_key: AWS 액세스 키 ID (선택 사항)
        aws_secret_key: AWS 시크릿 액세스 키 (선택 사항)
        aws_session_token: AWS 세션 토큰 (선택 사항)
        
    Returns:
        boto3 클라이언트 객체
    """
    # 자격 증명 설정
    client_kwargs = {
        'aws_access_key_id': aws_access_key,
        'aws_secret_access_key': aws_secret_key,
        'region_name': region
    }
    
    # 세션 토큰이 있는 경우 추가 (STS Assume Role을 통해 얻은 임시 자격 증명)
    if aws_session_token:
        client_kwargs['aws_session_token'] = aws_session_token
    
    # boto3 클라이언트 생성 및 반환
    return boto3.client(service_name, **client_kwargs)