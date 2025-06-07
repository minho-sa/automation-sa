"""
서비스 어드바이저 코드 예제
"""

# 통일된 검사 결과 구조 생성 함수
def create_unified_check_result(status, message, resources, recommendations, check_id):
    """
    통일된 검사 결과 객체를 생성합니다.
    
    Args:
        status: 검사 상태 ('ok', 'warning', 'error', 'info' 중 하나)
        message: 검사 결과 요약 메시지
        resources: 리소스 결과 객체 목록
        recommendations: 권장 사항 목록
        check_id: 검사 항목 ID
        
    Returns:
        통일된 검사 결과 객체
    """
    return {
        'id': check_id,
        'status': status,
        'message': message,
        'resources': resources,
        'recommendations': recommendations,
        'problem_count': len([r for r in resources if r['status'] != 'pass']),
        'total_count': len(resources)
    }

# 리소스 결과 생성 함수
def create_resource_result(resource_id, resource_name, status, status_text, advice):
    """
    통일된 리소스 결과 객체를 생성합니다.
    
    Args:
        resource_id: 리소스 ID
        resource_name: 리소스 이름
        status: 리소스 상태 ('pass', 'fail', 'warning', 'unknown' 중 하나)
        status_text: 상태 설명 텍스트
        advice: 리소스 상태에 대한 설명
        
    Returns:
        통일된 리소스 결과 객체
    """
    return {
        'id': resource_id,
        'name': resource_name,
        'status': status,
        'status_text': status_text,
        'advice': advice
    }

# EC2 인스턴스 타입 검사 예제
def instance_type_check_example():
    # 리소스별 설명 예제
    low_cpu_advice = "CPU 사용률이 낮습니다(평균: 5.2%, 최대: 15.8%). 이 인스턴스는 과다 프로비저닝되어 있습니다."
    high_cpu_advice = "CPU 사용률이 높습니다(평균: 85.3%, 최대: 95.1%). 이 인스턴스는 리소스 제약을 받고 있습니다."
    optimal_cpu_advice = "CPU 사용률(평균: 45.7%, 최대: 78.2%)이 적절한 범위(10-80%) 내에 있습니다."
    no_data_advice = "이 인스턴스에 대한 충분한 CloudWatch 메트릭 데이터가 없습니다. 최근에 시작되었거나 메트릭 수집이 활성화되지 않았을 수 있습니다."
    error_advice = "이 인스턴스의 메트릭 데이터를 가져오는 중 오류가 발생했습니다. 권한 문제 또는 API 호출 실패가 원인일 수 있습니다."
    
    # 리소스 결과 생성
    resources = [
        create_resource_result("i-1234abcd", "web-server-1", "fail", "최적화 필요", low_cpu_advice),
        create_resource_result("i-5678efgh", "web-server-2", "fail", "최적화 필요", high_cpu_advice),
        create_resource_result("i-90abcdef", "app-server-1", "pass", "최적화됨", optimal_cpu_advice),
        create_resource_result("i-ghij1234", "db-server-1", "unknown", "데이터 부족", no_data_advice),
        create_resource_result("i-klmn5678", "cache-server-1", "error", "오류", error_advice)
    ]
    
    # 검사 권장사항
    recommendations = [
        "CPU 사용률이 10% 미만인 인스턴스는 더 작은 인스턴스 타입으로 변경하여 비용을 절감하세요.",
        "CPU 사용률이 80% 이상인 인스턴스는 더 큰 인스턴스 타입으로 변경하여 성능을 개선하세요.",
        "예약 인스턴스 또는 Savings Plans를 고려하여 비용을 절감하세요.",
        "인스턴스 크기 조정 시 CPU 외에도 메모리, 네트워크, 디스크 I/O 등 다른 성능 지표도 함께 고려하세요."
    ]
    
    # 검사 결과 생성
    result = create_unified_check_result(
        status="warning",
        message="5개 인스턴스 중 2개가 최적화가 필요합니다.",
        resources=resources,
        recommendations=recommendations,
        check_id="ec2-instance-type"
    )
    
    return result

# EC2 보안 그룹 검사 예제
def security_group_check_example():
    # 리소스별 설명 예제
    ssh_risk_advice = "이 보안 그룹은 SSH 포트(22)가 모든 IP에 개방되어 있어 무차별 대입 공격에 취약합니다."
    rdp_risk_advice = "이 보안 그룹은 RDP 포트(3389)가 모든 IP에 개방되어 있어 보안 위험이 높습니다."
    db_risk_advice = "이 보안 그룹은 데이터베이스 포트가 인터넷에 직접 노출되어 있어 데이터 유출 위험이 있습니다."
    all_ports_risk_advice = "이 보안 그룹은 모든 포트(0-65535)가 개방되어 있어 심각한 보안 위험이 있습니다."
    safe_advice = "이 보안 그룹은 모든 인바운드 규칙이 적절하게 구성되어 있습니다."
    
    # 리소스 결과 생성
    resources = [
        create_resource_result("sg-1234abcd", "web-servers", "fail", "위험", ssh_risk_advice),
        create_resource_result("sg-5678efgh", "admin-servers", "fail", "위험", rdp_risk_advice),
        create_resource_result("sg-90abcdef", "db-servers", "fail", "위험", db_risk_advice),
        create_resource_result("sg-ghij1234", "test-servers", "pass", "안전", safe_advice),
        create_resource_result("sg-klmn5678", "internal-services", "pass", "안전", safe_advice)
    ]
    
    # 검사 권장사항
    recommendations = [
        "SSH(22) 접속은 특정 IP 주소로 제한하거나 VPN/배스천 호스트를 통해 접근하도록 설정하세요.",
        "RDP(3389) 접속은 특정 IP 주소로 제한하고 가능하면 VPN을 통해 접근하도록 설정하세요.",
        "데이터베이스 포트는 인터넷에 직접 노출하지 말고 내부 네트워크에서만 접근 가능하도록 설정하세요.",
        "모든 포트를 개방하는 규칙은 제거하고 필요한 포트만 선택적으로 개방하세요.",
        "보안 그룹 규칙을 정기적으로 검토하고 불필요한 규칙은 제거하세요."
    ]
    
    # 검사 결과 생성
    result = create_unified_check_result(
        status="warning",
        message="5개의 보안 그룹 중 3개에서 잠재적인 보안 위험이 발견되었습니다.",
        resources=resources,
        recommendations=recommendations,
        check_id="ec2-security-group"
    )
    
    return result

