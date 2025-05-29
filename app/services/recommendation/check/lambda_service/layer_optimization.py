import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

def check_layer_optimization(function: Dict, collection_id: str = None) -> Optional[Dict]:
    """
    Lambda 함수의 계층(Layer) 사용을 분석하고 최적화 권장사항을 제공합니다.
    
    계층을 효율적으로 사용하면 코드 크기를 줄이고, 배포 시간을 단축하며,
    여러 함수 간에 공통 코드를 공유할 수 있습니다.
    
    Args:
        function: Lambda 함수 정보가 포함된 딕셔너리
        collection_id: 수집 ID (로깅용)
        
    Returns:
        권장사항 딕셔너리 또는 권장사항이 없는 경우 None
    """
    log_prefix = f"[{collection_id}] " if collection_id else ""
    function_name = function.get('FunctionName', 'unknown')
    
    # 계층 정보 확인
    layers = function.get('Layers', [])
    code_size = function.get('CodeSize', 0)
    
    # 계층을 사용하지 않고 코드 크기가 큰 경우
    if not layers and code_size > 3 * 1024 * 1024:  # 3MB 이상
        logger.info(f"{log_prefix}Function {function_name} has large code size ({code_size/1024/1024:.2f}MB) but no layers")
        
        return {
            'ResourceId': function.get('FunctionArn', function_name),
            'ResourceType': 'AWS::Lambda::Function',
            'ResourceName': function_name,
            'Region': function.get('Region', 'unknown'),
            'Category': 'Performance',
            'Description': 'Lambda 계층(Layer) 사용 권장',
            'Impact': 'MEDIUM',
            'Recommendation': {
                'Text': '코드 크기가 큰 Lambda 함수에 계층(Layer)을 사용하여 배포 패키지 크기를 줄이세요.',
                'Details': '''
## Lambda 계층(Layer) 사용 권장

### 문제점
이 Lambda 함수의 배포 패키지 크기가 크지만(약 {:.2f}MB) 계층(Layer)을 사용하지 않고 있습니다. 
큰 배포 패키지는 콜드 스타트 시간을 증가시키고 배포 시간을 늘릴 수 있습니다.

### 권장 조치
1. 함수 코드에서 종속성과 라이브러리를 식별하세요.
2. 공통 종속성을 Lambda 계층으로 분리하세요.
3. 함수 코드에서는 비즈니스 로직만 유지하고 계층을 참조하도록 수정하세요.
4. 여러 함수에서 동일한 종속성을 사용하는 경우, 계층을 공유하여 관리 효율성을 높이세요.

### 이점
- 배포 패키지 크기 감소
- 콜드 스타트 시간 개선
- 코드 재사용성 향상
- 종속성 관리 간소화

### 구현 예시
```bash
# 계층 생성
zip -r layer.zip python/
aws lambda publish-layer-version \\
  --layer-name my-dependencies \\
  --description "Common dependencies for Lambda functions" \\
  --zip-file fileb://layer.zip \\
  --compatible-runtimes python3.9

# 함수에 계층 연결
aws lambda update-function-configuration \\
  --function-name {function_name} \\
  --layers arn:aws:lambda:${{AWS_REGION}}:${{ACCOUNT_ID}}:layer:my-dependencies:1
```

### 모범 사례
- 계층은 변경이 적은 종속성에 사용하세요.
- 계층 버전을 명시적으로 관리하여 예기치 않은 변경을 방지하세요.
- 계층 크기도 최적화하여 필요한 라이브러리만 포함하세요.
'''.format(code_size/1024/1024),
                'Link': 'https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html'
            }
        }
    
    # 계층을 과도하게 많이 사용하는 경우
    elif len(layers) > 5:
        logger.info(f"{log_prefix}Function {function_name} uses too many layers ({len(layers)})")
        
        return {
            'ResourceId': function.get('FunctionArn', function_name),
            'ResourceType': 'AWS::Lambda::Function',
            'ResourceName': function_name,
            'Region': function.get('Region', 'unknown'),
            'Category': 'Performance',
            'Description': 'Lambda 계층(Layer) 최적화 권장',
            'Impact': 'LOW',
            'Recommendation': {
                'Text': '너무 많은 계층(Layer)을 사용하고 있습니다. 계층을 통합하여 성능을 개선하세요.',
                'Details': '''
## Lambda 계층(Layer) 최적화 권장

### 문제점
이 Lambda 함수는 {0}개의 계층을 사용하고 있습니다. 너무 많은 계층을 사용하면 함수 초기화 시간이 증가하고 
관리가 복잡해질 수 있습니다.

### 권장 조치
1. 현재 사용 중인 계층의 내용을 검토하세요.
2. 관련 종속성을 가진 계층들을 통합하세요.
3. 더 이상 사용하지 않는 종속성이 있는 계층은 제거하세요.
4. 가능하면 계층 수를 5개 이하로 유지하세요.

### 이점
- 함수 초기화 시간 단축
- 계층 관리 간소화
- 종속성 충돌 가능성 감소

### 현재 사용 중인 계층
{1}

### 모범 사례
- 관련 종속성을 논리적으로 그룹화하여 계층을 구성하세요.
- 계층 버전을 명시적으로 관리하여 예기치 않은 변경을 방지하세요.
- 정기적으로 계층 사용을 검토하고 최적화하세요.
'''.format(len(layers), '\n'.join([f"- {layer.get('Arn', 'Unknown ARN')}" for layer in layers])),
                'Link': 'https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html'
            }
        }
    
    return None