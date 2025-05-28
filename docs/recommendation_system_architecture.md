# AWS 리소스 추천 시스템 아키텍처

## 1. 개요

이 문서는 AWS 리소스 검사 및 추천 시스템의 아키텍처와 동작 원리를 설명합니다. 이 시스템은 AWS 계정의 다양한 서비스(EC2, S3, Lambda, IAM 등)를 분석하고 보안, 비용 최적화, 성능 개선을 위한 권장사항을 제공합니다.

## 2. 시스템 아키텍처

시스템은 크게 다음과 같은 구성 요소로 이루어져 있습니다:

```
[웹 인터페이스 (Flask)] → [리소스 수집 서비스] → [권장사항 생성 서비스] → [서비스 어드바이저]
```

### 2.1 주요 컴포넌트

1. **웹 인터페이스 (Flask)**
   - 사용자 인증 및 세션 관리
   - 대시보드 및 권장사항 뷰 제공
   - 리소스 수집 진행 상황 표시

2. **리소스 수집 서비스**
   - AWS API를 통한 리소스 데이터 수집
   - 서비스별 리소스 정보 구조화

3. **권장사항 생성 서비스**
   - 수집된 리소스 데이터 분석
   - 서비스별 검사 항목 실행
   - 권장사항 생성 및 우선순위 지정

4. **서비스 어드바이저**
   - 심층 분석 및 상세 권장사항 제공
   - 사용자 요청에 따른 특정 검사 실행

## 3. 객체지향 설계

### 3.1 리소스 수집 서비스

리소스 수집 서비스는 각 AWS 서비스별로 모듈화되어 있습니다:

```
app/services/resource/
├── base_service.py
├── ec2.py
├── s3.py
├── lambda_service.py
├── iam.py
└── ...
```

각 모듈은 해당 서비스의 리소스를 수집하고 표준화된 형식으로 반환합니다.

#### 3.1.1 인증 처리

`base_service.py`에는 AWS API 호출을 위한 인증 처리 로직이 포함되어 있습니다:

```python
def create_boto3_client(service_name, region, auth_type='access_key', **auth_params):
    client_kwargs = {'region_name': region}
    
    if auth_type == 'access_key':
        # 직접 액세스 키로 인증
        client_kwargs['aws_access_key_id'] = auth_params.get('aws_access_key')
        client_kwargs['aws_secret_access_key'] = auth_params.get('aws_secret_key')
        # ...
    
    elif auth_type == 'role_arn':
        # 역할 수임하여 임시 자격 증명 획득
        temp_credentials = assume_role(...)
        # ...
    
    return boto3.client(service_name, **client_kwargs)
```

### 3.2 권장사항 생성 서비스

권장사항 생성 서비스는 다음과 같은 구조로 설계되어 있습니다:

```
app/services/recommendation/
├── __init__.py
├── get_ec2_recommendations.py
├── get_s3_recommendations.py
├── get_lambda_recommendations.py
├── get_iam_recommendations.py
├── check/
│   ├── ec2/
│   ├── s3/
│   ├── lambda_service/
│   └── iam/
└── ...
```

#### 3.2.1 권장사항 생성 흐름

1. 서비스별 권장사항 함수 호출 (`get_ec2_recommendations` 등)
2. 수집된 리소스 데이터를 각 검사 함수에 전달
3. 검사 함수에서 권장사항 생성
4. 생성된 권장사항 반환

```python
def get_ec2_recommendations(instances, collection_id=None):
    recommendations = []
    
    for instance in instances:
        # 각 체크 함수 실행
        checks = [
            check_backup_recommendations(instance, collection_id),
            check_cpu_utilization(instance, collection_id),
            # ...
        ]
        
        # 결과 필터링 (None 제외)
        instance_recommendations = [check for check in checks if check]
        recommendations.extend(instance_recommendations)
    
    return recommendations
```

#### 3.2.2 검사 함수 구조

각 검사 함수는 다음과 같은 구조로 구현되어 있습니다:

```python
def check_cpu_utilization(instance, collection_id=None):
    # 상수 정의
    CPU_THRESHOLD = {
        'VERY_LOW': 20,
        'HIGH': 80,
        'MONITORING_DAYS': 7
    }
    
    # 리소스 분석
    # ...
    
    # 권장사항 생성
    return {
        'service': 'EC2',
        'resource': instance_id,
        'message': '...',
        'severity': '중간',
        'steps': [...],
        'problem': '...',
        'impact': '...',
        'benefit': '...',
        'metadata': {...}
    }
```

### 3.3 서비스 어드바이저

서비스 어드바이저는 객체지향적인 설계로 구현되어 있습니다:

```
app/services/service_advisor/
├── __init__.py
├── advisor_factory.py
├── base_advisor.py
├── check_result.py
├── aws_client.py
├── ec2/
│   ├── __init__.py
│   ├── ec2_advisor.py
│   └── checks/
└── lambda_service/
    ├── __init__.py
    ├── lambda_service_advisor.py
    └── checks/
```

#### 3.3.1 팩토리 패턴

`ServiceAdvisorFactory` 클래스는 서비스 이름에 따라 적절한 어드바이저 객체를 생성합니다:

```python
class ServiceAdvisorFactory:
    def __init__(self):
        self.service_mapping = {
            'ec2': EC2Advisor,
            'lambda': LambdaServiceAdvisor,
            # ...
        }
    
    def get_advisor(self, service_name):
        if service_name not in self.service_mapping:
            return None
        
        advisor_class = self.service_mapping[service_name]
        return advisor_class()
```

