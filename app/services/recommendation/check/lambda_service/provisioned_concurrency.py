import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def check_provisioned_concurrency(function: Dict, collection_id: str = None) -> Optional[Dict]:
    """
    Lambda 함수의 프로비저닝된 동시성 설정을 확인합니다.
    
    프로비저닝된 동시성은 콜드 스타트 지연 시간을 줄이는 데 도움이 됩니다.
    특히 지연 시간에 민감한 애플리케이션이나 트래픽이 예측 가능한 워크로드에 유용합니다.
    
    Args:
        function: Lambda 함수 정보가 포함된 딕셔너리
        collection_id: 수집 ID (로깅용)
        
    Returns:
        권장사항 딕셔너리 또는 권장사항이 없는 경우 None
    """
    log_prefix = f"[{collection_id}] " if collection_id else ""
    function_name = function.get('FunctionName', 'unknown')
    
    # 프로비저닝된 동시성 설정 확인
    provisioned_concurrency = function.get('ProvisionedConcurrencyConfigs', [])
    
    # 함수 호출 패턴 분석 (이 예제에서는 호출 빈도가 높다고 가정)
    invocation_frequency = function.get('InvocationFrequency', {})
    avg_invocations_per_hour = invocation_frequency.get('AvgInvocationsPerHour', 0)
    max_concurrent_executions = invocation_frequency.get('MaxConcurrentExecutions', 0)
    
    # 호출 빈도가 높고 프로비저닝된 동시성이 설정되지 않은 경우
    if (avg_invocations_per_hour > 100 or max_concurrent_executions > 10) and not provisioned_concurrency:
        logger.info(f"{log_prefix}Function {function_name} has high invocation rate but no provisioned concurrency")
        
        return {
            'ResourceId': function.get('FunctionArn', function_name),
            'ResourceType': 'AWS::Lambda::Function',
            'ResourceName': function_name,
            'Region': function.get('Region', 'unknown'),
            'Category': 'Performance',
            'Description': '프로비저닝된 동시성 설정 권장',
            'Impact': 'MEDIUM',
            'Recommendation': {
                'Text': '지연 시간에 민감한 애플리케이션을 위해 프로비저닝된 동시성 설정을 고려하세요.',
                'Details': '''
## 프로비저닝된 동시성 설정 권장

### 문제점
이 Lambda 함수는 높은 호출 빈도를 보이지만 프로비저닝된 동시성이 설정되어 있지 않습니다. 
이로 인해 콜드 스타트 지연 시간이 발생할 수 있으며, 특히 트래픽이 급증하는 시점에 성능 저하가 발생할 수 있습니다.

### 권장 조치
1. 함수의 호출 패턴을 분석하여 적절한 프로비저닝된 동시성 값을 결정하세요.
2. AWS Management Console, AWS CLI 또는 AWS SDK를 사용하여 프로비저닝된 동시성을 구성하세요.
3. 비용 최적화를 위해 Application Auto Scaling을 사용하여 프로비저닝된 동시성을 자동으로 조정하는 것을 고려하세요.

### 이점
- 콜드 스타트 지연 시간 감소
- 일관된 성능 제공
- 트래픽 급증 시 안정적인 응답 시간 유지

### 구현 예시
```bash
# AWS CLI를 사용한 프로비저닝된 동시성 설정
aws lambda put-provisioned-concurrency-config \\
  --function-name ${function_name} \\
  --qualifier PROD \\
  --provisioned-concurrent-executions 10

# Auto Scaling 설정
aws application-autoscaling register-scalable-target \\
  --service-namespace lambda \\
  --resource-id function:${function_name}:PROD \\
  --scalable-dimension lambda:function:ProvisionedConcurrency \\
  --min-capacity 5 \\
  --max-capacity 50
```

### 주의사항
프로비저닝된 동시성은 추가 비용이 발생하므로, 비용과 성능 사이의 균형을 고려하여 설정하세요.
''',
                'Link': 'https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html'
            }
        }
    
    return None