# 실제 구현 예시 (인스턴스 타입 검사)
def analyze_instance_cpu_usage(instance_id, instance_name, avg_cpu, max_cpu):
    """
    인스턴스 CPU 사용률을 분석하여 결과를 생성합니다.
    
    Args:
        instance_id: 인스턴스 ID
        instance_name: 인스턴스 이름
        avg_cpu: 평균 CPU 사용률
        max_cpu: 최대 CPU 사용률
        
    Returns:
        리소스 결과 객체
    """
    if avg_cpu < 10 and max_cpu < 40:
        status = "fail"
        status_text = "최적화 필요"
        advice = f"CPU 사용률이 낮습니다(평균: {avg_cpu}%, 최대: {max_cpu}%). 이 인스턴스는 과다 프로비저닝되어 있습니다."
    elif avg_cpu > 80 or max_cpu > 90:
        status = "fail"
        status_text = "최적화 필요"
        advice = f"CPU 사용률이 높습니다(평균: {avg_cpu}%, 최대: {max_cpu}%). 이 인스턴스는 리소스 제약을 받고 있습니다."
    else:
        status = "pass"
        status_text = "최적화됨"
        advice = f"CPU 사용률(평균: {avg_cpu}%, 최대: {max_cpu}%)이 적절한 범위(10-80%) 내에 있습니다."
    
    return create_resource_result(
        resource_id=instance_id,
        resource_name=instance_name,
        status=status,
        status_text=status_text,
        advice=advice
    )

# 실제 구현 예시 (보안 그룹 검사)
def analyze_security_group_rules(sg_id, sg_name, risky_rules):
    """
    보안 그룹 규칙을 분석하여 결과를 생성합니다.
    
    Args:
        sg_id: 보안 그룹 ID
        sg_name: 보안 그룹 이름
        risky_rules: 위험한 규칙 목록
        
    Returns:
        리소스 결과 객체
    """
    if not risky_rules:
        status = "pass"
        status_text = "안전"
        advice = "이 보안 그룹은 모든 인바운드 규칙이 적절하게 구성되어 있습니다."
        return create_resource_result(
            resource_id=sg_id,
            resource_name=sg_name,
            status=status,
            status_text=status_text,
            advice=advice
        )
    
    status = "fail"
    status_text = "위험"
    
    # 위험 유형 분석
    advice_items = []
    
    # SSH 위험 확인
    if any(rule.get('port') == 22 for rule in risky_rules):
        advice_items.append("이 보안 그룹은 SSH 포트(22)가 모든 IP에 개방되어 있어 무차별 대입 공격에 취약합니다.")
    
    # RDP 위험 확인
    if any(rule.get('port') == 3389 for rule in risky_rules):
        advice_items.append("이 보안 그룹은 RDP 포트(3389)가 모든 IP에 개방되어 있어 보안 위험이 높습니다.")
    
    # DB 위험 확인
    if any(rule.get('port') in [3306, 5432] for rule in risky_rules):
        advice_items.append("이 보안 그룹은 데이터베이스 포트가 인터넷에 직접 노출되어 있어 데이터 유출 위험이 있습니다.")
    
    # 모든 포트 위험 확인
    if any(rule.get('all_ports', False) for rule in risky_rules):
        advice_items.append("이 보안 그룹은 모든 포트(0-65535)가 개방되어 있어 심각한 보안 위험이 있습니다.")
    
    advice = " ".join(advice_items)
    
    return create_resource_result(
        resource_id=sg_id,
        resource_name=sg_name,
        status=status,
        status_text=status_text,
        advice=advice
    )

# 검사 권장사항 생성 함수 예시
def get_instance_type_recommendations():
    """인스턴스 타입 검사 권장사항을 반환합니다."""
    return [
        "CPU 사용률이 10% 미만인 인스턴스는 더 작은 인스턴스 타입으로 변경하여 비용을 절감하세요.",
        "CPU 사용률이 80% 이상인 인스턴스는 더 큰 인스턴스 타입으로 변경하여 성능을 개선하세요.",
        "예약 인스턴스 또는 Savings Plans를 고려하여 비용을 절감하세요.",
        "인스턴스 크기 조정 시 CPU 외에도 메모리, 네트워크, 디스크 I/O 등 다른 성능 지표도 함께 고려하세요."
    ]

def get_security_group_recommendations():
    """보안 그룹 검사 권장사항을 반환합니다."""
    return [
        "SSH(22) 접속은 특정 IP 주소로 제한하거나 VPN/배스천 호스트를 통해 접근하도록 설정하세요.",
        "RDP(3389) 접속은 특정 IP 주소로 제한하고 가능하면 VPN을 통해 접근하도록 설정하세요.",
        "데이터베이스 포트는 인터넷에 직접 노출하지 말고 내부 네트워크에서만 접근 가능하도록 설정하세요.",
        "모든 포트를 개방하는 규칙은 제거하고 필요한 포트만 선택적으로 개방하세요.",
        "보안 그룹 규칙을 정기적으로 검토하고 불필요한 규칙은 제거하세요."
    ]