#### 3.3.2 템플릿 메서드 패턴

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
        
    def run_check(self, check_id):
        # 검사 실행 로직
```

## 4. 데이터 흐름

### 4.1 사용자 인증 흐름

1. 사용자가 로그인 페이지에서 자격 증명 입력
2. 서버는 사용자 인증 및 세션 생성
3. AWS 자격 증명 정보를 세션에 저장
4. 인증된 사용자는 대시보드로 리디렉션

### 4.2 리소스 수집 흐름

1. 사용자가 데이터 수집 요청
2. 서버는 선택된 서비스에 대한 리소스 수집 시작
3. 수집 진행 상황을 실시간으로 업데이트
4. 수집 완료 후 결과 저장

### 4.3 권장사항 생성 흐름

1. 수집된 리소스 데이터를 기반으로 권장사항 생성 시작
2. 각 서비스별 권장사항 함수 호출
3. 생성된 권장사항을 우선순위에 따라 정렬
4. 결과를 사용자에게 표시

## 5. 검사 항목 분석

### 5.1 EC2 검사 항목

| 검사 ID | 설명 | 카테고리 | 심각도 | 필수 값 | 튜닝 가능 값 |
|---------|------|----------|--------|---------|--------------|
| ec2-security-group | 보안 그룹 설정 검사 | 보안 | 높음 | - | risky_ports: [22, 3389, 3306, 5432] |
| ec2-instance-type | 인스턴스 타입 최적화 | 비용 최적화 | 중간 | - | avg_cpu_threshold: 10%, max_cpu_threshold: 80% |
| ec2-cpu-utilization | CPU 사용률 모니터링 | 성능 | 중간 | - | VERY_LOW: 20%, HIGH: 80%, MONITORING_DAYS: 7 |
| ec2-backup | 백업 권장사항 | 복원력 | 중간 | - | - |
| ec2-stopped-instance | 중지된 인스턴스 검사 | 비용 최적화 | 낮음 | - | stop_threshold_days: 30 |

### 5.2 S3 검사 항목

| 검사 ID | 설명 | 카테고리 | 심각도 | 필수 값 | 튜닝 가능 값 |
|---------|------|----------|--------|---------|--------------|
| s3-public-access | 퍼블릭 액세스 검사 | 보안 | 높음 | - | - |
| s3-versioning | 버전 관리 검사 | 데이터 보호 | 중간 | - | - |
| s3-encryption | 암호화 설정 검사 | 보안 | 높음 | - | - |
| s3-lifecycle-rules | 수명 주기 규칙 검사 | 비용 최적화 | 낮음 | - | - |
| s3-tag-management | 태그 관리 검사 | 관리 | 낮음 | - | - |

### 5.3 Lambda 검사 항목

| 검사 ID | 설명 | 카테고리 | 심각도 | 필수 값 | 튜닝 가능 값 |
|---------|------|----------|--------|---------|--------------|
| lambda-memory-size | 메모리 크기 최적화 | 비용 최적화 | 중간 | - | low_threshold: 40%, high_threshold: 90% |
| lambda-runtime-version | 런타임 버전 검사 | 보안 | 높음 | - | - |
| lambda-timeout-setting | 타임아웃 설정 검사 | 성능 | 중간 | - | low_threshold: 20%, high_threshold: 80% |
| lambda-vpc-configuration | VPC 구성 검사 | 네트워크 | 중간 | - | - |
| lambda-xray-tracing | X-Ray 추적 검사 | 모니터링 | 낮음 | - | - |

### 5.4 IAM 검사 항목

| 검사 ID | 설명 | 카테고리 | 심각도 | 필수 값 | 튜닝 가능 값 |
|---------|------|----------|--------|---------|--------------|
| iam-mfa-enabled | MFA 활성화 검사 | 보안 | 높음 | - | - |
| iam-access-key-rotation | 액세스 키 교체 검사 | 보안 | 중간 | - | rotation_days: 90 |
| iam-unused-credentials | 미사용 자격 증명 검사 | 보안 | 중간 | - | unused_days: 90 |
| iam-password-policy | 암호 정책 검사 | 보안 | 중간 | - | - |
| iam-external-trust-roles | 외부 신뢰 역할 검사 | 보안 | 높음 | - | - |

## 6. 확장성

현재 아키텍처는 다음과 같은 방식으로 확장 가능합니다:

1. **새로운 서비스 지원**
   - `app/services/resource/` 디렉토리에 새로운 리소스 수집 모듈 추가
   - `app/services/recommendation/` 디렉토리에 새로운 권장사항 생성 함수 추가
   - `app/services/service_advisor/` 디렉토리에 새로운 어드바이저 클래스 추가

2. **새로운 검사 항목 추가**
   - 서비스별 `check/` 디렉토리에 새로운 검사 함수 추가
   - 권장사항 생성 함수에 새로운 검사 함수 등록
   - 서비스 어드바이저에 새로운 검사 항목 등록

3. **사용자 인터페이스 확장**
   - 새로운 서비스에 대한 템플릿 추가
   - 대시보드 및 권장사항 뷰 확장

## 7. 결론

이 시스템은 객체지향 설계 원칙을 적용하여 확장성과 유지보수성을 갖춘 아키텍처로 구성되어 있습니다. 팩토리 패턴, 템플릿 메서드 패턴, 전략 패턴 등을 활용하여 다양한 AWS 서비스에 대한 검사와 권장사항을 유연하게 제공할 수 있습니다.

향후 개선 방향으로는 더 많은 AWS 서비스 지원, 검사 항목 확장, 사용자 정의 임계값 설정 기능, 권장사항 이행 자동화 등을 고려할 수 있습니다.