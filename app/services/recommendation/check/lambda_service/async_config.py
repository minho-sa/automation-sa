import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def check_async_config(function: Dict, collection_id: str = None) -> Optional[Dict]:
    """
    Lambda 함수의 비동기 호출 구성을 확인합니다.
    
    비동기 호출에 대한 적절한 구성은 오류 처리, 재시도 및 대상 구성을 통해
    함수의 안정성과 내결함성을 향상시킵니다.
    
    Args:
        function: Lambda 함수 정보가 포함된 딕셔너리
        collection_id: 수집 ID (로깅용)
        
    Returns:
        권장사항 딕셔너리 또는 권장사항이 없는 경우 None
    """
    log_prefix = f"[{collection_id}] " if collection_id else ""
    function_name = function.get('FunctionName', 'unknown')
    
    # 비동기 호출 구성 확인
    async_config = function.get('AsyncConfig', {})
    event_sources = function.get('EventSourceMappings', [])
    
    # 비동기 이벤트 소스 확인 (예: S3, SNS, EventBridge 등)
    has_async_triggers = False
    for source in event_sources:
        source_type = source.get('EventSourceArn', '').split(':')[2] if source.get('EventSourceArn') else ''
        if source_type in ['s3', 'sns', 'events', 'eventbridge']:
            has_async_triggers = True
            break
    
    # 비동기 트리거가 있지만 비동기 구성이 없는 경우
    if has_async_triggers and not async_config:
        logger.info(f"{log_prefix}Function {function_name} has async triggers but no async configuration")
        
        return {
            'ResourceId': function.get('FunctionArn', function_name),
            'ResourceType': 'AWS::Lambda::Function',
            'ResourceName': function_name,
            'Region': function.get('Region', 'unknown'),
            'Category': 'Reliability',
            'Description': 'Lambda 비동기 호출 구성 권장',
            'Impact': 'MEDIUM',
            'Recommendation': {
                'Text': '비동기적으로 호출되는 Lambda 함수에 적절한 비동기 구성을 설정하세요.',
                'Details': '''
## Lambda 비동기 호출 구성 권장

### 문제점
이 Lambda 함수는 비동기 이벤트 소스(S3, SNS, EventBridge 등)에 의해 트리거되지만, 
비동기 호출에 대한 구성이 설정되어 있지 않습니다. 이로 인해 오류 처리, 재시도 및 이벤트 라우팅이 
제대로 관리되지 않을 수 있습니다.

### 권장 조치
1. 비동기 호출에 대한 최대 재시도 횟수를 설정하세요.
2. 실패한 이벤트를 처리하기 위한 데드 레터 큐(DLQ)를 구성하세요.
3. 성공 및 실패 이벤트를 다른 AWS 서비스로 라우팅하기 위한 대상 구성을 고려하세요.
4. 필요에 따라 이벤트 수명 주기 관리를 위한 최대 이벤트 기간을 설정하세요.

### 이점
- 실패한 이벤트의 가시성 향상
- 오류 처리 및 복구 메커니즘 개선
- 이벤트 처리의 안정성 향상
- 이벤트 기반 아키텍처의 내결함성 강화

### 구현 예시
```bash
# AWS CLI를 사용한 비동기 구성 설정
aws lambda put-function-event-invoke-config \\
  --function-name {function_name} \\
  --maximum-retry-attempts 2 \\
  --maximum-event-age-in-seconds 3600 \\
  --destination-config '{{"OnSuccess": {{"Destination": "arn:aws:sqs:region:account-id:success-queue"}}, "OnFailure": {{"Destination": "arn:aws:sqs:region:account-id:failure-queue"}}}}'
```

### 모범 사례
- 최대 재시도 횟수는 애플리케이션 요구 사항에 따라 설정하세요(일반적으로 1-2회).
- 데드 레터 큐(SQS) 또는 실패 대상을 항상 구성하여 실패한 이벤트를 캡처하세요.
- 중요한 이벤트의 경우 성공 대상을 구성하여 이벤트 처리 흐름을 추적하세요.
- CloudWatch 경보를 설정하여 실패한 비동기 호출을 모니터링하세요.
''',
                'Link': 'https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html'
            }
        }
    
    # 비동기 구성이 있지만 DLQ나 대상이 구성되지 않은 경우
    elif has_async_triggers and async_config:
        has_dlq = False
        has_destinations = False
        
        if async_config.get('DestinationConfig'):
            dest_config = async_config.get('DestinationConfig', {})
            if dest_config.get('OnFailure', {}).get('Destination'):
                has_dlq = True
            if dest_config.get('OnSuccess', {}).get('Destination'):
                has_destinations = True
        
        if not has_dlq:
            logger.info(f"{log_prefix}Function {function_name} has async config but no DLQ or failure destination")
            
            return {
                'ResourceId': function.get('FunctionArn', function_name),
                'ResourceType': 'AWS::Lambda::Function',
                'ResourceName': function_name,
                'Region': function.get('Region', 'unknown'),
                'Category': 'Reliability',
                'Description': 'Lambda 비동기 호출 실패 처리 구성 권장',
                'Impact': 'MEDIUM',
                'Recommendation': {
                    'Text': '비동기 Lambda 함수에 실패 처리를 위한 데드 레터 큐(DLQ) 또는 실패 대상을 구성하세요.',
                    'Details': '''
## Lambda 비동기 호출 실패 처리 구성 권장

### 문제점
이 Lambda 함수는 비동기적으로 호출되지만, 실패한 이벤트를 처리하기 위한 
데드 레터 큐(DLQ) 또는 실패 대상이 구성되어 있지 않습니다. 
이로 인해 실패한 이벤트가 손실될 수 있으며 문제 해결이 어려워질 수 있습니다.

### 권장 조치
1. SQS 큐를 생성하여 데드 레터 큐로 사용하거나 다른 AWS 서비스(SQS, SNS, EventBridge 등)를 실패 대상으로 구성하세요.
2. Lambda 함수의 비동기 호출 구성에 실패 대상을 추가하세요.
3. 실패한 이벤트를 처리하기 위한 프로세스를 구현하세요.
4. CloudWatch 경보를 설정하여 DLQ 또는 실패 대상으로 라우팅된 이벤트를 모니터링하세요.

### 이점
- 실패한 이벤트의 손실 방지
- 문제 해결 및 디버깅 용이성 향상
- 이벤트 처리의 안정성 향상
- 장애 복구 메커니즘 개선

### 구현 예시
```bash
# SQS 데드 레터 큐 생성
aws sqs create-queue --queue-name {function_name}-dlq

# 비동기 구성에 실패 대상 추가
aws lambda put-function-event-invoke-config \\
  --function-name {function_name} \\
  --maximum-retry-attempts 2 \\
  --destination-config '{{"OnFailure": {{"Destination": "arn:aws:sqs:region:account-id:{function_name}-dlq"}}}}'
```

### 모범 사례
- 실패한 이벤트를 처리하기 위한 자동화된 프로세스를 구현하세요.
- DLQ에 보존 정책을 설정하여 이벤트가 너무 오래 유지되지 않도록 하세요.
- 정기적으로 DLQ를 모니터링하고 경고를 설정하세요.
- 실패 원인을 분석하고 근본 원인을 해결하기 위한 프로세스를 수립하세요.
''',
                    'Link': 'https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html#invocation-async-destinations'
                }
            }
    
    return None