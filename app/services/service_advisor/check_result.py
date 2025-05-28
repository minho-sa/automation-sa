"""
서비스 어드바이저 검사 결과 표준화 모듈
모든 검사 항목에서 일관된 결과 형식을 사용하기 위한 유틸리티 함수를 제공합니다.
"""
from typing import Dict, List, Any, Optional, Union

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

def create_resource_result(
    resource_id: str,
    status: str,
    advice: str,
    status_text: str,
    **additional_fields
) -> Dict[str, Any]:
    """
    표준화된 리소스 결과 객체를 생성합니다.
    
    Args:
        resource_id: 리소스 ID
        status: 리소스 상태 ('pass', 'fail', 'warning', 'unknown' 중 하나)
        advice: 리소스에 대한 권장 사항 (필수)
        status_text: 상태 텍스트 (필수)
        additional_fields: 추가 필드 (리소스 유형에 따라 다름)
        
    Returns:
        표준화된 리소스 결과 객체
    """
    result = {
        'id': resource_id,
        'status': status,
        'advice': advice,
        'status_text': status_text
    }
    
    # 추가 필드 병합
    result.update(additional_fields)
    
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