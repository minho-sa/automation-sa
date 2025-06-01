# 서비스 어드바이저 파일 구조

서비스 어드바이저는 AWS 리소스를 검사하고 최적화 권장사항을 제공하는 모듈입니다. 이 문서는 서비스 어드바이저의 파일 구조를 설명합니다.

## 디렉토리 구조 개요

```
automation-sa/
├── app/
│   ├── routes/
│   │   └── service_advisor.py       # 서비스 어드바이저 라우트
│   └── services/
│       └── service_advisor/         # 서비스 어드바이저 백엔드
│           ├── common/              # 공통 모듈
│           ├── ec2/                 # EC2 서비스 모듈
│           ├── iam/                 # IAM 서비스 모듈
│           ├── lambda_service/      # Lambda 서비스 모듈
│           ├── rds/                 # RDS 서비스 모듈
│           ├── s3/                  # S3 서비스 모듈
│           └── advisor_factory.py   # 어드바이저 팩토리
├── static/
│   ├── css/
│   │   └── service-advisor/         # 서비스 어드바이저 CSS
│   │       ├── common.css           # 공통 스타일
│   │       ├── history.css          # 기록 페이지 스타일
│   │       ├── ec2/                 # EC2 스타일
│   │       ├── iam/                 # IAM 스타일
│   │       ├── lambda/              # Lambda 스타일
│   │       ├── rds/                 # RDS 스타일
│   │       └── s3/                  # S3 스타일
│   └── js/
│       └── service-advisor/         # 서비스 어드바이저 JS
│           ├── common/              # 공통 JS
│           ├── ec2/                 # EC2 JS
│           ├── iam/                 # IAM JS
│           ├── lambda/              # Lambda JS
│           ├── rds/                 # RDS JS
│           ├── s3/                  # S3 JS
│           └── index.js             # 메인 페이지 JS
└── templates/
    └── service_advisor/            # 서비스 어드바이저 템플릿
        ├── common/                 # 공통 템플릿
        ├── ec2/                    # EC2 템플릿
        ├── iam/                    # IAM 템플릿
        ├── lambda/                 # Lambda 템플릿
        ├── rds/                    # RDS 템플릿
        ├── s3/                     # S3 템플릿
        └── index.html              # 메인 페이지 템플릿
```

## 백엔드 구조

### 공통 모듈 (`app/services/service_advisor/common/`)

- `__init__.py`: 모듈 초기화
- `base_advisor.py`: 기본 어드바이저 클래스
- `aws_client.py`: AWS 클라이언트 관리
- `history_storage.py`: 검사 기록 저장 및 관리
- `check_result.py`: 검사 결과 생성 유틸리티

### 서비스별 모듈

각 서비스 모듈은 다음과 같은 구조를 가집니다:

- `__init__.py`: 모듈 초기화
- `{service}_advisor.py`: 서비스별 어드바이저 클래스
- `checks/`: 검사 항목 모듈
  - `__init__.py`: 모듈 초기화
  - `{check_name}.py`: 개별 검사 항목 구현

예시: EC2 모듈 (`app/services/service_advisor/ec2/`)
- `__init__.py`
- `ec2_advisor.py`
- `checks/`
  - `__init__.py`
  - `security_group_check.py`
  - `instance_type_check.py`

### 어드바이저 팩토리 (`app/services/service_advisor/advisor_factory.py`)

서비스 이름에 따라 적절한 어드바이저 객체를 생성하는 팩토리 클래스입니다.

## 프론트엔드 구조

### 템플릿 (`templates/service_advisor/`)

#### 공통 템플릿 (`templates/service_advisor/common/`)

- `base.html`: 서비스 어드바이저 기본 템플릿
- `history.html`: 검사 기록 페이지
- `history_detail.html`: 검사 기록 상세 페이지
- `auth_status.html`: 인증 상태 표시
- `not_found.html`: 404 페이지

#### 서비스별 템플릿

각 서비스는 다음과 같은 템플릿을 가집니다:
- `{service}.html`: 서비스별 메인 페이지

예시: EC2 템플릿 (`templates/service_advisor/ec2/ec2.html`)

### JavaScript (`static/js/service-advisor/`)

#### 공통 JavaScript (`static/js/service-advisor/common/`)

- `common.js`: 공통 기능
- `auth.js`: 인증 관련 기능
- `history.js`: 기록 페이지 기능
- `pdf-export.js`: PDF 내보내기 기능

#### 서비스별 JavaScript

각 서비스는 다음과 같은 JavaScript 파일을 가집니다:
- `{service}.js`: 서비스별 기능

예시: EC2 JavaScript (`static/js/service-advisor/ec2/ec2.js`)

### CSS (`static/css/service-advisor/`)

- `common.css`: 공통 스타일
- `history.css`: 기록 페이지 스타일

#### 서비스별 CSS

각 서비스는 다음과 같은 CSS 파일을 가집니다:
- `{service}.css`: 서비스별 스타일

예시: EC2 CSS (`static/css/service-advisor/ec2/ec2.css`)

## 라우트 (`app/routes/service_advisor.py`)

서비스 어드바이저의 웹 라우트를 정의합니다:

- `/service-advisor`: 메인 페이지
- `/service-advisor/<service_name>`: 서비스별 페이지
- `/service-advisor/history`: 검사 기록 페이지
- `/service-advisor/history/<key>`: 검사 기록 상세 페이지
- `/api/service-advisor/<service_name>/run-check`: 검사 실행 API
- `/api/service-advisor/history/<service_name>/<check_id>`: 검사 기록 조회 API
- `/api/service-advisor/services`: 사용 가능한 서비스 목록 API
- `/api/service-advisor/history/delete/<key>`: 검사 기록 삭제 API