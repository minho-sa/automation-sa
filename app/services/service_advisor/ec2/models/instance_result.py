"""
EC2 인스턴스 검사 결과 모델
"""
from dataclasses import dataclass
from typing import Any, Dict, Union
from app.services.service_advisor.common.check_result import ResourceResult

@dataclass
class InstanceResult(ResourceResult):
    """EC2 인스턴스 검사 결과 모델"""
    instance_name: str
    instance_type: str
    avg_cpu: Union[float, str]
    max_cpu: Union[float, str]
    
    @classmethod
    def create(cls, instance_id: str, status: str, advice: str, status_text: str, **kwargs) -> 'InstanceResult':
        """
        인스턴스 결과 객체를 생성합니다.
        
        Args:
            instance_id: 인스턴스 ID
            status: 상태 코드
            advice: 권장 사항
            status_text: 상태 텍스트
            **kwargs: 추가 필드
            
        Returns:
            InstanceResult 객체
        """
        return cls(
            id=instance_id,
            status=status,
            advice=advice,
            status_text=status_text,
            instance_name=kwargs.get('instance_name', 'N/A'),
            instance_type=kwargs.get('instance_type', 'N/A'),
            avg_cpu=kwargs.get('avg_cpu', 'N/A'),
            max_cpu=kwargs.get('max_cpu', 'N/A')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        결과 객체를 딕셔너리로 변환합니다.
        
        Returns:
            Dict[str, Any]: 결과 딕셔너리
        """
        result = super().to_dict()
        return result