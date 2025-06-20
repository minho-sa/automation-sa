# RDS 서비스 어드바이저 검사항목 분석

## 개요
RDS 서비스 어드바이저는 Amazon RDS 데이터베이스 인스턴스의 보안, 가용성, 성능, 비용 최적화를 위한 포괄적인 검사를 수행합니다.

## 검사항목 목록

### 1. 백업 보존 기간 검사 (rds-backup-retention)

#### 검사 목적
- **주요 목적**: 데이터 손실 방지를 위한 적절한 백업 정책 확인
- **데이터 보호**: 하드웨어 장애, 인적 오류, 악의적 행위로부터 데이터 보호

#### 심각도 기준: HIGH
**HIGH로 설정한 이유:**
1. **데이터 중요성**: 데이터베이스는 비즈니스의 핵심 자산으로 손실 시 치명적 영향
2. **복구 불가능성**: 백업 없이 데이터 손실 시 완전한 복구가 불가능
3. **규제 요구사항**: 대부분의 산업에서 데이터 백업을 법적으로 요구
4. **비즈니스 연속성**: 백업은 재해 복구 계획의 핵심 요소

#### 검사 기준
- **FAIL 조건**: BackupRetentionPeriod < 1 (자동 백업 비활성화)
- **WARNING 조건**: BackupRetentionPeriod < 7일
- **PASS 조건**: BackupRetentionPeriod >= 7일
- **권장 기준**: 최소 7일 (recommended_retention = 7)
- **분석 대상**: 모든 RDS 인스턴스의 BackupRetentionPeriod 설정

#### 권장 개선 방안
1. **최소 보존 기간**: 프로덕션 DB는 최소 7일 이상 설정
2. **장기 백업**: 중요한 데이터는 스냅샷을 통한 장기 보존
3. **백업 테스트**: 정기적인 백업 복원 테스트 수행
4. **자동화**: 백업 정책의 자동 적용 및 모니터링

---

### 2. 다중 AZ 구성 검사 (rds-multi-az)

#### 검사 목적
- **주요 목적**: 데이터베이스 고가용성 확보
- **장애 대응**: 하드웨어 장애, AZ 장애 시 자동 장애 조치

#### 심각도 기준: MEDIUM
**MEDIUM으로 설정한 이유:**
1. **가용성 중요성**: 서비스 중단은 비즈니스에 영향을 주지만 데이터 손실만큼 치명적이지 않음
2. **비용 고려**: 다중 AZ는 추가 비용이 발생하여 모든 환경에 필수는 아님
3. **환경별 차이**: 개발/테스트 환경에서는 선택적으로 적용 가능
4. **대안 존재**: 읽기 전용 복제본 등 다른 고가용성 방법 존재

#### 검사 기준
- **FAIL 조건**: 프로덕션 환경 인스턴스의 MultiAZ가 false
- **WARNING 조건**: 일반 환경 인스턴스의 MultiAZ가 false
- **PASS 조건**: MultiAZ가 true인 경우
- **환경 식별**: 
  - 태그: environment/env 키가 'prod', 'production', 'prd' 포함
  - 인스턴스명: 'prod', 'production', 'prd' 포함
- **분석 대상**: 모든 RDS 인스턴스의 MultiAZ 설정

#### 권장 개선 방안
1. **프로덕션 필수**: 모든 프로덕션 데이터베이스에 다중 AZ 구성
2. **비용 분석**: 다중 AZ 비용 vs 다운타임 비용 분석
3. **테스트**: 장애 조치 시나리오 테스트 수행
4. **모니터링**: 장애 조치 이벤트 모니터링 및 알림 설정

---

### 3. 암호화 설정 검사 (rds-encryption)

#### 검사 목적
- **주요 목적**: 저장 데이터의 암호화를 통한 데이터 보호
- **규제 준수**: 개인정보보호법, GDPR 등 규제 요구사항 충족

#### 심각도 기준: HIGH
**HIGH로 설정한 이유:**
1. **데이터 보안**: 암호화되지 않은 데이터는 물리적 접근 시 노출 위험
2. **규제 요구사항**: 대부분의 데이터 보호 규정에서 암호화 필수
3. **민감 정보**: 데이터베이스는 일반적으로 민감한 정보 포함
4. **복구 불가능**: 암호화 없이 데이터 유출 시 되돌릴 수 없음

