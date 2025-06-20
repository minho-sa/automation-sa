# AWS 리소스 관리 및 최적화 콘솔

AWS 리소스를 수집하고 분석하여 최적화 권장사항을 제공하는 Flask 기반 웹 애플리케이션입니다.

## 주요 기능

### 🔐 사용자 인증
- S3 기반 사용자 데이터 저장
- bcrypt를 사용한 비밀번호 해싱
- Flask-Login 세션 관리
- AWS 자격증명 (Access Key/Role ARN) 지원

### 📊 리소스 수집
- **지원 서비스**: EC2, S3 (현재 구현됨)
- CloudWatch 메트릭 수집 (EC2 CPU, 메모리, 네트워크)
- S3 기반 데이터 영구 저장
- 메모리 캐시를 통한 성능 최적화

### 🎯 서비스 어드바이저
- **지원 서비스**: EC2, S3, Lambda, RDS, IAM
- 보안, 성능, 비용 최적화 검사
- PDF 리포트 생성
- 검사 이력 관리

## 프로젝트 구조
```
.
├── app/
│   ├── models/
│   │   └── user.py                        # 사용자 모델 (Flask-Login)
│   ├── routes/
│   │   ├── auth.py                        # 로그인/로그아웃
│   │   ├── dashboard.py                   # 메인 대시보드 (호환성)
│   │   ├── resource.py                    # 리소스 수집/관리
│   │   └── service_advisor.py             # 서비스 어드바이저
│   ├── services/
│   │   ├── resource/
│   │   │   ├── collectors/
│   │   │   │   ├── common/                # 공통 수집기 모듈
│   │   │   │   ├── ec2/                   # EC2 수집기 (구현됨)
│   │   │   │   ├── s3/                    # S3 수집기 (구현됨)
│   │   │   │   ├── lambda/                # Lambda 수집기 (미구현)
│   │   │   │   └── rds/                   # RDS 수집기 (미구현)
│   │   │   ├── common/
│   │   │   │   ├── resource_model.py      # 리소스 데이터 모델
│   │   │   │   ├── data_storage.py        # S3 데이터 저장소
│   │   │   │   ├── base_collector.py      # 기본 수집기 클래스
│   │   │   │   └── aws_client.py          # AWS 클라이언트
│   │   │   ├── collector_factory.py       # 수집기 팩토리
│   │   │   ├── ec2_collector.py           # EC2 수집기 구현
│   │   │   └── s3_collector.py            # S3 수집기 구현
│   │   ├── service_advisor/
│   │   │   ├── common/                    # 공통 어드바이저 모듈
│   │   │   ├── ec2/                       # EC2 어드바이저
│   │   │   ├── s3/                        # S3 어드바이저
│   │   │   ├── lambda_service/            # Lambda 어드바이저
│   │   │   ├── rds/                       # RDS 어드바이저
│   │   │   ├── iam/                       # IAM 어드바이저
│   │   │   └── advisor_factory.py         # 어드바이저 팩토리
│   │   ├── aws_services.py                # AWS 서비스 통합
│   │   ├── aws_utils.py                   # AWS 유틸리티
│   │   ├── user_storage.py                # S3 기반 사용자 저장소
│   │   └── s3_storage.py                  # S3 저장소 서비스
│   ├── utils/
│   │   └── pdf_generator.py               # PDF 리포트 생성
│   └── __init__.py                        # Flask 앱 초기화
├── static/                                # CSS, JavaScript
├── templates/                             # Jinja2 템플릿
├── docs/                                  # 문서
├── logs/                                  # 애플리케이션 로그
├── config.py                              # 설정 파일
├── requirements.txt                       # Python 의존성
└── run.py                                 # 애플리케이션 실행
```

## 설치 및 설정

### 사전 요구 사항
- Python 3.7+
- AWS 계정 및 자격증명
- S3 버킷 (데이터 저장용)

### 설치

1. **저장소 복제**
```bash
git clone <repository-url>
cd again_console
```

2. **가상 환경 및 의존성**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **환경 설정**
`.env` 파일 생성:
```env
SECRET_KEY=your-secret-key
AWS_ACCESS_KEY=your-access-key
AWS_SECRET_KEY=your-secret-key
AWS_REGION=ap-northeast-2
DATA_BUCKET_NAME=your-bucket-name
```

