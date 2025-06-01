"""
수집 결과 생성을 위한 유틸리티 함수 모듈
"""

from typing import Dict, List, Any, Optional

# 수집 결과 상태 상수
STATUS_SUCCESS = 'success'
STATUS_WARNING = 'warning'
STATUS_ERROR = 'error'

def create_collection_result(status: str, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    표준화된 수집 결과를 생성합니다.
    
    Args:
        status: 수집 상태 (success, warning, error)
        message: 수집 결과 메시지
        data: 수집 결과 데이터 (선택 사항)
        
    Returns:
        Dict[str, Any]: 표준화된 수집 결과
    """
    result = {
        'status': status,
        'message': message
    }
    
    if data:
        result['data'] = data
    
    return result

def create_error_result(message: str) -> Dict[str, Any]:
    """
    오류 결과를 생성합니다.
    
    Args:
        message: 오류 메시지
        
    Returns:
        Dict[str, Any]: 오류 결과
    """
    return create_collection_result(
        status=STATUS_ERROR,
        message=message
    )

def create_success_result(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    성공 결과를 생성합니다.
    
    Args:
        message: 성공 메시지
        data: 수집 결과 데이터 (선택 사항)
        
    Returns:
        Dict[str, Any]: 성공 결과
    """
    return create_collection_result(
        status=STATUS_SUCCESS,
        message=message,
        data=data
    )