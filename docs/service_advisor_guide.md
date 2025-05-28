# 서비스 어드바이저 개발 가이드

이 문서는 EC2 서비스 어드바이저를 기준으로 다른 AWS 서비스에 대한 어드바이저를 개발할 때 참고할 수 있는 가이드입니다.

## 1. 백엔드 구조

### 1.1 디렉토리 구조
```
app/services/service_advisor/
├── __init__.py
├── advisor_factory.py        # 서비스 어드바이저 팩토리
├── base_advisor.py           # 기본 어드바이저 클래스
├── check_result.py           # 결과 표준화 유틸리티
├── aws_client.py             # AWS 클라이언트 생성 유틸리티
└── [service_name]/           # 서비스별 디렉토리
    ├── __init__.py
    ├── [service_name]_advisor.py  # 서비스별 어드바이저 클래스
    └── checks/               # 서비스별 검사 항목
        ├── __init__.py
        └── [check_name].py   # 개별 검사 항목
```

### 1.2 어드바이저 클래스 구현

`BaseAdvisor` 클래스를 상속받아 서비스별 어드바이저 클래스를 구현합니다.

```python
from app.services.service_advisor.base_advisor import BaseAdvisor
from app.services.service_advisor.[service_name].checks import check_module1, check_module2

class ServiceNameAdvisor(BaseAdvisor):
    """
    서비스에 대한 어드바이저 클래스입니다.
    """
    
    def _register_checks(self) -> None:
        """서비스에 대한 검사 항목을 등록합니다."""
        
        # 검사 항목 1
        self.register_check(
            check_id='service-check-id-1',
            name='검사 항목 이름 1',
            description='검사 항목에 대한 상세 설명입니다.',
            function=check_module1.run,
            category='카테고리',  # 보안, 비용 최적화, 성능 등
            severity='high'      # high, medium, low
        )
        
        # 검사 항목 2
        self.register_check(
            check_id='service-check-id-2',
            name='검사 항목 이름 2',
            description='검사 항목에 대한 상세 설명입니다.',
            function=check_module2.run,
            category='카테고리',
            severity='medium'
        )
```

### 1.3 검사 항목 구현

각 검사 항목은 독립적인 모듈로 구현하며, `run()` 함수를 제공해야 합니다.

```python
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run() -> Dict[str, Any]:
    """
    검사를 실행하고 결과를 반환합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # AWS 클라이언트 생성
        client = create_boto3_client('service_name')
        
        # 리소스 수집
        resources = client.describe_resources()
        
        # 리소스 분석 결과
        resource_analysis = []
        
        # 리소스 분석
        for resource in resources['Resources']:
            resource_id = resource['ResourceId']
            
            # 리소스 상태 결정
            status = RESOURCE_STATUS_PASS  # 기본값은 통과
            status_text = '최적화됨'        # 상태 텍스트
            advice = '적절하게 구성되어 있습니다.'  # 권장 사항
            
            # 조건에 따라 상태 변경
            if condition_not_met(resource):
                status = RESOURCE_STATUS_FAIL
                status_text = '최적화 필요'
                advice = '리소스에 대한 구체적인 권장 사항입니다.'
            
            # 표준화된 리소스 결과 생성
            resource_result = create_resource_result(
                resource_id=resource_id,
                status=status,
                advice=advice,
                status_text=status_text,
                # 추가 필드
                field1=resource['Field1'],
                field2=resource['Field2']
            )
            
            resource_analysis.append(resource_result)
        
        # 결과 분류
        passed_resources = [r for r in resource_analysis if r['status'] == RESOURCE_STATUS_PASS]
        failed_resources = [r for r in resource_analysis if r['status'] == RESOURCE_STATUS_FAIL]
        
        # 최적화 필요 리소스 카운트
        optimization_needed_count = len(failed_resources)
        
        # 권장사항 생성
        recommendations = []
        if optimization_needed_count > 0:
            recommendations.append(f'{optimization_needed_count}개 리소스에 대한 권장 사항입니다.')
        
        # 데이터 준비
        data = {
            'resources': resource_analysis,
            'passed_resources': passed_resources,
            'failed_resources': failed_resources,
            'optimization_needed_count': optimization_needed_count,
            'total_resources_count': len(resource_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if optimization_needed_count > 0:
            message = f'{len(resource_analysis)}개 리소스 중 {optimization_needed_count}개가 최적화가 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 리소스({len(passed_resources)}개)가 적절하게 구성되어 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=['모든 리소스가 적절하게 구성되어 있습니다.']
            )
    
    except Exception as e:
        return create_error_result(f'검사 중 오류가 발생했습니다: {str(e)}')
```

