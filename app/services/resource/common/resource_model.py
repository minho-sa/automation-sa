from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

@dataclass
class ResourceModel:
    """
    모든 AWS 리소스 모델의 기본 클래스입니다.
    """
    id: str
    region: str
    tags: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        리소스 모델을 딕셔너리로 변환합니다.
        
        Returns:
            Dict[str, Any]: 리소스 데이터 딕셔너리
        """
        return asdict(self)

@dataclass
class EC2Instance(ResourceModel):
    """
    EC2 인스턴스 리소스 모델
    """
    type: str = ""
    state: str = ""
    az: str = ""
    launch_time: Optional[datetime] = None
    state_transition_time: Optional[datetime] = None
    security_groups: List[Dict[str, Any]] = field(default_factory=list)
    volumes: List[Dict[str, Any]] = field(default_factory=list)
    
    # 인스턴스 상세 정보
    architecture: str = ""
    hypervisor: str = ""
    root_device_type: str = ""
    root_device_name: str = ""
    virtualization_type: str = ""
    network_interfaces: List[Dict[str, Any]] = field(default_factory=list)
    
    # UI에 필요한 CPU 메트릭 정보
    cpu_utilization: Optional[float] = None  # 현재 CPU 사용률
    cpu_max: Optional[float] = None  # 최대 CPU 사용률
    cpu_min: Optional[float] = None  # 최소 CPU 사용률
    cpu_trend: List[Dict[str, Any]] = field(default_factory=list)  # CPU 사용률 추세
    
    # 메모리 메트릭 정보 (CloudWatch 에이전트 필요)
    memory_utilization: Optional[float] = None  # 현재 메모리 사용률
    
    # 디스크 메트릭 정보 (CloudWatch 에이전트 필요)
    disk_utilization: Optional[float] = None  # 현재 디스크 사용률
    
    # 네트워크 메트릭 정보
    network_in: Optional[float] = None  # 네트워크 인바운드 (MB)
    network_out: Optional[float] = None  # 네트워크 아웃바운드 (MB)
    network_in_sum: Optional[float] = None  # 네트워크 인바운드 합계 (MB)
    network_out_sum: Optional[float] = None  # 네트워크 아웃바운드 합계 (MB)
    network_trend: List[Dict[str, Any]] = field(default_factory=list)  # 네트워크 추세

@dataclass
class S3Bucket(ResourceModel):
    """
    S3 버킷 리소스 모델
    """
    name: str = ""
    creation_date: Optional[datetime] = None
    versioning_enabled: bool = False
    public_access: bool = False
    encryption_enabled: bool = False
    lifecycle_rules: List[Dict[str, Any]] = field(default_factory=list)
    size_bytes: Optional[int] = None
    object_count: Optional[int] = None
    
    # 버킷 정책 정보
    policy: Optional[Dict[str, Any]] = None
    
    # 버킷 CORS 설정
    cors_rules: List[Dict[str, Any]] = field(default_factory=list)
    
    # 버킷 웹사이트 설정
    website_enabled: bool = False
    website_config: Optional[Dict[str, Any]] = None
    
    # 버킷 로깅 설정
    logging_enabled: bool = False
    logging_target_bucket: str = ""
    logging_target_prefix: str = ""
    
    # 스토리지 클래스별 객체 분포
    storage_class_distribution: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 액세스 포인트
    access_points: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class RDSInstance(ResourceModel):
    """
    RDS 인스턴스 리소스 모델
    """
    db_instance_identifier: str = ""
    db_instance_class: str = ""
    engine: str = ""
    engine_version: str = ""
    status: str = ""
    az: str = ""
    multi_az: bool = False
    storage_type: str = ""
    allocated_storage: int = 0
    endpoint: Optional[Dict[str, Any]] = None
    create_time: Optional[datetime] = None
    
    # 성능 지표
    cpu_utilization: Optional[float] = None
    db_connections: Optional[int] = None
    free_storage_space: Optional[float] = None
    read_iops: Optional[float] = None
    write_iops: Optional[float] = None
    
    # 백업 설정
    backup_retention_period: int = 0
    preferred_backup_window: str = ""
    latest_backup_time: Optional[datetime] = None
    
    # 보안 설정
    publicly_accessible: bool = False
    vpc_security_groups: List[Dict[str, Any]] = field(default_factory=list)
    parameter_groups: List[Dict[str, Any]] = field(default_factory=list)
    
    # 모니터링 설정
    enhanced_monitoring: bool = False
    monitoring_interval: int = 0
    
    # 성능 인사이트
    performance_insights_enabled: bool = False

@dataclass
class LambdaFunction(ResourceModel):
    """
    Lambda 함수 리소스 모델
    """
    function_name: str = ""
    runtime: str = ""
    handler: str = ""
    code_size: int = 0
    description: str = ""
    timeout: int = 0
    memory_size: int = 0
    last_modified: Optional[datetime] = None
    
    # 환경 변수
    environment_variables: Dict[str, str] = field(default_factory=dict)
    
    # VPC 설정
    vpc_config: Optional[Dict[str, Any]] = None
    
    # 트리거 및 대상
    event_sources: List[Dict[str, Any]] = field(default_factory=list)
    destinations: Dict[str, str] = field(default_factory=dict)
    
    # 성능 지표
    invocations: Optional[int] = None
    errors: Optional[int] = None
    throttles: Optional[int] = None
    duration_avg: Optional[float] = None
    duration_max: Optional[float] = None
    
    # 동시성 설정
    reserved_concurrency: Optional[int] = None
    provisioned_concurrency: Optional[int] = None

@dataclass
class IAMUser(ResourceModel):
    """
    IAM 사용자 리소스 모델
    """
    user_name: str = ""
    path: str = ""
    create_date: Optional[datetime] = None
    password_last_used: Optional[datetime] = None
    
    # 액세스 키
    access_keys: List[Dict[str, Any]] = field(default_factory=list)
    
    # 그룹 멤버십
    groups: List[str] = field(default_factory=list)
    
    # 정책
    attached_policies: List[Dict[str, Any]] = field(default_factory=list)
    inline_policies: List[Dict[str, Any]] = field(default_factory=list)
    
    # MFA 디바이스
    mfa_devices: List[Dict[str, Any]] = field(default_factory=list)
    
    # 보안 인증 정보
    has_console_password: bool = False
    has_active_access_keys: bool = False
    has_signing_certificates: bool = False
    has_ssh_public_keys: bool = False

@dataclass
class IAMRole(ResourceModel):
    """
    IAM 역할 리소스 모델
    """
    role_name: str = ""
    path: str = ""
    create_date: Optional[datetime] = None
    
    # 신뢰 관계
    assume_role_policy: Dict[str, Any] = field(default_factory=dict)
    
    # 정책
    attached_policies: List[Dict[str, Any]] = field(default_factory=list)
    inline_policies: List[Dict[str, Any]] = field(default_factory=list)
    
    # 최대 세션 기간
    max_session_duration: int = 3600