import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def check_code_signing(function: Dict, collection_id: str = None) -> Optional[Dict]:
    """
    Lambda 함수의 코드 서명 구성을 확인합니다.
    
    코드 서명은 배포된 코드의 무결성과 신뢰성을 보장하는 보안 기능입니다.
    승인된 개발자의 코드만 Lambda 함수에 배포되도록 하여 보안을 강화합니다.
    
    Args:
        function: Lambda 함수 정보가 포함된 딕셔너리
        collection_id: 수집 ID (로깅용)
        
    Returns:
        권장사항 딕셔너리 또는 권장사항이 없는 경우 None
    """
    log_prefix = f"[{collection_id}] " if collection_id else ""
    function_name = function.get('FunctionName', 'unknown')
    
    # 코드 서명 구성 확인
    code_signing_config = function.get('CodeSigningConfig', {})
    
    # 코드 서명이 구성되지 않은 경우
    if not code_signing_config:
        logger.info(f"{log_prefix}Function {function_name} has no code signing configuration")
        
        # 프로덕션 환경인지 확인 (태그 기반)
        tags = function.get('Tags', {})
        is_production = False
        
        for key, value in tags.items():
            if (key.lower() in ['environment', 'env'] and 
                value.lower() in ['prod', 'production']):
                is_production = True
                break
        
        # 프로덕션 환경이거나 중요한 함수인 경우에만 권장
        if is_production or function_name.lower().startswith(('prod-', 'production-')):
            return {
                'ResourceId': function.get('FunctionArn', function_name),
                'ResourceType': 'AWS::Lambda::Function',
                'ResourceName': function_name,
                'Region': function.get('Region', 'unknown'),
                'Category': 'Security',
                'Description': 'Lambda 함수 코드 서명 구성 권장',
                'Impact': 'MEDIUM',
                'Recommendation': {
                    'Text': '프로덕션 Lambda 함수에 코드 서명을 구성하여 코드 무결성을 보장하세요.',
                    'Details': '''
## Lambda 함수 코드 서명 구성 권장

### 문제점
이 프로덕션 Lambda 함수에 코드 서명이 구성되어 있지 않습니다. 
코드 서명이 없으면 승인되지 않은 코드가 함수에 배포될 위험이 있습니다.

### 권장 조치
1. AWS Signer를 사용하여 서명 프로필을 생성하세요.
2. Lambda 코드 서명 구성을 생성하고 서명 프로필을 연결하세요.
3. Lambda 함수를 코드 서명 구성과 연결하세요.
4. 코드 서명 검증 정책을 설정하세요(경고 또는 적용).

### 이점
- 승인된 코드만 Lambda 함수에 배포되도록 보장
- 코드 무결성 및 신뢰성 향상
- 악의적인 코드 배포 위험 감소
- 규정 준수 요구 사항 충족

### 구현 예시
```bash
# 서명 프로필 생성
aws signer put-signing-profile \\
  --profile-name LambdaSigningProfile \\
  --signing-material certificateArn=arn:aws:acm:region:account-id:certificate/certificate-id \\
  --platform-id "AWSLambda-SHA384-ECDSA"

# 코드 서명 구성 생성
aws lambda create-code-signing-config \\
  --description "Code signing for production Lambda functions" \\
  --allowed-publishers hash-algorithms=SHA384 signing-profile-version-arns=arn:aws:signer:region:account-id:signing-profile/LambdaSigningProfile \\
  --code-signing-policies untrusted-artifact-on-deployment=Enforce

# Lambda 함수와 코드 서명 구성 연결
aws lambda update-function-code-signing-config \\
  --function-name {function_name} \\
  --code-signing-config-arn arn:aws:lambda:region:account-id:code-signing-config:uuid
```

### 모범 사례
- 프로덕션 환경의 모든 Lambda 함수에 코드 서명을 적용하세요.
- 코드 서명 검증 정책을 '적용(Enforce)'으로 설정하여 서명되지 않은 코드 배포를 방지하세요.
- 서명 인증서와 프로필을 안전하게 관리하세요.
- CI/CD 파이프라인에 코드 서명 단계를 통합하세요.
''',
                    'Link': 'https://docs.aws.amazon.com/lambda/latest/dg/configuration-codesigning.html'
                }
            }
    
    return None