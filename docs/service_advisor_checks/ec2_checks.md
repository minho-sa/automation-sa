# EC2 서비스 어드바이저 검사 항목

EC2 서비스 어드바이저는 EC2 인스턴스와 관련 리소스에 대한 다양한 검사를 수행하여 보안, 비용 최적화, 성능 등의 측면에서 개선 사항을 제안합니다.

## 검사 항목 목록

| 검사 ID | 이름 | 카테고리 | 심각도 | 설명 |
|---------|------|----------|--------|------|
| ec2-security-group | 보안 그룹 설정 검사 | 보안 | high | EC2 인스턴스의 보안 그룹 설정을 검사하여 0.0.0.0/0과 같이 과도하게 개방된 인바운드 규칙이 있는지 확인합니다. |
| ec2-instance-type | 인스턴스 타입 최적화 | 비용 최적화 | medium | CloudWatch 지표를 분석하여 EC2 인스턴스의 CPU 사용률을 확인하고, 과다 프로비저닝되거나 부족한 인스턴스를 식별합니다. |

## 검사 결과 구조

### 공통 결과 구조

모든 검사 항목은 다음과 같은 공통 결과 구조를 가집니다:

```json
{
  "status": "ok|warning|error",
  "message": "검사 결과 요약 메시지",
  "data": {
    // 검사 항목별 상세 데이터
  },
  "recommendations": [
    "권장사항 1",
    "권장사항 2"
  ]
}
```

### 보안 그룹 설정 검사 결과 구조

```json
{
  "status": "warning",
  "message": "5개의 보안 그룹 중 2개에서 잠재적인 보안 위험이 발견되었습니다.",
  "data": {
    "security_groups": [
      {
        "id": "sg-1234567890abcdef0",
        "status": "fail",
        "advice": "SSH 접속은 특정 IP 주소로 제한하거나 VPN/배스천 호스트를 통해 접근하도록 설정하세요.",
        "status_text": "위험",
        "sg_name": "web-server-sg",
        "vpc_id": "vpc-1234567890abcdef0",
        "description": "Web server security group",
        "risky_rules": [
          {
            "cidr": "0.0.0.0/0",
            "protocol": "tcp",
            "port_range": "22",
            "risk": "모든 IP에 대해 위험한 포트가 개방되어 있습니다."
          }
        ],
        "risky_rules_count": 1
      }
    ],
    "passed_groups": [...],
    "failed_groups": [...],
    "problem_count": 2,
    "total_count": 5
  },
  "recommendations": [
    "SSH 접속은 특정 IP 주소로 제한하거나 VPN/배스천 호스트를 통해 접근하도록 설정하세요. (영향받는 보안 그룹: web-server-sg)"
  ]
}
```

### 인스턴스 타입 최적화 검사 결과 구조

```json
{
  "status": "warning",
  "message": "10개 인스턴스 중 3개가 최적화가 필요합니다.",
  "data": {
    "instances": [
      {
        "id": "i-1234567890abcdef0",
        "status": "fail",
        "advice": "CPU 사용률이 낮습니다(평균: 5.2%, 최대: 15.3%). 더 작은 인스턴스 타입으로 변경하세요.",
        "status_text": "최적화 필요",
        "instance_name": "web-server-1",
        "instance_type": "t3.large",
        "avg_cpu": 5.2,
        "max_cpu": 15.3
      }
    ],
    "passed_instances": [...],
    "failed_instances": [...],
    "unknown_instances": [...],
    "problem_count": 3,
    "total_count": 10
  },
  "recommendations": [
    "사용률이 낮은 2개 인스턴스는 더 작은 인스턴스 타입으로 변경하여 비용을 절감하세요. (영향받는 인스턴스: web-server-1 (i-1234567890abcdef0))",
    "사용률이 높은 1개 인스턴스는 더 큰 인스턴스 타입으로 변경하여 성능을 개선하세요. (영향받는 인스턴스: api-server-1 (i-0987654321fedcba0))"
  ]
}
```