from typing import Dict, List, Any, Callable, Optional
import logging
import boto3

class BaseAdvisor:
    """
    모든 서비스 어드바이저의 기본 클래스입니다.
    각 서비스별 어드바이저는 이 클래스를 상속받아 구현합니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        어드바이저 초기화 및 검사 항목 등록
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        self.checks = {}
        self.logger = logging.getLogger(__name__)
        self.session = session
        self._register_checks()
    
    def _register_checks(self) -> None:
        """
        서비스별 검사 항목을 등록하는 메서드.
        각 서비스 어드바이저에서 오버라이드해야 합니다.
        """
        pass
    
    def register_check(self, check_id: str, name: str, description: str, 
                      function: Callable, category: str, severity: str) -> None:
        """
        검사 항목을 등록합니다.
        
        Args:
            check_id: 검사 항목 ID
            name: 검사 항목 이름
            description: 검사 항목 설명
            function: 검사 실행 함수
            category: 검사 카테고리 (보안, 비용 최적화 등)
            severity: 심각도 (high, medium, low)
        """
        self.checks[check_id] = {
            'id': check_id,
            'name': name,
            'description': description,
            'function': function,
            'category': category,
            'severity': severity
        }
        self.logger.info(f"검사 항목 등록: {check_id} ({name})")
    
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
    
    def run_check(self, check_id: str, role_arn: str = None) -> Dict[str, Any]:
        """
        특정 검사를 실행합니다.
        
        Args:
            check_id: 실행할 검사 항목 ID
            role_arn: AWS 자격증명용 Role ARN (선택 사항)
            
        Returns:
            Dict[str, Any]: 검사 결과
            
        Raises:
            ValueError: 존재하지 않는 검사 항목 ID인 경우
        """
        if check_id not in self.checks:
            raise ValueError(f"존재하지 않는 검사 항목 ID: {check_id}")
        
        check_info = self.checks[check_id]
        self.logger.info(f"검사 실행: {check_id} ({check_info['name']})")
        
        try:
            # 사용자 인증 정보 로깅
            if role_arn:
                self.logger.info(f"Role ARN {role_arn}을 사용하여 검사 실행")
            
            # 검사 실행
            result = check_info['function']()
            
            # 검사 ID 추가
            result['id'] = check_id
            return result
        except Exception as e:
            self.logger.error(f"검사 실행 중 오류 발생: {check_id} - {str(e)}")
            return {
                'id': check_id,
                'status': 'error',
                'message': f'검사 실행 중 오류가 발생했습니다: {str(e)}'
            }