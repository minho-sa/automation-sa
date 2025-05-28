# Service Advisor 아키텍처 분석

## 1. 개요

Service Advisor는 AWS 리소스를 분석하고 최적화 권장사항을 제공하는 웹 애플리케이션입니다. 이 문서는 현재 코드베이스의 아키텍처와 동작 원리를 객체지향적 관점에서 분석합니다.

## 2. 아키텍처 구조

Service Advisor는 다음과 같은 계층 구조로 설계되어 있습니다:

```
[웹 인터페이스 (Flask)] → [서비스 레이어] → [AWS 리소스 액세스 레이어]
```

### 2.1 주요 컴포넌트

1. **웹 인터페이스 (Flask)**
   - 사용자 인증 및 세션 관리
   - 대시보드 및 권장사항 뷰 제공
   - API 엔드포인트 제공

2. **서비스 레이어**
   - 리소스 수집 서비스 (`app/services/resource/`)
   - 권장사항 생성 서비스 (`app/services/recommendation/`)
   - 서비스 어드바이저 (`app/services/service_advisor/`)

3. **AWS 리소스 액세스 레이어**
   - AWS API 클라이언트 관리
   - 자격 증명 처리

## 3. 객체지향 설계 분석

### 3.1 서비스 어드바이저 패턴

서비스 어드바이저는 다음과 같은 객체지향 패턴을 사용합니다:

#### 3.1.1 팩토리 패턴

`ServiceAdvisorFactory` 클래스는 서비스 이름에 따라 적절한 어드바이저 객체를 생성합니다:

```python
class ServiceAdvisorFactory:
    def __init__(self):
        self.service_mapping = {
            'ec2': EC2Advisor,
            'lambda': LambdaServiceAdvisor,
            # 추가 서비스...
        }
    
    def get_advisor(self, service_name):
        if service_name not in self.service_mapping:
            return None
        
        advisor_class = self.service_mapping[service_name]
        return advisor_class()
        
    def get_available_services(self):
        # 사용 가능한 서비스 목록 반환
        services = []
        for service_name in self.service_mapping.keys():
            service_info = {
                'id': service_name,
                'name': self._get_service_display_name(service_name)
            }
            services.append(service_info)
        return services
```

#### 3.1.2 템플릿 메서드 패턴

`BaseAdvisor` 클래스는 공통 기능을 정의하고, 각 서비스별 어드바이저가 이를 확장합니다:

```python
class BaseAdvisor:
    def __init__(self):
        self.checks = {}
        self._register_checks()
    
    def _register_checks(self):
        # 서브클래스에서 구현
        pass
    
    def register_check(self, check_id, name, description, function, category, severity):
        # 검사 항목 등록 로직
        self.checks[check_id] = {
            'id': check_id,
            'name': name,
            'description': description,
            'function': function,
            'category': category,
            'severity': severity
        }
        
    def get_available_checks(self):
        # 사용 가능한 검사 항목 목록 반환
        return [
            {
                'id': check_id,
                'name': check_info['name'],
                'description': check_info['description'],
                'category': check_info['category'],
                'severity': check_info['severity']
            }
            for check_id, check_info in self.checks.items()
        ]
        
    def run_check(self, check_id):
        # 검사 실행 로직
        if check_id not in self.checks:
            raise ValueError(f"존재하지 않는 검사 항목 ID: {check_id}")
        
        check_info = self.checks[check_id]
        try:
            result = check_info['function']()
            result['id'] = check_id
            return result
        except Exception as e:
            return {
                'id': check_id,
                'status': 'error',
                'message': f'검사 실행 중 오류가 발생했습니다: {str(e)}'
            }
```

#### 3.1.3 전략 패턴

각 검사 항목은 독립적인 함수로 구현되어 어드바이저에 등록됩니다:

