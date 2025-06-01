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
    
    # UI에 필요한 CPU 메트릭 정보만 저장
    cpu_utilization: Optional[float] = None  # 현재 CPU 사용률
    cpu_trend: List[float] = field(default_factory=list)  # 최근 CPU 사용률 추세 (UI 표시용)
    
    # UI에 필요한 네트워크 메트릭 정보만 저장
    network_in: Optional[float] = None  # 네트워크 인바운드 (MB)
    network_out: Optional[float] = None  # 네트워크 아웃바운드 (MB)

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