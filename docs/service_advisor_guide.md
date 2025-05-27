# 서비스 어드바이저 확장 가이드

## 새로운 검사 항목 추가하기

서비스 어드바이저에 새로운 검사 항목을 추가하는 방법을 설명합니다.

### 1. 검사 모듈 생성

먼저 해당 서비스의 `checks` 디렉토리에 새로운 검사 모듈을 생성합니다.

```
app/services/service_advisor/{서비스명}/checks/{검사_모듈명}.py
```

예시 (EC2 서비스에 새로운 검사 항목 추가):
```python
# app/services/service_advisor/ec2/checks/new_check.py
import boto3
from typing import Dict, List, Any

def run() -> Dict[str, Any]:
    """
    새로운 검사 항목에 대한 설명을 작성합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # AWS 리소스 정보 수집
        ec2 = boto3.client('ec2')
        
        # 검사 로직 구현
        # ...
        
        # 결과 생성
        if problem_found:
            return {
                'status': 'warning',  # 'ok', 'warning', 'error', 'info' 중 하나
                'data': {
                    # 검사 결과 데이터
                },
                'recommendations': [
                    # 권장 사항 목록
                ],
                'message': '검사 결과 메시지'
            }
        else:
            return {
                'status': 'ok',
                'data': {},
                'recommendations': [],
                'message': '문제가 발견되지 않았습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'검사 중 오류가 발생했습니다: {str(e)}'
        }
```

### 2. 서비스 어드바이저에 검사 항목 등록

해당 서비스의 어드바이저 클래스에 새로운 검사 항목을 등록합니다.

1. 먼저 검사 모듈을 import 합니다:

```python
# app/services/service_advisor/ec2/ec2_advisor.py
from app.services.service_advisor.ec2.checks import (
    security_group_check,
    instance_type_check,
    # ... 기존 import 항목들
    new_check  # 새로운 검사 모듈 import
)
```

2. `_register_checks` 메서드에 새로운 검사 항목을 등록합니다:

```python
def _register_checks(self) -> None:
    """EC2 서비스에 대한 검사 항목을 등록합니다."""
    
    # 기존 검사 항목들...
    
    # 새로운 검사 항목 등록
    self.register_check(
        check_id='ec2-new-check',  # 고유한 ID
        name='새로운 검사 항목',  # 사용자에게 표시될 이름
        description='새로운 검사 항목에 대한 설명입니다.',  # 설명
        function=new_check.run,  # 검사 실행 함수
        category='성능',  # 카테고리 (보안, 비용 최적화, 성능, 거버넌스 등)
        severity='medium'  # 심각도 (high, medium, low)
    )
```

### 3. 검사 결과 표시 로직 추가 (선택 사항)

검사 결과가 특별한 형식으로 표시되어야 하는 경우, 해당 서비스의 템플릿 파일에 결과 표시 로직을 추가합니다.

```javascript
// templates/service_advisor/ec2.html의 JavaScript 부분

// 새로운 검사 항목의 결과 테이블 생성 함수
function createNewCheckTable(data) {
    if (!data || !data.some_property) return '';
    
    return `
        <div class="check-result-data">
            <h4>검사 결과 제목</h4>
            <div class="table-responsive">
                <table class="awsui-table">
                    <thead>
                        <tr>
                            <th>항목 1</th>
                            <th>항목 2</th>
                            <!-- 필요한 열 추가 -->
                        </tr>
                    </thead>
                    <tbody>
                        ${data.items.map(item => `
                            <tr>
                                <td>${item.property1}</td>
                                <td>${item.property2}</td>
                                <!-- 필요한 셀 추가 -->
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// 기존 코드에 새로운 검사 항목 처리 추가
if (data.id === 'ec2-new-check' && data.data.some_property) {
    resultHtml += createNewCheckTable(data.data);
}
```

### 4. 새로운 서비스 추가하기

완전히 새로운 서비스를 추가하려면 다음 단계를 따릅니다:

1. 서비스 디렉토리 구조 생성:
```
app/services/service_advisor/{새로운_서비스명}/
app/services/service_advisor/{새로운_서비스명}/checks/
```

2. 서비스 어드바이저 클래스 생성:
```python
# app/services/service_advisor/{새로운_서비스명}/{새로운_서비스명}_advisor.py
from app.services.service_advisor.base_advisor import BaseAdvisor

class NewServiceAdvisor(BaseAdvisor):
    """
    새로운 서비스에 대한 어드바이저 클래스입니다.
    """
    
    def _register_checks(self) -> None:
        """새로운 서비스에 대한 검사 항목을 등록합니다."""
        # 검사 항목 등록
        pass
```

3. 팩토리 클래스에 새로운 서비스 등록:
```python
# app/services/service_advisor/advisor_factory.py
from app.services.service_advisor.ec2.ec2_advisor import EC2Advisor
from app.services.service_advisor.{새로운_서비스명}.{새로운_서비스명}_advisor import NewServiceAdvisor

class ServiceAdvisorFactory:
    def __init__(self):
        """팩토리 초기화"""
        self.advisors = {
            'ec2': EC2Advisor,
            '새로운_서비스_id': NewServiceAdvisor  # 새로운 서비스 등록
        }
    
    # ... 기존 코드 ...
    
    def get_available_services(self) -> List[Dict[str, Any]]:
        """사용 가능한 모든 서비스 목록을 반환합니다."""
        services = [
            {
                'id': 'ec2',
                'name': 'EC2',
                'description': 'Amazon Elastic Compute Cloud',
                'icon': 'fa-server'
            },
            {
                'id': '새로운_서비스_id',
                'name': '새로운 서비스 이름',
                'description': '새로운 서비스 설명',
                'icon': 'fa-icon-name'  # Font Awesome 아이콘 이름
            }
        ]
        return services
```

4. 서비스 템플릿 파일 생성:
```html
<!-- templates/service_advisor/{새로운_서비스명}.html -->
{% extends "base.html" %}

{% block title %}새로운 서비스 어드바이저 - AWS 콘솔 체크{% endblock %}

<!-- 나머지 템플릿 코드 -->
```

### 5. 테스트

새로운 검사 항목이나 서비스를 추가한 후에는 다음을 확인합니다:

1. 서비스 어드바이저 페이지에서 새로운 검사 항목이 표시되는지 확인
2. 검사 실행 시 예상대로 작동하는지 확인
3. 결과가 올바르게 표시되는지 확인

## 검사 결과 형식

모든 검사 항목은 다음 형식의 결과를 반환해야 합니다:

```python
{
    'status': str,  # 'ok', 'warning', 'error', 'info' 중 하나
    'data': dict,   # 검사 결과 데이터 (테이블 등에 표시될 정보)
    'recommendations': List[str],  # 권장 사항 목록
    'message': str  # 검사 결과 요약 메시지
}
```

## 카테고리 및 심각도

### 카테고리
- `보안`: 보안 관련 검사 항목
- `비용 최적화`: 비용 절감 관련 검사 항목
- `성능`: 성능 최적화 관련 검사 항목
- `거버넌스`: 규정 준수 및 관리 관련 검사 항목
- `일반`: 기타 검사 항목

### 심각도
- `high`: 높은 심각도 (빨리 해결해야 하는 문제)
- `medium`: 중간 심각도 (해결을 권장하는 문제)
- `low`: 낮은 심각도 (선택적으로 해결할 수 있는 문제)