#### 검사 기준
- **FAIL 조건**: 프로덕션 환경 인스턴스의 StorageEncrypted가 false
- **WARNING 조건**: 일반 환경 인스턴스의 StorageEncrypted가 false
- **PASS 조건**: StorageEncrypted가 true인 경우
- **환경 식별**: 
  - 태그: environment/env가 'prod'/'production'
  - 인스턴스명: 'prod-', 'production-' 시작하거나 'prod' 포함
- **분석 대상**: 모든 RDS 인스턴스의 StorageEncrypted 설정

#### 권장 개선 방안
1. **기본 암호화**: 모든 새 인스턴스에 암호화 기본 적용
2. **키 관리**: AWS KMS를 통한 암호화 키 관리
3. **마이그레이션**: 기존 암호화되지 않은 인스턴스의 암호화 마이그레이션
4. **성능 테스트**: 암호화 적용 후 성능 영향 측정

---

### 4. 공개 액세스 설정 검사 (rds-public-access)

#### 검사 목적
- **주요 목적**: 데이터베이스의 인터넷 노출 방지
- **보안 강화**: 무차별 대입 공격 및 취약점 스캐닝 방지

#### 심각도 기준: HIGH
**HIGH로 설정한 이유:**
1. **직접적 위험**: 인터넷에 노출된 데이터베이스는 즉각적인 공격 대상
2. **공격 빈도**: 공개 데이터베이스는 자동화된 공격 도구의 주요 타겟
3. **데이터 유출**: 성공적인 공격 시 전체 데이터베이스 내용 유출 가능
4. **방어 어려움**: 인터넷 전체에서 오는 공격을 모두 차단하기 어려움

#### 검사 기준
- **FAIL 조건**: PubliclyAccessible = true로 설정된 모든 인스턴스
- **PASS 조건**: PubliclyAccessible = false로 설정된 인스턴스
- **예외 없음**: 모든 데이터베이스는 VPC 내부에서만 접근 가능해야 함
- **분석 대상**: 모든 RDS 인스턴스의 PubliclyAccessible 설정

#### 권장 개선 방안
1. **VPC 구성**: 모든 데이터베이스를 VPC 내부에 배치
2. **프라이빗 서브넷**: 데이터베이스 전용 프라이빗 서브넷 구성
3. **접근 제어**: 보안 그룹을 통한 세밀한 접근 제어
4. **VPN/Direct Connect**: 외부 접근이 필요한 경우 안전한 연결 방법 사용

---

### 5. 인스턴스 크기 최적화 검사 (rds-instance-sizing)

#### 검사 목적
- **주요 목적**: CloudWatch 메트릭 분석을 통한 인스턴스 크기 최적화
- **비용 효율성**: 과다/과소 프로비저닝된 인스턴스 식별

#### 심각도 기준: MEDIUM
**MEDIUM으로 설정한 이유:**
1. **비용 영향**: 데이터베이스 인스턴스는 상당한 비용을 차지
2. **성능 영향**: 부적절한 크기는 애플리케이션 성능에 직접 영향
3. **점진적 개선**: 즉시 해결하지 않아도 서비스 중단은 없음
4. **복잡성**: 데이터베이스 크기 조정은 신중한 계획과 테스트 필요

#### 검사 기준
- **FAIL 조건**:
  - 평균 CPU 사용률 < 5% AND 최대 CPU 사용률 < 20% (다운사이징 권장)
  - 평균 CPU 사용률 > 70% OR 최대 CPU 사용률 > 90% (업그레이드 권장)
- **PASS 조건**: CPU 사용률이 적절한 범위 내 (5-70%)
- **UNKNOWN 조건**: CloudWatch 데이터 부족 또는 접근 오류
- **분석 기간**: 최근 14일간의 CloudWatch 메트릭 데이터
- **추가 메트릭**: FreeableMemory, FreeStorageSpace

#### 권장 개선 방안
1. **성능 분석**: CPU, 메모리, I/O 등 종합적 성능 지표 분석
2. **점진적 조정**: 단계적 인스턴스 크기 조정 및 성능 모니터링
3. **예약 인스턴스**: 안정적인 워크로드에 대한 비용 절감
4. **읽기 전용 복제본**: 읽기 워크로드 분산을 통한 성능 개선

## 검사 항목별 심각도 분포

### 총 검사 항목: 5개

### HIGH (높음) - 즉시 조치 필요 (3개)
- 백업 보존 기간 검사
- 암호화 설정 검사
- 공개 액세스 설정 검사

### MEDIUM (중간) - 계획적 개선 필요 (2개)
- 다중 AZ 구성 검사
- 인스턴스 크기 최적화 검사