### 1.4 어드바이저 팩토리 등록

새로운 서비스 어드바이저를 `ServiceAdvisorFactory` 클래스에 등록합니다.

```python
# app/services/service_advisor/advisor_factory.py
class ServiceAdvisorFactory:
    def __init__(self):
        self.service_mapping = {
            'ec2': EC2Advisor,
            'lambda': LambdaServiceAdvisor,
            'service_name': ServiceNameAdvisor,  # 새로운 서비스 추가
        }
```

## 2. 프론트엔드 구조

### 2.1 파일 구조
```
static/js/service-advisor/
├── common.js                # 공통 기능
├── main.js                  # 메인 초기화 코드
└── [service_name].js        # 서비스별 JavaScript
```

### 2.2 서비스별 JavaScript 클래스

`ServiceAdvisorCommon` 클래스를 상속받아 서비스별 JavaScript 클래스를 구현합니다.

```javascript
/**
 * 서비스 어드바이저 기능
 * 서비스 관련 검사 항목을 처리합니다.
 */
class ServiceAdvisorName extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.checkHandlers = {
      'service-check-id-1': {
        createResultHtml: this.createResultHtml1.bind(this),
        createTable: this.createTable1.bind(this)
      },
      'service-check-id-2': {
        createResultHtml: this.createResultHtml2.bind(this),
        createTable: this.createTable2.bind(this)
      }
    };
  }

  // 결과 HTML 생성
  createResultHtml1(data) {
    const checkId = 'service-check-id-1';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.resources.forEach(resource => {
      const statusText = resource.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(resource);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.resources.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const resources = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${resources.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createTable1(data.data.resources)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const resources = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createTable1(resources)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>리소스 분석 (${data.data.total_resources_count}개)</h4>
        <ul class="nav nav-tabs" id="resourceTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="resourceTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 테이블 생성
  createTable1(resources) {
    if (!resources || resources.length === 0) return '<div class="alert alert-info">표시할 리소스가 없습니다.</div>';
    
    return `
      <style>
        .resource-table th:nth-child(1) { width: 15%; }
        .resource-table th:nth-child(2) { width: 15%; }
        .resource-table th:nth-child(3) { width: 55%; }
        .resource-table th:nth-child(4) { width: 15%; }
        .resource-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table resource-table">
          <thead>
            <tr>
              <th>리소스 ID</th>
              <th>필드 1</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${resources.map(resource => {
              let statusClass = '';
              let statusIcon = '';
              
              if (resource.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (resource.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (resource.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (resource.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${resource.id || ''}</td>
                  <td>${resource.field1 || ''}</td>
                  <td>${resource.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${resource.status_text || ''}
                    </span>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }
}
```

### 2.3 HTML 템플릿

서비스별 HTML 템플릿을 작성합니다.

```html
<!-- templates/service_advisor/service_name.html -->
{% extends "base.html" %}

{% block title %}서비스 어드바이저 - AWS 콘솔 체크{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/service-advisor.css') }}">
{% endblock %}

{% block content %}
<div class="page-header">
    <div class="page-header-title">
        <h1>서비스 어드바이저</h1>
        <p>서비스에 대한 검사 항목을 확인하고 실행할 수 있습니다.</p>
    </div>
    <div class="page-header-actions">
        <a href="{{ url_for('service_advisor.service_advisor_view') }}" class="awsui-button awsui-button-normal">
            <i class="fas fa-arrow-left"></i> 서비스 목록으로 돌아가기
        </a>
    </div>
</div>

<div class="row mt-4">
    <div class="col-12">
        <div class="awsui-container">
            <h2 class="mb-4">검사 항목</h2>
            
            <div class="check-actions mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="select-all-checks">
                    <label class="form-check-label" for="select-all-checks">
                        전체 선택
                    </label>
                </div>
                <button id="run-selected-checks" class="awsui-button awsui-button-primary ml-3">
                    <i class="fas fa-play"></i> 선택한 항목 검사하기
                </button>
            </div>
            
            <div class="check-items-container">
                {% for check in checks %}
                <div class="check-item" data-check-id="{{ check.id }}">
                    <div class="check-item-header">
                        <div class="check-item-title">
                            <input type="checkbox" class="check-select" data-check-id="{{ check.id }}">
                            <h3>{{ check.name }}</h3>
                            <span class="check-item-category {{ check.category|lower }}">{{ check.category }}</span>
                            <span class="check-item-severity {{ check.severity }}">{{ check.severity }}</span>
                        </div>
                        <div class="check-item-actions">
                            <span class="last-check-date" id="last-check-date-{{ check.id }}">검사 기록 없음</span>
                            <button class="awsui-button awsui-button-primary run-check-btn" data-check-id="{{ check.id }}">
                                <i class="fas fa-play"></i> 검사하기
                            </button>
                        </div>
                    </div>
                    <div class="check-item-description">
                        {{ check.description }}
                    </div>
                    <div class="check-item-result" id="result-{{ check.id }}" style="display: none;">
                        <div class="check-result-loading">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <span>검사 중입니다...</span>
                        </div>
                        <div class="check-result-content" style="display: none;">
                            <!-- 결과는 JavaScript로 동적 생성됩니다 -->
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/service-advisor/common.js') }}"></script>
<script src="{{ url_for('static', filename='js/service-advisor/service_name.js') }}"></script>
<script src="{{ url_for('static', filename='js/service-advisor/main.js') }}"></script>
{% endblock %}
```

## 3. 통일해야 할 사항

### 3.1 백엔드 표준화

#### 3.1.1 리소스 결과 형식
- 필수 필드:
  - `resource_id`: 리소스 식별자
  - `status`: 리소스 상태 코드 (`pass`, `fail`, `unknown`, `error`)
  - `advice`: 상세 권장 사항
  - `status_text`: 상태 텍스트 (UI에 표시)

#### 3.1.2 검사 결과 형식
- 필수 필드:
  - `status`: 검사 상태 (`ok`, `warning`, `error`, `info`)
  - `message`: 검사 결과 메시지
  - `data`: 검사 결과 데이터
  - `recommendations`: 권장 사항 목록

#### 3.1.3 데이터 구조
- 리소스 목록: `resources`
- 상태별 분류: `passed_resources`, `failed_resources`, `unknown_resources`
- 카운트 정보: `total_resources_count`, `failed_resources_count`

### 3.2 프론트엔드 표준화

#### 3.2.1 동적 탭 생성
- 전체 탭은 항상 첫 번째로 표시
- 상태별 탭은 `status_text` 값에 따라 동적 생성
- 탭 ID는 `${safeStatusText}-tab-${checkId}` 형식 사용
- 탭 콘텐츠 ID는 `${safeStatusText}-content-${checkId}` 형식 사용

#### 3.2.2 테이블 스타일
- 테이블에 고유한 클래스 부여: `[service]-table`
- 컬럼 너비 지정: 
  ```css
  .[service]-table th:nth-child(n) { width: x%; }
  ```
- 텍스트 자동 줄바꿈: 
  ```css
  .[service]-table td { word-break: break-word; }
  ```

#### 3.2.3 상태 표시
- 상태에 따른 아이콘 및 색상 일관성 유지
  - `pass`: 초록색, check-circle 아이콘
  - `fail`: 노란색, exclamation-triangle 아이콘
  - `unknown`: 파란색, info-circle 아이콘
  - `error`: 빨간색, times-circle 아이콘

## 4. 확장 시 주의사항

1. **백엔드 데이터 구조 일관성**
   - 모든 서비스가 동일한 데이터 구조를 따라야 함
   - 필수 필드가 누락되지 않도록 주의

2. **프론트엔드 동적 처리**
   - 백엔드에서 받은 데이터를 임의로 변경하지 않음
   - `status_text` 값을 그대로 사용하여 탭 및 상태 표시

3. **테이블 레이아웃**
   - 서비스별 특성에 맞게 컬럼 너비 조정
   - 컬럼 수가 많을 경우 가로 스크롤 고려

4. **오류 처리**
   - 모든 검사 항목에서 일관된 오류 처리 패턴 사용
   - 사용자에게 명확한 오류 메시지 제공

## 5. 예시 코드

### 5.1 EC2 인스턴스 타입 검사 예시

```python
# app/services/service_advisor/ec2/checks/instance_type_check.py
def run():
    try:
        # 리소스 수집 및 분석
        
        # 인스턴스 타입 최적화 분석
        status = RESOURCE_STATUS_PASS
        status_text = '최적화됨'
        advice = '현재 인스턴스 타입은 워크로드에 적합합니다.'
        
        if avg_cpu < 10 and max_cpu < 40:
            status = RESOURCE_STATUS_FAIL
            status_text = '최적화 필요'
            advice = 'CPU 사용률이 낮습니다. 더 작은 인스턴스 타입으로 변경하여 비용을 절감하세요.'
        
        # 표준화된 리소스 결과 생성
        instance_result = create_resource_result(
            resource_id=instance_id,
            status=status,
            advice=advice,
            status_text=status_text,
            instance_name=instance_name,
            instance_type=instance_type,
            avg_cpu=round(avg_cpu, 2),
            max_cpu=round(max_cpu, 2)
        )
        
        # 전체 결과 생성
        return create_check_result(
            status=STATUS_WARNING,
            message=message,
            data=data,
            recommendations=recommendations
        )
    except Exception as e:
        return create_error_result(f'인스턴스 타입 검사 중 오류가 발생했습니다: {str(e)}')
```

### 5.2 EC2 인스턴스 타입 테이블 예시

```javascript
// static/js/service-advisor/ec2.js
createInstanceTypeTable(instances) {
  if (!instances || instances.length === 0) return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
  
  return `
    <style>
      .instance-table th:nth-child(1) { width: 12%; }
      .instance-table th:nth-child(2) { width: 15%; }
      .instance-table th:nth-child(3) { width: 10%; }
      .instance-table th:nth-child(4) { width: 10%; }
      .instance-table th:nth-child(5) { width: 10%; }
      .instance-table th:nth-child(6) { width: 30%; }
      .instance-table th:nth-child(7) { width: 13%; }
      .instance-table td { word-break: break-word; }
    </style>
    <div class="table-responsive">
      <table class="awsui-table instance-table">
        <thead>
          <tr>
            <th>인스턴스 ID</th>
            <th>인스턴스 이름</th>
            <th>인스턴스 타입</th>
            <th>평균 CPU</th>
            <th>최대 CPU</th>
            <th>권장 사항</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          ${instances.map(instance => {
            let statusClass = '';
            let statusIcon = '';
            
            if (instance.status === 'fail') {
              statusClass = 'warning';
              statusIcon = 'exclamation-triangle';
            } else if (instance.status === 'pass') {
              statusClass = 'success';
              statusIcon = 'check-circle';
            } else if (instance.status === 'unknown') {
              statusClass = 'info';
              statusIcon = 'info-circle';
            } else if (instance.status === 'error') {
              statusClass = 'danger';
              statusIcon = 'times-circle';
            } else {
              statusClass = 'secondary';
              statusIcon = 'question-circle';
            }
            
            return `
              <tr>
                <td>${instance.id || ''}</td>
                <td>${instance.instance_name || 'N/A'}</td>
                <td>${instance.instance_type || ''}</td>
                <td>${instance.avg_cpu !== undefined ? `${instance.avg_cpu}%` : 'N/A'}</td>
                <td>${instance.max_cpu !== undefined ? `${instance.max_cpu}%` : 'N/A'}</td>
                <td>${instance.advice || ''}</td>
                <td>
                  <span class="resource-status ${statusClass}">
                    <i class="fas fa-${statusIcon}"></i>
                    ${instance.status_text || ''}
                  </span>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
}
```