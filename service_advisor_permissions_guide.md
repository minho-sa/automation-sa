# 서비스 어드바이저 최소 권한 가이드

## 개요
서비스 어드바이저 전체 기능을 사용하기 위해 필요한 최소 권한을 정리했습니다. 모든 권한은 읽기 전용으로 제한되어 있어 AWS 리소스에 대한 안전한 분석만 수행합니다.

## 필요한 IAM 권한

### 통합 권한 정책
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ServiceAdvisorReadOnlyPermissions",
            "Effect": "Allow",
            "Action": [
                "ec2:Describe*",
                "rds:Describe*",
                "rds:List*",
                "lambda:List*",
                "lambda:Get*",
                "iam:List*",
                "iam:Get*",
                "iam:GenerateCredentialReport",
                "s3:List*",
                "s3:Get*",
                "cloudwatch:Get*"
            ],
            "Resource": "*"
        }
    ]
}
```

## 권한별 안전성 분석

### 1. EC2 권한
- **`ec2:Describe*`**: EC2 리소스 정보만 조회 (인스턴스, 보안그룹, 볼륨, EIP 등)
  - ✅ **안전**: 읽기 전용, 리소스 생성/수정/삭제 불가
  - ✅ **용도**: 보안 설정, 백업 상태, 인스턴스 최적화 분석

### 2. RDS 권한
- **`rds:Describe*`**: RDS 인스턴스 설정 정보 조회
- **`rds:List*`**: RDS 리소스 목록 및 태그 조회
  - ✅ **안전**: 읽기 전용, 데이터베이스 설정 변경 불가
  - ✅ **용도**: 백업, 암호화, Multi-AZ, 인스턴스 크기 분석

### 3. Lambda 권한
- **`lambda:List*`**: Lambda 함수 목록 및 기본 설정 조회
- **`lambda:Get*`**: Lambda 함수 상세 설정 조회
  - ✅ **안전**: 읽기 전용, 함수 코드나 설정 변경 불가
  - ✅ **용도**: 메모리, 타임아웃, 런타임, 권한 분석

### 4. IAM 권한
- **`iam:List*`**: IAM 리소스 목록 조회 (사용자, 정책, 그룹, 역할)
- **`iam:Get*`**: IAM 리소스 상세 정보 조회 (정책 문서, 계정 설정)
- **`iam:GenerateCredentialReport`**: 자격 증명 보고서 생성
  - ✅ **안전**: 읽기 전용, 사용자나 정책 생성/수정/삭제 불가
  - ✅ **용도**: 액세스 키 교체, MFA 설정, 비활성 사용자 분석
  - ✅ **무료**: `GenerateCredentialReport`는 비용이 발생하지 않는 무료 기능
  - ⚠️ **참고**: 실제 리소스가 아닌 분석용 보고서만 생성

### 5. S3 권한 (향후 확장용)
- **`s3:List*`**: S3 버킷 목록 및 기본 정보 조회
- **`s3:Get*`**: S3 버킷 설정 정보 조회
  - ✅ **안전**: 읽기 전용, 버킷이나 객체 생성/수정/삭제 불가
  - ✅ **용도**: 암호화, 공개 액세스, 버전 관리 분석

### 6. CloudWatch 권한
- **`cloudwatch:Get*`**: CloudWatch 메트릭 데이터 조회
  - ✅ **안전**: 읽기 전용, 메트릭이나 알람 생성/수정/삭제 불가
  - ✅ **용도**: CPU, 메모리 사용률 등 성능 데이터 분석

## 보안 특징

### ✅ 완전한 읽기 전용
- **생성 권한 없음**: Create, Put, Post 등 생성 권한 제외
- **수정 권한 없음**: Update, Modify, Change 등 수정 권한 제외
- **삭제 권한 없음**: Delete, Remove, Terminate 등 삭제 권한 제외

### ✅ 데이터 보호
- **민감 데이터 접근 불가**: 실제 데이터나 파일 내용 접근 불가
- **설정 정보만 조회**: 리소스 구성 및 메타데이터만 분석
- **로그 데이터 접근 불가**: 애플리케이션 로그나 사용자 데이터 접근 불가

### ✅ 최소 권한 원칙
- **필요한 권한만**: 서비스 어드바이저 기능에 필요한 최소한의 권한
- **와일드카드 제한**: 읽기 전용 작업에만 와일드카드 사용
- **리소스 범위**: 필요시 특정 리소스로 제한 가능

## 역할 생성 및 사용

### 1. 신뢰 정책 (Trust Policy)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:root"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "Bool": {
                    "aws:MultiFactorAuthPresent": "true"
                }
            }
        }
    ]
}
```

### 2. 역할 생성 CLI 명령어
```bash
# 역할 생성
aws iam create-role \
    --role-name ServiceAdvisorRole \
    --assume-role-policy-document file://trust-policy.json

# 정책 연결
aws iam put-role-policy \
    --role-name ServiceAdvisorRole \
    --policy-name ServiceAdvisorPolicy \
    --policy-document file://service_advisor_minimum_permissions.json
```

### 3. 사용 예시
```python
# 서비스 어드바이저 실행
role_arn = "arn:aws:iam::123456789012:role/ServiceAdvisorRole"
result = service_advisor.run(role_arn=role_arn)
```

## 추가 보안 권장사항

### 1. MFA 요구
- 역할 사용 시 MFA 인증 필수 설정
- 신뢰 정책에 MFA 조건 포함

### 2. 시간 제한
- 역할 세션 시간 제한 (예: 1시간)
- 정기적인 재인증 요구

### 3. IP 제한
- 특정 IP 주소에서만 역할 사용 허용
- VPN이나 특정 네트워크에서만 접근

### 4. 로깅 및 모니터링
- CloudTrail을 통한 API 호출 로깅
- 비정상적인 접근 패턴 모니터링

이 권한 설정을 통해 서비스 어드바이저는 AWS 리소스를 안전하게 분석하면서도 보안을 유지할 수 있습니다.