```python
# EC2Advisor 예시
def _register_checks(self):
    self.register_check(
        check_id='ec2-security-group',
        name='보안 그룹 설정 검사',
        description='...',
        function=security_group_check.run,
        category='보안',
        severity='high'
    )
```

### 3.2 권장사항 생성 패턴

권장사항 생성은 다음과 같은 패턴을 사용합니다:

#### 3.2.1 파이프라인 패턴

리소스 데이터를 수집하고 여러 검사를 통해 권장사항을 생성하는 파이프라인:

```python
def get_ec2_recommendations(instances, collection_id=None):
    recommendations = []
    
    for instance in instances:
        # 각 체크 함수 실행
        checks = [
            check_backup_recommendations(instance, collection_id),
            check_cpu_utilization(instance, collection_id),
            # 추가 검사...
        ]
        
        # 결과 필터링 (None 제외)
        instance_recommendations = [check for check in checks if check]
        recommendations.extend(instance_recommendations)
    
    return recommendations
```

#### 3.2.2 결과 표준화 패턴

모든 검사 결과는 표준화된 형식으로 반환됩니다:

```python
def create_check_result(status, message, data=None, recommendations=None, check_id=None):
    result = {
        'status': status,
        'message': message
    }
    
    if data is not None:
        result['data'] = data
    
    if recommendations is not None:
        result['recommendations'] = recommendations
    
    if check_id is not None:
        result['id'] = check_id
    
    return result

def create_resource_result(resource_id, status, advice, status_text, **additional_fields):
    result = {
        'id': resource_id,
        'status': status,
        'advice': advice,
        'status_text': status_text
    }
    
    # 추가 필드 병합
    result.update(additional_fields)
    
    return result
```

#### 3.2.3 EC2 검사 로직의 결과 표준화 적용

EC2 검사 로직에서는 결과 표준화 패턴이 다음과 같이 적용됩니다:

1. **표준화된 헬퍼 함수 사용**

   `check_result.py` 모듈에서 제공하는 헬퍼 함수들을 사용하여 모든 검사 결과를 일관된 형식으로 반환합니다:

   ```python
   # 검사 전체 결과 생성
   create_check_result(status, message, data, recommendations, check_id)

   # 개별 리소스 결과 생성 (모든 파라미터가 필수)
   create_resource_result(resource_id, status, advice, status_text, **additional_fields)

   # 오류 결과 생성
   create_error_result(error_message)
   ```

2. **실제 적용 예시**

   EC2 보안 그룹 검사에서의 적용:

   ```python
   # 개별 보안 그룹 결과 생성
   sg_result = create_resource_result(
       resource_id=sg_id,
       status=status,
       advice=advice,
       status_text=status_text,
       sg_name=sg_name,
       vpc_id=vpc_id,
       description=description,
       risky_rules=risky_rules
   )

   # 전체 검사 결과 생성
   return create_check_result(
       status=STATUS_WARNING,
       message=message,
       data=data,
       recommendations=recommendations
   )
   ```

   EC2 인스턴스 타입 검사에서의 적용:

   ```python
   # status_text 결정
   if recommendation == '다운사이징 권장':
       status_text = '과다 프로비저닝'
   elif recommendation == '업그레이드 권장':
       status_text = '부족한 리소스'
   else:
       status_text = '최적화됨'
       
   # 개별 인스턴스 결과 생성
   instance_result = create_resource_result(
       resource_id=instance_id,
       status=status,
       advice=advice,
       status_text=status_text,  # 필수 파라미터로 추가
       instance_name=instance_name,
       instance_type=instance_type,
       avg_cpu=round(avg_cpu, 2),
       max_cpu=round(max_cpu, 2),
       recommendation=recommendation
   )
   ```

