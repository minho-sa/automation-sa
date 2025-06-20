# EC2 서비스 어드바이저 검사항목 분석

## 개요
EC2 서비스 어드바이저는 Amazon EC2 인스턴스와 관련 리소스의 보안, 성능, 비용 최적화, 운영 효율성, 데이터 보호를 위한 포괄적인 검사를 수행합니다.

## 검사항목 목록

### 1. 보안 그룹 설정 검사 (ec2-security-group)

#### 검사 목적
- **주요 목적**: 과도하게 개방된 보안 그룹 규칙으로 인한 보안 위험 식별
- **보안 위험**: 0.0.0.0/0과 같은 광범위한 CIDR 블록에 대한 SSH, RDP, 데이터베이스 포트 개방

#### 심각도 기준: HIGH
**HIGH로 설정한 이유:**
1. **직접적인 보안 위험**: 인터넷에서 직접 접근 가능한 중요 포트는 즉각적인 보안 위협
2. **공격 빈도**: SSH(22), RDP(3389) 포트는 가장 빈번하게 공격받는 대상
3. **영향 범위**: 한 번의 침해로 전체 인스턴스가 위험에 노출
4. **복구 난이도**: 침해 발생 시 시스템 전체 재구축이 필요할 수 있음

#### 검사 기준
- **FAIL 조건**:
  - SSH 포트(22)가 0.0.0.0/0에 개방
  - RDP 포트(3389)가 0.0.0.0/0에 개방
  - 데이터베이스 포트(3306, 5432, 1433, 27017, 6379, 5984)가 인터넷에 노출
  - 모든 프로토콜(-1)이 0.0.0.0/0에 개방된 경우
  - 위험한 포트 범위가 포함된 경우

#### 권장 개선 방안
1. **특정 IP 제한**: 관리자 IP 주소로만 SSH/RDP 접근 제한
2. **VPN/배스천 호스트**: 직접 접근 대신 중간 서버를 통한 접근
3. **AWS Systems Manager Session Manager**: SSH/RDP 대체 솔루션 사용
4. **정기적 검토**: 보안 그룹 규칙의 주기적 감사

---

### 2. 인스턴스 타입 최적화 (ec2-instance-type)

#### 검사 목적
- **주요 목적**: CloudWatch 메트릭 분석을 통한 인스턴스 크기 최적화
- **비용 효율성**: 과다/과소 프로비저닝된 인스턴스 식별

#### 심각도 기준: MEDIUM
**MEDIUM으로 설정한 이유:**
1. **비용 영향**: 직접적인 보안 위험은 아니지만 상당한 비용 절감 효과
2. **성능 영향**: 부적절한 크기는 애플리케이션 성능에 영향
3. **점진적 개선**: 즉시 해결하지 않아도 시스템이 중단되지 않음
4. **측정 가능**: 정량적 지표로 개선 효과 측정 가능

#### 검사 기준
- **FAIL 조건**:
  - 평균 CPU 사용률 < 10% AND 최대 CPU 사용률 < 40% (과다 프로비저닝)
  - 평균 CPU 사용률 > 80% OR 최대 CPU 사용률 > 90% (과소 프로비저닝)
- **UNKNOWN 조건**: 충분한 CloudWatch 메트릭 데이터가 없는 경우
- **분석 기간**: 최근 14일간의 CloudWatch 메트릭 데이터 (1시간 간격)

#### 권장 개선 방안
1. **다운사이징**: CPU 사용률이 지속적으로 낮은 인스턴스
2. **업그레이드**: CPU 사용률이 지속적으로 높은 인스턴스
3. **예약 인스턴스**: 안정적인 워크로드에 대한 비용 절감
4. **Auto Scaling**: 동적 워크로드에 대한 자동 크기 조정

---

### 3. EC2 퍼블릭 인스턴스 검사 (ec2_public_instance_check)

#### 검사 목적
- **주요 목적**: 불필요한 퍼블릭 IP 할당으로 인한 보안 위험 최소화
- **네트워크 보안**: 프라이빗 네트워크 구성을 통한 보안 강화