4. **실행**
```bash
python run.py
```

## 사용 방법

### 1. 사용자 등록/로그인
- `http://localhost:5000` 접속
- 회원가입 후 AWS 자격증명 입력
- 로그인하여 대시보드 접속

### 2. 리소스 수집
- 리소스 관리 메뉴 접속
- 수집할 서비스 선택 (현재: EC2, S3)
- AWS 리전 선택 후 수집 시작
- 실시간 진행 상황 모니터링

### 3. 데이터 조회
- 수집 이력에서 데이터 확인
- 서비스별 상세 정보 조회
- CloudWatch 메트릭 확인 (EC2)

### 4. 서비스 어드바이저
- 서비스 어드바이저 메뉴 접속
- 검사할 서비스 선택
- 보안/성능/비용 검사 실행
- PDF 리포트 다운로드

## 현재 구현된 기능

### 리소스 수집 (구현됨)
- **EC2**: 인스턴스 정보, CPU/메모리/네트워크 메트릭, 보안 그룹, 볼륨 정보
- **S3**: 버킷 정보, 암호화 설정, 퍼블릭 액세스, 라이프사이클 정책, 스토리지 클래스

### 서비스 어드바이저 (구현됨)
- **EC2**: 인스턴스 타입, 보안 그룹, EBS 암호화, 백업, 미사용 리소스, 종료 보호, 모니터링
- **S3**: 퍼블릭 액세스, 암호화, 버전 관리, 라이프사이클, 로깅, 지능형 계층화
- **Lambda**: 메모리 할당, 타임아웃, 런타임, 코드 서명, 권한
- **RDS**: 백업 보존, 암호화, Multi-AZ, 퍼블릭 액세스, 인스턴스 크기
- **IAM**: MFA, 액세스 키 순환, 비활성 사용자, 루트 계정, 비밀번호 정책

### 데이터 저장
- S3 기반 계층적 데이터 저장
- 사용자별 데이터 분리
- 메모리 캐시 시스템
- 수집 이력 관리

## 문제 해결

### 필수 IAM 권한
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "s3:List*",
        "s3:Get*",
        "cloudwatch:Get*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket/*"
    }
  ]
}
```

### 일반적인 문제
1. **자격증명 오류**: `.env` 파일의 AWS 키 확인
2. **권한 부족**: 위 IAM 정책 적용
3. **S3 접근 오류**: 버킷 존재 및 권한 확인
4. **데이터 미표시**: 브라우저 캐시 삭제, 로그 확인
5. **CloudWatch 메트릭 없음**: EC2에 CloudWatch 에이전트 설치 필요

## 기술 스택

### 백엔드
- **Flask**: 웹 프레임워크
- **Flask-Login**: 사용자 인증
- **Boto3**: AWS SDK
- **bcrypt**: 비밀번호 해싱

### 프론트엔드
- **Bootstrap**: UI 프레임워크
- **JavaScript**: 동적 기능
- **Chart.js**: 데이터 시각화

### 저장소
- **S3**: 사용자 데이터 및 수집 데이터 저장
- **메모리 캐시**: 성능 최적화

### AWS 서비스
- **EC2**: 인스턴스 정보 수집
- **S3**: 버킷 정보 수집
- **CloudWatch**: 메트릭 수집
- **STS**: 자격증명 관리

## S3 데이터 구조

```
s3://bucket-name/
├── users/
│   └── {username}/
│       ├── profile.json                # 사용자 정보
│       └── collections/
│           └── {collection_id}/
│               ├── metadata.json       # 수집 메타데이터
│               ├── ec2.json           # EC2 데이터
│               └── s3.json            # S3 데이터
└── service_advisor/
    └── history/
        └── {username}/
            └── {service}/
                └── {timestamp}.json    # 검사 결과
```

## 개발 정보

### 의존성
- flask==2.0.1
- flask-login==0.5.0
- boto3==1.18.0
- python-dotenv==0.19.0
- reportlab==3.6.1 (PDF 생성)
- PyPDF2>=3.0.0 (PDF 병합)

### 로그
- 애플리케이션 로그: `logs/app.log`
- 로그 순환: 자동 (10개 파일)
- 로그 레벨: INFO, ERROR, WARNING

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.