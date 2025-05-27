from abc import ABC, abstractmethod
import boto3
from typing import Dict, List, Any

class BaseAdvisor(ABC):
    """
    서비스 어드바이저의 기본 클래스입니다.
    모든 서비스별 어드바이저는 이 클래스를 상속받아야 합니다.
    """
    
    def __init__(self):
        """어드바이저 초기화"""
        self.checks = {}
        self._register_checks()
    
    @abstractmethod
    def _register_checks(self) -> None:
        """
        사용 가능한 검사 항목을 등록합니다.
        각 서비스 어드바이저에서 구현해야 합니다.
        """
        pass
    
    def get_available_checks(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 모든 검사 항목 목록을 반환합니다.
        
        Returns:
            List[Dict[str, Any]]: 검사 항목 목록
        """
        return [
            {
                'id': check_id,
                'name': check_info['name'],
                'description': check_info['description'],
                'category': check_info.get('category', '일반'),
                'severity': check_info.get('severity', 'medium')
            }
            for check_id, check_info in self.checks.items()
        ]
    
    def run_check(self, check_id: str) -> Dict[str, Any]:
        """
        특정 검사를 실행합니다.
        
        Args:
            check_id (str): 실행할 검사의 ID
            
        Returns:
            Dict[str, Any]: 검사 결과
            
        Raises:
            ValueError: 존재하지 않는 검사 ID가 제공된 경우
        """
        if check_id not in self.checks:
            raise ValueError(f"검사 ID '{check_id}'를 찾을 수 없습니다.")
        
        check_info = self.checks[check_id]
        check_func = check_info['function']
        
        try:
            result = check_func()
            return {
                'id': check_id,
                'name': check_info['name'],
                'description': check_info['description'],
                'category': check_info.get('category', '일반'),
                'severity': check_info.get('severity', 'medium'),
                'status': result.get('status', 'unknown'),
                'data': result.get('data', {}),
                'recommendations': result.get('recommendations', []),
                'message': result.get('message', '')
            }
        except Exception as e:
            return {
                'id': check_id,
                'name': check_info['name'],
                'description': check_info['description'],
                'status': 'error',
                'message': f"검사 실행 중 오류가 발생했습니다: {str(e)}"
            }
    
    def register_check(self, check_id: str, name: str, description: str, 
                      function, category: str = '일반', severity: str = 'medium') -> None:
        """
        새로운 검사 항목을 등록합니다.
        
        Args:
            check_id (str): 검사 ID
            name (str): 검사 이름
            description (str): 검사 설명
            function (callable): 검사를 수행할 함수
            category (str, optional): 검사 카테고리. 기본값은 '일반'
            severity (str, optional): 검사 심각도. 기본값은 'medium'
        """
        self.checks[check_id] = {
            'name': name,
            'description': description,
            'function': function,
            'category': category,
            'severity': severity
        }