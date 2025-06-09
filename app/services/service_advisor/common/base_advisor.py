"""
모든 서비스 어드바이저의 기본 클래스
"""
import boto3
from typing import Dict, List, Any, Optional
import logging
from config import Config

class BaseAdvisor:
    """
    모든 서비스 어드바이저의 기본 클래스
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        기본 어드바이저 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        self.session = session or boto3.Session()
        self.logger = logging.getLogger(__name__)
        self.checks = {}
        self._register_checks()
    
    def _register_checks(self) -> None:
        """
        서비스별 검사 항목을 등록합니다.
        하위 클래스에서 구현해야 합니다.
        """
        pass
    
    def register_check(self, check_id, name, description, function, category, severity):
        """
        검사 항목을 등록합니다.
        
        Args:
            check_id: 검사 ID
            name: 검사 이름
            description: 검사 설명
            function: 검사 실행 함수
            category: 검사 카테고리
            severity: 심각도
        """
        self.checks[check_id] = {
            'id': check_id,
            'name': name,
            'description': description,
            'function': function,
            'category': category,
            'severity': severity
        }
    
    def get_available_checks(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 검사 항목 목록을 반환합니다.
        
        Returns:
            List[Dict[str, Any]]: 검사 항목 목록
        """
        return [
            {
                'id': check_id,
                'name': check_info['name'],
                'description': check_info['description'],
                'category': check_info['category'],
                'severity': check_info['severity']
            }
            for check_id, check_info in self.checks.items()
        ]
    
    def run_check(self, check_id, role_arn=None) -> Dict[str, Any]:
        """
        특정 검사를 실행합니다.
        
        Args:
            check_id: 검사 ID
            role_arn: AWS 역할 ARN (선택 사항)
            
        Returns:
            Dict[str, Any]: 검사 결과
        """
        if check_id not in self.checks:
            return {
                'status': 'error',
                'message': f'검사 항목을 찾을 수 없습니다: {check_id}',
                'resources': [],
                'recommendations': []
            }
        
        check_info = self.checks[check_id]
        check_function = check_info.get('function')
        
        try:
            result = check_function(role_arn=role_arn)
            result['id'] = check_id
            return result
        except Exception as e:
            self.logger.error(f"검사 실행 중 오류 발생: {str(e)}")
            return {
                'status': 'error',
                'message': f'검사 실행 중 오류가 발생했습니다: {str(e)}',
                'resources': [],
                'recommendations': []
            }
    
    def collect_data(self) -> Dict[str, Any]:
        """
        AWS에서 필요한 데이터를 수집합니다.
        하위 클래스에서 구현해야 합니다.
        
        Returns:
            Dict[str, Any]: 수집된 데이터
        """
        raise NotImplementedError("하위 클래스에서 구현해야 합니다.")
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        수집된 데이터를 분석하여 결과를 생성합니다.
        하위 클래스에서 구현해야 합니다.
        
        Args:
            collected_data: 수집된 데이터
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        raise NotImplementedError("하위 클래스에서 구현해야 합니다.")
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        분석 결과를 바탕으로 권장사항을 생성합니다.
        하위 클래스에서 구현해야 합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            List[str]: 권장사항 목록
        """
        raise NotImplementedError("하위 클래스에서 구현해야 합니다.")
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """
        분석 결과를 바탕으로 메시지를 생성합니다.
        하위 클래스에서 구현해야 합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            str: 결과 메시지
        """
        raise NotImplementedError("하위 클래스에서 구현해야 합니다.")