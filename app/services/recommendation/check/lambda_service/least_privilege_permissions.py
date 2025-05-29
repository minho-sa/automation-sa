import logging
import json
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

def check_least_privilege_permissions(function: Dict, collection_id: str = None) -> Optional[Dict]:
    """
    Lambda 함수의 실행 역할(IAM Role)이 최소 권한 원칙을 따르는지 확인합니다.
    
    최소 권한 원칙은 보안 모범 사례로, 함수가 작업을 수행하는 데 필요한 최소한의 권한만 부여해야 합니다.
    과도한 권한은 보안 위험을 증가시킬 수 있습니다.
    
    Args:
        function: Lambda 함수 정보가 포함된 딕셔너리
        collection_id: 수집 ID (로깅용)
        
    Returns:
        권장사항 딕셔너리 또는 권장사항이 없는 경우 None
    """
    log_prefix = f"[{collection_id}] " if collection_id else ""
    function_name = function.get('FunctionName', 'unknown')
    
    # 실행 역할 정보 확인
    role = function.get('Role', {})
    role_name = role.get('RoleName', '')
    role_policies = role.get('AttachedPolicies', [])
    inline_policies = role.get('InlinePolicies', [])
    
    # 관리형 정책 확인 (특히 과도하게 권한이 넓은 정책)
    risky_policies = []
    for policy in role_policies:
        policy_name = policy.get('PolicyName', '')
        if any(p in policy_name for p in ['AdministratorAccess', 'FullAccess', 'PowerUserAccess']):
            risky_policies.append(policy_name)
    
    # 인라인 정책에서 과도한 권한 확인
    for policy in inline_policies:
        policy_doc = policy.get('PolicyDocument', {})
        if isinstance(policy_doc, str):
            try:
                policy_doc = json.loads(policy_doc)
            except:
                continue
                
        statements = policy_doc.get('Statement', [])
        for statement in statements:
            effect = statement.get('Effect')
            action = statement.get('Action')
            resource = statement.get('Resource')
            
            # "Effect": "Allow", "Action": "*", "Resource": "*" 패턴 확인
            if (effect == 'Allow' and 
                (action == '*' or (isinstance(action, list) and '*' in action)) and
                (resource == '*' or (isinstance(resource, list) and '*' in resource))):
                risky_policies.append(f"인라인 정책: {policy.get('PolicyName', 'Unknown')}")
    
    # 위험한 정책이 발견된 경우
    if risky_policies:
        logger.info(f"{log_prefix}Function {function_name} has overly permissive policies: {', '.join(risky_policies)}")
        
        return {
            'ResourceId': function.get('FunctionArn', function_name),
            'ResourceType': 'AWS::Lambda::Function',
            'ResourceName': function_name,
            'Region': function.get('Region', 'unknown'),
            'Category': 'Security',
            'Description': 'Lambda 함수 실행 역할의 과도한 권한',
            'Impact': 'HIGH',
            'Recommendation': {
                'Text': '최소 권한 원칙에 따라 Lambda 함수의 실행 역할 권한을 제한하세요.',
                'Details': f'''
## Lambda 함수 실행 역할의 과도한 권한

### 문제점
이 Lambda 함수의 실행 역할({role_name})에 과도하게 넓은 권한이 부여되어 있습니다. 
다음과 같은 위험한 정책이 발견되었습니다:

{chr(10).join([f"- {policy}" for policy in risky_policies])}

과도한 권한은 보안 위험을 증가시키고, 의도하지 않은 리소스 액세스나 변경을 허용할 수 있습니다.

### 권장 조치
1. 함수가 실제로 필요로 하는 AWS 서비스와 작업을 식별하세요.
2. 최소 권한 원칙에 따라 새로운 IAM 정책을 생성하세요.
3. 광범위한 관리형 정책을 제거하고 구체적인 권한을 가진 정책으로 대체하세요.
4. AWS IAM Access Analyzer를 사용하여 실제로 사용되는 권한을 분석하세요.

### 이점
- 보안 태세 강화
- 잠재적인 보안 침해의 영향 범위 제한
- 규정 준수 요구 사항 충족

### 구현 예시
```json
{{
  "Version": "2012-10-17",
  "Statement": [
    {{
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/*"
    }},
    {{
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }}
  ]
}}
```

### 모범 사례
- 정기적으로 IAM 역할과 정책을 검토하고 불필요한 권한을 제거하세요.
- AWS CloudTrail 로그를 모니터링하여 실행 역할이 수행하는 작업을 추적하세요.
- 새로운 권한이 필요할 때마다 최소 권한 원칙을 적용하세요.
''',
                'Link': 'https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege'
            }
        }
    
    return None