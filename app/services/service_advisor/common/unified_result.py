"""
서비스 어드바이저 통일된 검사 결과 모듈
모든 검사 항목에서 일관된 결과 형식을 사용하기 위한 유틸리티 함수를 제공합니다.
"""
from typing import Dict, List, Any, Optional

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

def create_unified_check_result(
    status: str,
    message: str,
    resources: List[Dict[str, Any]],
    recommendations: List[str],
    check_id: str
) -> Dict[str, Any]:
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
        'problem_count': len([r for r in resources if r['status'] != RESOURCE_STATUS_PASS]),
        'total_count': len(resources)
    }

def create_resource_result(
    resource_id: str,
    resource_name: str,
    status: str,
    status_text: str,
    advice: str
) -> Dict[str, Any]:
    """
    통일된 리소스 결과 객체를 생성합니다.
    
    Args:
        resource_id: 리소스 ID
        resource_name: 리소스 이름
        status: 리소스 상태 ('pass', 'fail', 'warning', 'unknown' 중 하나)
        status_text: 상태 설명 텍스트
        advice: 리소스별 권장 사항
        
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

def create_error_result(error_message: str) -> Dict[str, Any]:
    """
    오류 결과 객체를 생성합니다.
    
    Args:
        error_message: 오류 메시지
        
    Returns:
        오류 결과 객체
    """
    return {
        'status': STATUS_ERROR,
        'message': error_message,
        'resources': [],
        'recommendations': [],
        'problem_count': 0,
        'total_count': 0
    }