3. **이점**

   이러한 결과 표준화 패턴은 다음과 같은 이점을 제공합니다:
   - **일관성**: 모든 EC2 검사가 동일한 형식의 결과를 반환하여 처리 로직 단순화
   - **확장성**: 새로운 검사 항목 추가 시 동일한 패턴을 따르면 기존 시스템과 통합 용이
   - **유지보수성**: 결과 형식 변경 시 헬퍼 함수만 수정하면 모든 검사에 적용됨
   - **프론트엔드 호환성**: 표준화된 결과 형식으로 UI 렌더링 로직 단순화

### 3.3 AWS 클라이언트 관리

`aws_client.py` 모듈은 AWS API 호출을 위한 클라이언트 생성 및 인증 처리를 담당합니다:

```python
def create_boto3_client(service_name, region=config.AWS_REGION, auth_type=None, **auth_params):
    client_kwargs = {'region_name': region}
    
    # 세션에서 인증 정보 가져오기
    if auth_type is None and session.get('auth_type'):
        auth_type = session.get('auth_type')
        auth_params = session.get('auth_params', {})
    
    if auth_type == 'access_key':
        # 직접 액세스 키로 인증
        client_kwargs['aws_access_key_id'] = auth_params.get('aws_access_key')
        client_kwargs['aws_secret_access_key'] = auth_params.get('aws_secret_key')
        # ...
    
    elif auth_type == 'role_arn':
        # 역할 수임하여 임시 자격 증명 획득
        temp_credentials = assume_role(...)
        # ...
    
    # boto3 클라이언트 생성 및 반환
    return boto3.client(service_name, **client_kwargs)
```

## 4. 데이터 흐름

### 4.1 권장사항 생성 흐름

1. 사용자가 웹 인터페이스에서 권장사항 생성 요청
2. 서버는 AWS 리소스 데이터 수집 (`app/services/resource/`)
3. 수집된 데이터를 기반으로 권장사항 생성 (`app/services/recommendation/`)
4. 생성된 권장사항을 사용자에게 표시

### 4.2 서비스 어드바이저 흐름

1. 사용자가 특정 서비스의 어드바이저 페이지 접근
2. `ServiceAdvisorFactory`가 해당 서비스의 어드바이저 객체 생성
3. 어드바이저는 `get_available_checks()` 메서드를 통해 사용 가능한 검사 항목 목록 제공
4. 사용자가 특정 검사 실행 요청
5. 어드바이저가 `run_check(check_id)` 메서드를 통해 검사 실행 및 결과 반환

### 4.3 웹 라우트 처리

`service_advisor.py` 라우트 모듈은 다음과 같은 엔드포인트를 제공합니다:

```python
@service_advisor_bp.route('/service-advisor')
@login_required
def service_advisor_view():
    # 서비스 어드바이저 메인 페이지 렌더링
    return render_template('service_advisor/index.html')

@service_advisor_bp.route('/service-advisor/<service_name>')
@login_required
def service_advisor_detail(service_name):
    # 특정 서비스에 대한 어드바이저 페이지 렌더링
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return render_template('service_advisor/not_found.html', service_name=service_name)
    
    checks = advisor.get_available_checks()
    return render_template(f'service_advisor/{service_name}.html', checks=checks, service_name=service_name)

@service_advisor_bp.route('/api/service-advisor/<service_name>/run-check', methods=['POST'])
@login_required
def run_service_check(service_name):
    # 특정 서비스의 검사 실행
    data = request.json
    check_id = data.get('check_id')
    
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return jsonify({'error': f'서비스 {service_name}에 대한 어드바이저를 찾을 수 없습니다.'}), 404
    
    try:
        result = advisor.run_check(check_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'검사 실행 중 오류가 발생했습니다: {str(e)}'}), 500
```

## 5. 검사 항목 분석

### 5.1 필수 값과 튜닝 가능 값

각 검사 항목은 다음과 같은 구조로 구성됩니다:

#### 5.1.1 필수 값