#### 심각도 기준: MEDIUM
**MEDIUM으로 설정한 이유:**
1. **보안 위험**: 퍼블릭 IP는 공격 표면을 증가시키지만 보안 그룹으로 제어 가능
2. **아키텍처 의존**: 웹 서버 등 일부 인스턴스는 퍼블릭 액세스가 필요
3. **점진적 개선**: 네트워크 아키텍처 변경은 시간이 필요
4. **대안 존재**: ALB/NLB를 통한 안전한 퍼블릭 액세스 가능

#### 검사 기준
- **WARNING 조건**: PublicIpAddress가 존재하는 인스턴스
- **PASS 조건**: 퍼블릭 IP가 없는 인스턴스
- **분석 대상**: terminated 상태를 제외한 모든 EC2 인스턴스

#### 권장 개선 방안
1. **프라이빗 서브넷**: 퍼블릭 액세스가 불필요한 인스턴스는 프라이빗 서브넷으로 이동
2. **로드 밸런서**: ALB/NLB를 통한 안전한 퍼블릭 액세스
3. **NAT Gateway**: 프라이빗 인스턴스의 아웃바운드 인터넷 액세스
4. **Systems Manager**: Session Manager를 통한 안전한 관리 접근

---

### 4. EBS 볼륨 암호화 검사 (ec2_ebs_encryption_check)

#### 검사 목적
- **주요 목적**: 저장 데이터의 암호화를 통한 데이터 보호
- **규제 준수**: 데이터 보호 규정 요구사항 충족

#### 심각도 기준: HIGH
**HIGH로 설정한 이유:**
1. **데이터 보안**: 암호화되지 않은 볼륨은 물리적 접근 시 데이터 노출 위험
2. **규제 요구사항**: 대부분의 데이터 보호 규정에서 암호화 필수
3. **복구 불가능**: 데이터 유출 후에는 되돌릴 수 없음
4. **비용 대비 효과**: 암호화 비용은 미미하지만 보안 효과는 큼

#### 검사 기준
- **FAIL 조건**: 암호화되지 않은 EBS 볼륨
- **분석 대상**: 모든 EBS 볼륨

#### 권장 개선 방안
1. **기본 암호화**: 계정 수준에서 EBS 기본 암호화 활성화
2. **KMS 키 관리**: AWS KMS를 통한 암호화 키 중앙 관리
3. **마이그레이션**: 기존 볼륨의 암호화 마이그레이션
4. **정책 적용**: 암호화되지 않은 볼륨 생성 방지 정책

---

### 5. 미사용 리소스 검사 (ec2_unused_resources_check)

#### 검사 목적
- **주요 목적**: 사용되지 않는 리소스로 인한 불필요한 비용 제거
- **비용 최적화**: Elastic IP, EBS 볼륨 등 미사용 리소스 식별

#### 심각도 기준: MEDIUM
**MEDIUM으로 설정한 이유:**
1. **비용 영향**: 미사용 리소스는 지속적인 비용 발생
2. **점진적 개선**: 즉시 해결하지 않아도 서비스 중단은 없음
3. **관리 효율성**: 리소스 정리를 통한 관리 복잡성 감소
4. **측정 가능**: 비용 절감 효과를 명확히 측정 가능

#### 검사 기준
- **WARNING 조건**:
  - InstanceId가 없는 Elastic IP (인스턴스에 연결되지 않음)
  - status가 'available'인 EBS 볼륨 (사용되지 않는 볼륨)
- **PASS 조건**: InstanceId가 있는 Elastic IP

#### 권장 개선 방안
1. **정기적 정리**: 주기적인 미사용 리소스 점검 및 정리
2. **자동화**: 미사용 리소스 자동 탐지 및 알림
3. **태그 관리**: 리소스 용도 및 소유자 태그를 통한 관리
4. **비용 모니터링**: Cost Explorer를 통한 비용 추적

---

### 6. 인스턴스 모니터링 설정 검사 (ec2_instance_monitoring_check)

