# IAM 서비스 어드바이저 체크 항목

## 개요
IAM 서비스 어드바이저는 AWS Identity and Access Management(IAM)의 구성, 보안 및 모범 사례 준수 여부를 검사하여 개선 방안을 제안합니다.

## 체크 항목

### 액세스 키 교체 검사
- **설명**: IAM 액세스 키 교체 상태를 검사하고 오래된 액세스 키에 대한 교체 방안을 제안합니다.
- **검사 내용**:
  - 모든 IAM 사용자의 액세스 키 생성 날짜 확인
  - 90일 이상 교체되지 않은 액세스 키 식별 (경고)
  - 180일 이상 교체되지 않은 액세스 키 식별 (실패)
- **권장 사항**:
  - 액세스 키는 90일마다 교체
  - 프로그래밍 방식 액세스가 필요하지 않은 사용자에게는 액세스 키를 발급하지 않음
  - 오래된 액세스 키는 즉시 교체

### 암호 정책 검사
- **설명**: IAM 계정 암호 정책을 검사하고 보안 강화 방안을 제안합니다.
- **검사 내용**:
  - 암호 정책 설정 여부 확인
  - 최소 암호 길이 검사 (14자 이상 권장)
  - 암호 복잡성 요구사항 검사 (대문자, 소문자, 숫자, 특수 문자)
  - 암호 만료 설정 검사 (90일 이하 권장)
  - 암호 재사용 방지 설정 검사 (24개 이상 권장)
- **권장 사항**:
  - 강력한 암호 정책 설정
  - 최소 암호 길이를 14자 이상으로 설정
  - 대문자, 소문자, 숫자, 특수 문자 요구
  - 암호 재사용 방지
  - 최대 암호 사용 기간을 90일로 설정

### MFA 설정 검사
- **설명**: IAM 사용자의 MFA(다중 인증) 설정 상태를 검사하고 개선 방안을 제안합니다.
- **검사 내용**:
  - 콘솔 액세스 권한이 있는 사용자의 MFA 설정 여부 확인
  - 관리자 권한을 가진 사용자의 MFA 설정 여부 확인
  - 사용자 그룹 멤버십 및 권한 분석
- **권장 사항**:
  - 모든 IAM 사용자, 특히 관리자 권한이 있는 사용자에게 MFA 설정
  - 가상 MFA 디바이스, U2F 보안 키 또는 하드웨어 MFA 디바이스 사용

### 루트 계정 보안 검사
- **설명**: AWS 계정의 루트 사용자 보안 설정을 검사하고 개선 방안을 제안합니다.
- **검사 내용**:
  - 루트 계정 MFA 설정 여부 확인
  - 루트 계정 액세스 키 존재 여부 확인
- **권장 사항**:
  - 루트 계정에 MFA 즉시 설정
  - 루트 계정의 액세스 키 삭제
  - 루트 계정은 AWS 계정 생성 및 특정 관리 작업에만 사용
  - 루트 계정 이메일 주소와 연결된 이메일 계정에도 강력한 보안 조치 적용

### 비활성 사용자 검사
- **설명**: IAM 사용자의 활동 상태를 검사하고 비활성 사용자에 대한 개선 방안을 제안합니다.
- **검사 내용**:
  - 사용자의 마지막 활동 시간 확인 (콘솔 로그인, 액세스 키 사용)
  - 90일 이상 활동이 없는 사용자 식별 (경고)
  - 180일 이상 활동이 없는 사용자 식별 (실패)
  - 생성된 후 활동이 없는 사용자 식별
- **권장 사항**:
  - 장기간 비활성 상태인 사용자 계정 비활성화 또는 삭제
  - 정기적으로 비활성 사용자 검토
  - 사용자 계정 수명 주기 관리 정책 수립

### 기타 IAM 체크 항목
- **직접 연결된 정책**: 사용자에게 직접 연결된 정책 검사 및 그룹 기반 권한 관리 권장
- **과도한 권한**: 과도한 권한을 가진 사용자 또는 역할 식별
- **외부 신뢰 역할**: 외부 계정에 대한 신뢰 관계가 있는 역할 검사
- **루트 계정 액세스 키**: 루트 계정의 액세스 키 존재 여부 검사
- **서비스 연결 역할**: 서비스 연결 역할 사용 검사
- **미사용 자격 증명**: 장기간 사용되지 않은 자격 증명 식별