- `check_id`: 검사 항목 고유 식별자
- `name`: 검사 항목 이름
- `description`: 검사 항목 설명
- `function`: 검사 실행 함수
- `category`: 검사 카테고리 (보안, 비용 최적화 등)
- `severity`: 심각도 (high, medium, low)

#### 5.1.2 리소스 결과 필수 값

리소스 결과 생성 시 다음 값들이 필수입니다:

- `resource_id`: 리소스 고유 식별자
- `status`: 리소스 상태 (pass, fail, warning, unknown)
- `advice`: 리소스에 대한 권장 사항
- `status_text`: 상태를 설명하는 텍스트

#### 5.1.3 튜닝 가능 값

각 검사 함수 내부에서 다음과 같은 값을 조정할 수 있습니다:

- **EC2 CPU 사용률 검사**
  - `CPU_THRESHOLD['VERY_LOW']`: 낮은 CPU 사용률 기준 (기본값: 20%)
  - `CPU_THRESHOLD['HIGH']`: 높은 CPU 사용률 기준 (기본값: 80%)
  - `CPU_THRESHOLD['MONITORING_DAYS']`: 모니터링 기간 (기본값: 7일)

- **EC2 보안 그룹 검사**
  - `risky_ports`: 위험한 포트 목록 (기본값: [22, 3389, 3306, 5432])

- **Lambda 메모리 크기 검사**
  - 메모리 사용률 임계값 (낮음: 40%, 높음: 90%)

- **Lambda 타임아웃 설정 검사**
  - 타임아웃 사용률 임계값 (낮음: 20%, 높음: 80%)

### 5.2 검사 결과 상태 코드

`check_result.py` 모듈은 다음과 같은 상태 코드를 정의합니다:

```python
# 상태 상수 정의
STATUS_OK = 'ok'
STATUS_WARNING = 'warning'
STATUS_ERROR = 'error'
STATUS_INFO = 'info'

# 리소스 상태 상수 정의
RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_FAIL = 'fail'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_UNKNOWN = 'unknown'
```

## 6. 확장성

현재 아키텍처는 다음과 같은 방식으로 확장 가능합니다:

1. **새로운 서비스 추가**
   - `BaseAdvisor`를 상속받는 새로운 어드바이저 클래스 구현
   - `ServiceAdvisorFactory`의 `service_mapping`에 추가
   - 서비스별 템플릿 파일 추가 (`templates/service_advisor/<service_name>.html`)

2. **새로운 검사 항목 추가**
   - 서비스별 `checks` 디렉토리에 새로운 검사 함수 구현
   - 해당 서비스 어드바이저의 `_register_checks` 메서드에 등록

3. **권장사항 생성 로직 확장**
   - `app/services/recommendation/` 디렉토리에 새로운 권장사항 생성 함수 추가
   - `__init__.py`에 함수 등록

4. **사용자 인터페이스 확장**
   - 새로운 서비스에 대한 템플릿 추가
   - 대시보드 및 권장사항 뷰 확장

## 7. 결론

Service Advisor는 객체지향 설계 원칙을 적용하여 확장성과 유지보수성을 갖춘 아키텍처로 구성되어 있습니다. 팩토리 패턴, 템플릿 메서드 패턴, 전략 패턴 등을 활용하여 다양한 AWS 서비스에 대한 검사와 권장사항을 유연하게 제공할 수 있습니다.

`BaseAdvisor` 클래스의 `get_available_checks` 메서드는 등록된 모든 검사 항목의 메타데이터를 반환하여 웹 인터페이스에서 사용자에게 검사 항목 목록을 표시하는 데 사용됩니다. 이 메서드는 실제 검사 함수(`function`)를 제외한 모든 메타데이터를 포함하여 보안을 유지하면서도 필요한 정보를 제공합니다.

향후 개선 방향으로는 더 많은 AWS 서비스 지원, 검사 항목 확장, 사용자 정의 임계값 설정 기능, 권장사항 이행 자동화 등을 고려할 수 있습니다.