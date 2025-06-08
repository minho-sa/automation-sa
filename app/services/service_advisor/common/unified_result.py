"""
통일된 검사 결과 형식을 제공하는 유틸리티 모듈
"""
from typing import Dict, List, Any, Optional

# 상태 코드 정의
STATUS_OK = 'ok'
STATUS_WARNING = 'warning'
STATUS_ERROR = 'error'

# 리소스 상태 코드 정의
RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_FAIL = 'fail'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_UNKNOWN = 'unknown'

def create_unified_check_result(
    status: str,
    message: str,
    resources: List[Dict[str, Any]],
    recommendations: List[str],
    check_id: str = '',
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    통일된 형식의 검사 결과를 생성합니다.
    
    Args:
        status: 검사 상태 (ok, warning, error)
        message: 검사 결과 메시지
        resources: 리소스 결과 목록
        recommendations: 권장사항 목록
        check_id: 검사 ID (선택 사항)
        data: 추가 데이터 (선택 사항)
        
    Returns:
        Dict[str, Any]: 통일된 형식의 검사 결과
    """
    result = {
        'status': status,
        'message': message,
        'resources': resources,
        'recommendations': recommendations,
        'problem_count': len([r for r in resources if r['status'] == RESOURCE_STATUS_FAIL]),
        'total_count': len(resources)
    }
    
    if check_id:
        result['id'] = check_id
        
    if data:
        result['data'] = data
        
    return result

def create_resource_result(
    resource_id: str,
    resource_name: str = '',
    status: str = RESOURCE_STATUS_UNKNOWN,
    status_text: str = '',
    advice: str = '',
    **kwargs
) -> Dict[str, Any]:
    """
    통일된 형식의 리소스 결과를 생성합니다.
    
    Args:
        resource_id: 리소스 ID
        resource_name: 리소스 이름 (선택 사항)
        status: 리소스 상태 (pass, fail, warning, unknown)
        status_text: 상태 텍스트 (선택 사항)
        advice: 권장사항 (선택 사항)
        **kwargs: 추가 속성
        
    Returns:
        Dict[str, Any]: 통일된 형식의 리소스 결과
    """
    result = {
        'id': resource_id,
        'name': resource_name or resource_id,
        'status': status,
        'status_text': status_text,
        'advice': advice
    }
    
    # 추가 속성 추가
    for key, value in kwargs.items():
        result[key] = value
        
    return result

def create_error_result(error_message: str) -> Dict[str, Any]:
    """
    오류 결과를 생성합니다.
    
    Args:
        error_message: 오류 메시지
        
    Returns:
        Dict[str, Any]: 오류 결과
    """
    return {
        'status': STATUS_ERROR,
        'message': error_message,
        'resources': [],
        'recommendations': ['오류를 해결한 후 다시 시도하세요.'],
        'problem_count': 0,
        'total_count': 0
    }