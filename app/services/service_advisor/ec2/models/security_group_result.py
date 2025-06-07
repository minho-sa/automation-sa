"""
EC2 보안 그룹 검사 결과 모델
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any
from app.services.service_advisor.common.check_result import ResourceResult

@dataclass
class RiskyRule:
    """위험한 보안 그룹 규칙 모델"""
    cidr: str
    protocol: str
    port_range: str
    risk: str

@dataclass
class SecurityGroupResult(ResourceResult):
    """EC2 보안 그룹 검사 결과 모델"""
    sg_name: str
    vpc_id: str
    description: str
    risky_rules: List[RiskyRule] = field(default_factory=list)
    
    @property
    def risky_rules_count(self) -> int:
        """위험한 규칙 수를 반환합니다."""
        return len(self.risky_rules)
    
    @classmethod
    def create(cls, sg_id: str, status: str, advice: str, status_text: str, **kwargs) -> 'SecurityGroupResult':
        """
        보안 그룹 결과 객체를 생성합니다.
        
        Args:
            sg_id: 보안 그룹 ID
            status: 상태 코드
            advice: 권장 사항
            status_text: 상태 텍스트
            **kwargs: 추가 필드
            
        Returns:
            SecurityGroupResult 객체
        """
        risky_rules = []
        for rule in kwargs.get('risky_rules', []):
            risky_rules.append(RiskyRule(
                cidr=rule.get('cidr', ''),
                protocol=rule.get('protocol', ''),
                port_range=rule.get('port_range', ''),
                risk=rule.get('risk', '')
            ))
        
        return cls(
            id=sg_id,
            status=status,
            advice=advice,
            status_text=status_text,
            sg_name=kwargs.get('sg_name', 'N/A'),
            vpc_id=kwargs.get('vpc_id', 'N/A'),
            description=kwargs.get('description', ''),
            risky_rules=risky_rules
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        결과 객체를 딕셔너리로 변환합니다.
        
        Returns:
            Dict[str, Any]: 결과 딕셔너리
        """
        result = super().to_dict()
        result['risky_rules'] = [vars(rule) for rule in self.risky_rules]
        result['risky_rules_count'] = self.risky_rules_count
        return result