#### 검사 목적
- **주요 목적**: CloudWatch 상세 모니터링을 통한 성능 가시성 확보
- **운영 효율성**: 성능 문제 조기 감지 및 대응

#### 심각도 기준: LOW
**LOW로 설정한 이유:**
1. **운영 개선**: 즉각적인 위험은 없지만 운영 효율성 향상
2. **비용 고려**: 상세 모니터링은 추가 비용 발생
3. **선택적 적용**: 모든 인스턴스에 필수는 아님
4. **대안 존재**: 기본 모니터링으로도 기본적인 감시 가능

#### 검사 기준
- **WARNING 조건**: 상세 모니터링이 비활성화된 인스턴스

#### 권장 개선 방안
1. **중요 인스턴스 우선**: 프로덕션 환경부터 상세 모니터링 적용
2. **알람 설정**: CloudWatch 알람을 통한 성능 이슈 감지
3. **비용 분석**: 모니터링 비용 vs 운영 효율성 분석
4. **로그 모니터링**: CloudWatch Logs 에이전트 설치 고려

---

### 7. 인스턴스 태그 관리 검사 (ec2_instance_tags_check)

#### 검사 목적
- **주요 목적**: 리소스 관리 및 비용 할당을 위한 태그 표준화
- **거버넌스**: 조직의 리소스 관리 정책 준수

#### 심각도 기준: LOW
**LOW로 설정한 이유:**
1. **관리 효율성**: 직접적인 위험은 없지만 관리 효율성 향상
2. **점진적 개선**: 시간을 두고 천천히 개선 가능
3. **조직별 차이**: 조직마다 태그 정책이 다를 수 있음
4. **비용 추적**: 태그 기반 비용 분석 및 할당에 유용

#### 검사 기준
- **WARNING 조건**: 필수 태그(Name, Environment, Owner) 중 하나 이상 누락
- **PASS 조건**: 모든 필수 태그가 설정됨
- **분석 대상**: terminated 상태를 제외한 모든 EC2 인스턴스

#### 권장 개선 방안
1. **태그 정책**: 조직 차원의 태그 표준 정의
2. **자동화**: Infrastructure as Code를 통한 태그 자동 적용
3. **정기적 검토**: 분기별 태그 준수 상태 검토
4. **비용 분석**: 태그 기반 비용 분석 및 최적화

---

### 8. 인스턴스 생명주기 검사 (ec2_instance_lifecycle_check)

#### 검사 목적
- **주요 목적**: 오래된 인스턴스 식별을 통한 보안 및 성능 개선
- **유지 관리**: 정기적인 인스턴스 업데이트 및 교체 권장

#### 심각도 기준: MEDIUM
**MEDIUM으로 설정한 이유:**
1. **보안 위험**: 오래된 인스턴스는 보안 패치가 누락될 가능성
2. **성능 개선**: 최신 AMI 및 인스턴스 타입의 성능 향상 기회
3. **점진적 개선**: 즉시 해결하지 않아도 서비스 중단은 없음
4. **계획적 접근**: 인스턴스 교체는 신중한 계획과 테스트 필요

#### 검사 기준
- **WARNING 조건**: 1년(365일) 이상 실행된 인스턴스

#### 권장 개선 방안
1. **정기적 교체**: 연간 인스턴스 교체 계획 수립
2. **최신 AMI**: 최신 보안 패치가 적용된 AMI 사용
3. **Blue-Green 배포**: 무중단 인스턴스 교체 전략
4. **자동화**: 인스턴스 교체 프로세스 자동화

---

### 9. 인스턴스 백업 상태 검사 (ec2_instance_backup_check)

#### 검사 목적
- **주요 목적**: 인스턴스 데이터의 백업 상태 확인
- **데이터 보호**: 스냅샷을 통한 데이터 보호 및 복구 능력 확보

#### 심각도 기준: HIGH
**HIGH로 설정한 이유:**
1. **데이터 보호**: 백업 없는 데이터 손실은 치명적 영향
2. **복구 능력**: 장애 발생 시 신속한 복구를 위한 필수 요소
3. **비즈니스 연속성**: 백업은 재해 복구 계획의 핵심
4. **규제 요구사항**: 많은 산업에서 데이터 백업을 법적으로 요구

