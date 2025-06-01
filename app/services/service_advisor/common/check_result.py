"""
검사 결과 생성을 위한 유틸리티 함수 모듈
"""

from typing import Dict, List, Any, Optional

# 검사 결과 상태 상수
STATUS_OK = 'ok'
STATUS_WARNING = 'warning'
STATUS_ERROR = 'error'

# 리소스 상태 상수
RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_FAIL = 'fail'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_UNKNOWN = 'unknown'

def create_check_result(status: str, message: str, data: Optional[Dict[str, Any]] = None, 
                       recommendations: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    표준화된 검사 결과를 생성합니다.
    
    Args:
        status: 검사 상태 (ok, warning, error)
        message: 검사 결과 메시지
        data: 검사 결과 데이터 (선택 사항)
        recommendations: 권장 사항 목록 (선택 사항)
        
    Returns:
        Dict[str, Any]: 표준화된 검사 결과
    """
    result = {
        'status': status,
        'message': message
    }
    
    if data:
        result['data'] = data
    
    if recommendations:
        result['recommendations'] = recommendations
    
    return result

def create_error_result(message: str) -> Dict[str, Any]:
    """
    오류 결과를 생성합니다.
    
    Args:
        message: 오류 메시지
        
    Returns:
        Dict[str, Any]: 오류 결과
    """
    return create_check_result(
        status=STATUS_ERROR,
        message=message,
        recommendations=['오류가 발생했습니다. 다시 시도하거나 관리자에게 문의하세요.']
    )

def create_resource_result(resource_id: str, status: str, advice: str, status_text: str, **kwargs) -> Dict[str, Any]:
    """
    리소스 검사 결과를 생성합니다.
    
    Args:
        resource_id: 리소스 ID
        status: 리소스 상태 (pass, fail, warning, unknown)
        advice: 권장 사항
        status_text: 상태 텍스트
        **kwargs: 추가 데이터
        
    Returns:
        Dict[str, Any]: 리소스 검사 결과
    """
    result = {
        'id': resource_id,
        'status': status,
        'advice': advice,
        'status_text': status_text
    }
    
    # 추가 데이터 병합
    result.update(kwargs)
    
    return result