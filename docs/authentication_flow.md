# AWS 인증 방식과 데이터 수집 플로우

이 문서는 AWS Console Check 애플리케이션에서 사용하는 인증 방식과 데이터 수집 플로우를 설명합니다.

## 인증 방식 및 세션 저장 방법

AWS Console Check 애플리케이션은 두 가지 인증 방식을 지원합니다:

1. **액세스 키 인증 방식**
2. **역할 ARN 인증 방식**

### 액세스 키 인증 방식

사용자가 액세스 키와 시크릿 키를 사용하여 로그인할 경우:

```python
# 세션에 저장되는 정보
session['auth_type'] = 'access_key'
session['auth_params'] = {
    'aws_access_key': aws_access_key,
    'aws_secret_key': aws_secret_key
}
```

- 세션에는 `aws_access_key`와 `aws_secret_key`만 저장됩니다.
- ARN 정보는 세션에 저장되지 않습니다.
- 실제 AWS 서비스 호출 시 저장된 액세스 키와 시크릿 키를 직접 사용합니다.

### 역할 ARN 인증 방식

사용자가 역할 ARN을 사용하여 로그인할 경우:

```python
# 세션에 저장되는 정보
session['auth_type'] = 'role_arn'
session['auth_params'] = {
    'role_arn': role_arn
}
```

- 세션에는 `role_arn`만 저장됩니다.
- 액세스 키와 시크릿 키는 세션에 저장되지 않습니다.
- 실제 AWS 서비스 호출 시 ARN을 사용하여 임시 자격 증명을 생성합니다.

## 데이터 수집 플로우 (EC2 예시)

### 1. 사용자 로그인 및 세션 저장

사용자가 로그인하면 인증 방식에 따라 세션에 정보가 저장됩니다.

### 2. 데이터 수집 요청

사용자가 데이터 수집 버튼을 클릭하면 `/start_collection` 엔드포인트가 호출됩니다:

```python
@app.route('/start_collection', methods=['POST'])
@login_required
def start_collection():
    # AWS 자격 증명 가져오기
    auth_type = session.get('auth_type')
    auth_params = session.get('auth_params', {})
    
    # 데이터 수집 시작
    thread = threading.Thread(
        target=collect_data, 
        kwargs={
            'region': region, 
            'user_id': user_id, 
            'selected_services': selected_services, 
            'auth_type': auth_type, 
            'auth_params': auth_params
        }
    )
    thread.daemon = True
    thread.start()
```

### 3. 데이터 수집 함수 호출

`collect_data` 함수는 선택된 서비스에 대해 데이터 수집 함수를 호출합니다:

```python
def collect_data(region, user_id, selected_services=None, auth_type='access_key', auth_params=None):
    # 선택된 서비스만 수집
    for service_key in selected_services:
        if service_key in service_collectors:
            # 해당 서비스의 데이터 수집 함수 호출
            collection_status['all_services_data'][service_key] = service_collectors[service_key](
                region=region, 
                collection_id=collection_status['collection_id'], 
                auth_type=auth_type, 
                **auth_params
            )
```

### 4. EC2 데이터 수집 함수

EC2 데이터 수집 함수는 인증 유형에 따라 boto3 클라이언트를 생성하고 데이터를 수집합니다:

```python
def get_ec2_data(region: str, collection_id: str = None, auth_type: str = 'access_key', **auth_params) -> Dict:
    try:
        # boto3 클라이언트 생성
        ec2_client = create_boto3_client('ec2', region, auth_type=auth_type, **auth_params)
        cloudwatch = create_boto3_client('cloudwatch', region, auth_type=auth_type, **auth_params)
        
        # EC2 인스턴스 정보 수집
        response = ec2_client.describe_instances()
        instances = []
        
        # 인스턴스 정보 처리
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                # 인스턴스 데이터 수집 및 처리
                # ...
                
        return {'instances': instances}
    except Exception as e:
        return {'error': str(e)}
```

### 5. boto3 클라이언트 생성

`create_boto3_client` 함수는 인증 유형에 따라 다르게 동작합니다:

```python
def create_boto3_client(service_name, region, auth_type='access_key', **auth_params):
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
            region=region
        )
        
        # 임시 자격 증명으로 클라이언트 설정
        client_kwargs['aws_access_key_id'] = temp_credentials['access_key']
        client_kwargs['aws_secret_access_key'] = temp_credentials['secret_key']
        client_kwargs['aws_session_token'] = temp_credentials['session_token']
    
    # boto3 클라이언트 생성 및 반환
    return boto3.client(service_name, **client_kwargs)
```

### 6. 역할 수임 (ARN 인증 방식인 경우)

ARN 인증 방식인 경우 `assume_role` 함수를 통해 임시 자격 증명을 생성합니다:

```python
def assume_role(role_arn, region, session_name="AssumedRoleSession", duration_seconds=3600):
    # STS 클라이언트 생성
    sts_client = boto3.client('sts', region_name=region)
    
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
```

## 인증 방식 비교

| 인증 방식 | 세션에 저장되는 정보 | AWS 서비스 호출 방식 |
|----------|-------------------|-------------------|
| 액세스 키 | aws_access_key, aws_secret_key | 저장된 액세스 키와 시크릿 키를 직접 사용 |
| 역할 ARN | role_arn | STS를 통해 임시 자격 증명 생성 후 사용 |

## 결론

- **액세스 키 인증 방식**은 사용자가 제공한 액세스 키와 시크릿 키를 직접 사용하여 AWS 서비스에 접근합니다.
- **역할 ARN 인증 방식**은 사용자가 제공한 역할 ARN을 사용하여 임시 자격 증명을 생성한 후 AWS 서비스에 접근합니다.
- 두 방식 모두 최종적으로는 `create_boto3_client` 함수를 통해 boto3 클라이언트를 생성하여 AWS 서비스에 접근합니다.