#### 검사 기준
- **WARNING 조건**: 최근 7일 내 스냅샷 백업이 없는 인스턴스

#### 권장 개선 방안
1. **자동화된 백업**: AWS Backup을 통한 자동 백업 정책
2. **정기적 스냅샷**: 중요한 인스턴스의 일일 스냅샷
3. **백업 테스트**: 정기적인 백업 복원 테스트
4. **보존 정책**: 비용 효율적인 백업 보존 정책 수립

---

### 10. 인스턴스 종료 보호 검사 (ec2_termination_protection_check)

#### 검사 목적
- **주요 목적**: 실수로 인한 중요 인스턴스 종료 방지
- **운영 안정성**: 프로덕션 환경의 안정성 확보

#### 심각도 기준: MEDIUM
**MEDIUM으로 설정한 이유:**
1. **운영 안정성**: 실수로 인한 서비스 중단 방지
2. **환경별 차이**: 프로덕션 환경에서만 필수
3. **복구 가능**: 종료된 인스턴스도 백업이 있으면 복구 가능
4. **관리 복잡성**: 종료 보호는 관리 절차를 복잡하게 만들 수 있음

#### 검사 기준
- **WARNING 조건**: Environment 태그가 'prod', 'production', 'prd'인 인스턴스의 DisableApiTermination이 false
- **PASS 조건**: 종료 보호가 활성화되었거나 프로덕션 환경이 아닌 경우
- **환경 식별**: Environment 태그를 통한 프로덕션 환경 식별

#### 권장 개선 방안
1. **프로덕션 필수**: 모든 프로덕션 인스턴스에 종료 보호 설정
2. **환경 태그**: Environment 태그를 통한 환경 구분
3. **IAM 정책**: 인스턴스 종료 권한 제한
4. **모니터링**: 종료 보호 설정 변경 감시

---

### 11. 인스턴스 세대 검사 (ec2_instance_generation_check)

#### 검사 목적
- **주요 목적**: 구세대 인스턴스 타입 식별 및 최신 세대 업그레이드 권장
- **성능 최적화**: 최신 세대의 향상된 성능 및 기능 활용

#### 심각도 기준: MEDIUM
**MEDIUM으로 설정한 이유:**
1. **성능 개선**: 최신 세대는 더 나은 성능과 비용 효율성 제공
2. **기술 부채**: 구세대 사용은 장기적으로 기술 부채 누적
3. **점진적 개선**: 즉시 해결하지 않아도 서비스 중단은 없음
4. **호환성**: 인스턴스 세대 변경 시 호환성 테스트 필요

#### 검사 기준
- **WARNING 조건**: 구세대 인스턴스 타입(t1, t2, m1, m2, m3, c1, c3, r3, i2, d2, g2) 사용

#### 권장 개선 방안
1. **최신 세대 업그레이드**: t3, m5, c5, r5 등 최신 세대로 업그레이드
2. **성능 테스트**: 업그레이드 후 성능 영향 측정
3. **단계적 적용**: 개발 → 스테이징 → 프로덕션 순서로 적용
4. **Compute Optimizer**: AWS Compute Optimizer 권장사항 활용

## 검사 항목별 심각도 분포

### 총 검사 항목: 11개

### HIGH (높음) - 즉시 조치 필요 (3개)
- 보안 그룹 설정 검사
- EBS 볼륨 암호화 검사
- 인스턴스 백업 상태 검사

### MEDIUM (중간) - 계획적 개선 필요 (6개)
- 인스턴스 타입 최적화
- EC2 퍼블릭 인스턴스 검사
- 미사용 리소스 검사
- 인스턴스 생명주기 검사
- 인스턴스 종료 보호 검사
- 인스턴스 세대 검사

### LOW (낮음) - 점진적 개선 권장 (2개)
- 인스턴스 모니터링 설정 검사
- 인스턴스 태그 관리 검사