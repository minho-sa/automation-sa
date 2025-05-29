import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def check_log_retention(function: Dict, collection_id: str = None) -> Optional[Dict]:
    """
    Lambda 함수의 CloudWatch Logs 로그 그룹 보존 기간 설정을 확인합니다.
    
    적절한 로그 보존 기간을 설정하면 비용을 최적화하고 규정 준수 요구 사항을 충족할 수 있습니다.
    기본적으로 CloudWatch Logs 로그 그룹은 만료 기간 없이 로그를 무기한 보존합니다.
    
    Args:
        function: Lambda 함수 정보가 포함된 딕셔너리
        collection_id: 수집 ID (로깅용)
        
    Returns:
        권장사항 딕셔너리 또는 권장사항이 없는 경우 None
    """
    log_prefix = f"[{collection_id}] " if collection_id else ""
    function_name = function.get('FunctionName', 'unknown')
    
    # 로그 그룹 정보 확인
    log_group = function.get('LogGroup', {})
    retention_in_days = log_group.get('RetentionInDays')
    
    # 로그 보존 기간이 설정되지 않은 경우
    if retention_in_days is None:
        logger.info(f"{log_prefix}Function {function_name} has no log retention period set")
        
        return {
            'ResourceId': function.get('FunctionArn', function_name),
            'ResourceType': 'AWS::Lambda::Function',
            'ResourceName': function_name,
            'Region': function.get('Region', 'unknown'),
            'Category': 'Cost',
            'Description': 'CloudWatch Logs 로그 보존 기간 설정 권장',
            'Impact': 'MEDIUM',
            'Recommendation': {
                'Text': 'Lambda 함수의 CloudWatch Logs 로그 그룹에 적절한 보존 기간을 설정하세요.',
                'Details': '''
## CloudWatch Logs 로그 보존 기간 설정 권장

### 문제점
이 Lambda 함수의 CloudWatch Logs 로그 그룹에 보존 기간이 설정되어 있지 않습니다. 
기본적으로 CloudWatch Logs는 로그를 무기한 보존하므로, 시간이 지남에 따라 스토리지 비용이 증가할 수 있습니다.

### 권장 조치
1. 비즈니스 요구 사항, 규정 준수 요구 사항 및 비용 고려 사항에 따라 적절한 로그 보존 기간을 결정하세요.
2. AWS Management Console, AWS CLI 또는 AWS SDK를 사용하여 로그 그룹의 보존 기간을 설정하세요.
3. 일반적으로 운영 로그는 30일, 규정 준수 관련 로그는 1년 이상의 보존 기간을 고려하세요.

### 이점
- CloudWatch Logs 스토리지 비용 절감
- 로그 관리 간소화
- 규정 준수 요구 사항 충족

### 구현 예시
```bash
# AWS CLI를 사용한 로그 보존 기간 설정
aws logs put-retention-policy \\
  --log-group-name /aws/lambda/{function_name} \\
  --retention-in-days 30
```

### 일반적인 보존 기간 옵션
- 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653일

### 모범 사례
- 개발 환경에서는 짧은 보존 기간(예: 7-14일)을 설정하세요.
- 프로덕션 환경에서는 문제 해결을 위해 최소 30일의 보존 기간을 고려하세요.
- 중요한 감사 로그는 규정 준수 요구 사항에 따라 더 긴 보존 기간을 설정하세요.
- 로그 데이터를 장기 보관해야 하는 경우, S3로 내보내는 것을 고려하세요.
''',
                'Link': 'https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html'
            }
        }
    
    # 로그 보존 기간이 너무 길게 설정된 경우 (예: 1년 이상)
    elif retention_in_days > 365:
        logger.info(f"{log_prefix}Function {function_name} has very long log retention period: {retention_in_days} days")
        
        return {
            'ResourceId': function.get('FunctionArn', function_name),
            'ResourceType': 'AWS::Lambda::Function',
            'ResourceName': function_name,
            'Region': function.get('Region', 'unknown'),
            'Category': 'Cost',
            'Description': 'CloudWatch Logs 로그 보존 기간 최적화 권장',
            'Impact': 'LOW',
            'Recommendation': {
                'Text': 'Lambda 함수의 CloudWatch Logs 로그 보존 기간이 매우 깁니다. 비용 최적화를 위해 검토하세요.',
                'Details': f'''
## CloudWatch Logs 로그 보존 기간 최적화 권장

### 문제점
이 Lambda 함수의 CloudWatch Logs 로그 그룹에 {retention_in_days}일의 매우 긴 보존 기간이 설정되어 있습니다. 
긴 보존 기간은 CloudWatch Logs 스토리지 비용을 증가시킬 수 있습니다.

### 권장 조치
1. 현재 설정된 {retention_in_days}일의 보존 기간이 비즈니스 요구 사항이나 규정 준수 요구 사항에 필요한지 검토하세요.
2. 장기 보관이 필요한 경우, CloudWatch Logs에서 S3로 로그를 내보내는 것을 고려하세요.
3. 필요에 따라 보존 기간을 조정하세요(예: 운영 로그는 30-90일).

### 이점
- CloudWatch Logs 스토리지 비용 절감
- 효율적인 로그 관리

### 구현 예시
```bash
# AWS CLI를 사용한 로그 보존 기간 조정
aws logs put-retention-policy \\
  --log-group-name /aws/lambda/{function_name} \\
  --retention-in-days 90

# CloudWatch Logs에서 S3로 로그 내보내기 설정
aws logs create-export-task \\
  --task-name "ExportTask" \\
  --log-group-name /aws/lambda/{function_name} \\
  --from 1234567890000 \\
  --to 1234567890000 \\
  --destination my-log-bucket \\
  --destination-prefix my-log-exports
```

### 모범 사례
- 로그 데이터의 중요도와 사용 패턴에 따라 보존 기간을 설정하세요.
- 장기 보관이 필요한 로그는 S3로 내보내고 S3 수명 주기 정책을 사용하여 비용을 최적화하세요.
- 정기적으로 로그 사용 패턴을 검토하고 보존 정책을 조정하세요.
''',
                'Link': 'https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatchLogsConcepts.html'
            }
        }
    
    return None