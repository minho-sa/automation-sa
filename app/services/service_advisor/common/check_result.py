"""
서비스 어드바이저 검사 결과 표준화 모듈
모든 검사 항목에서 일관된 결과 형식을 사용하기 위한 유틸리티 함수를 제공합니다.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# 상태 상수 정의
STATUS_OK = 'ok'
STATUS_WARNING = 'warning'
STATUS_ERROR = 'error'
STATUS_INFO = 'info'

# 리소스 상태 상수 정의
RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_FAIL = 'fail'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_UNKNOWN = 'unknown'

@dataclass
class ResourceResult:
    """리소스 검사 결과의 기본 클래스"""
    id: str
    status: str
    advice: str
    status_text: str
    
    def to_dict(self) -> Dict[str, Any]:
        """데이터클래스를 딕셔너리로 변환"""
        return asdict(self)

def create_check_result(
    status: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    recommendations: Optional[List[str]] = None,
    check_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    표준화된 검사 결과 객체를 생성합니다.
    
    Args:
        status: 검사 상태 ('ok', 'warning', 'error', 'info' 중 하나)
        message: 검사 결과 메시지
        data: 검사 결과 데이터 (선택 사항)
        recommendations: 권장 사항 목록 (선택 사항)
        check_id: 검사 항목 ID (선택 사항)
        
    Returns:
        표준화된 검사 결과 객체
    """
    result = {
        'status': status,
        'message': message
    }
    
    if data is not None:
        result['data'] = data
    
    if recommendations is not None:
        result['recommendations'] = recommendations
    
    if check_id is not None:
        result['id'] = check_id
    
    return result

def create_error_result(error_message: str) -> Dict[str, str]:
    """
    오류 결과 객체를 생성합니다.
    
    Args:
        error_message: 오류 메시지
        
    Returns:
        오류 결과 객체
    """
    return {
        'status': STATUS_ERROR,
        'message': error_message
    }