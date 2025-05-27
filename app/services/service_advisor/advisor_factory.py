from typing import Dict, List, Optional, Any
from app.services.service_advisor.ec2.ec2_advisor import EC2Advisor

class ServiceAdvisorFactory:
    """
    서비스 어드바이저 팩토리 클래스입니다.
    서비스 이름에 따라 적절한 어드바이저 인스턴스를 생성합니다.
    """
    
    def __init__(self):
        """팩토리 초기화"""
        self.advisors = {
            'ec2': EC2Advisor
        }
    
    def get_advisor(self, service_name: str):
        """
        서비스 이름에 해당하는 어드바이저 인스턴스를 반환합니다.
        
        Args:
            service_name (str): 서비스 이름
            
        Returns:
            BaseAdvisor: 서비스 어드바이저 인스턴스 또는 None
        """
        advisor_class = self.advisors.get(service_name.lower())
        if advisor_class:
            return advisor_class()
        return None
    
    def get_available_services(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 모든 서비스 목록을 반환합니다.
        
        Returns:
            List[Dict[str, Any]]: 서비스 목록
        """
        services = [
            {
                'id': 'ec2',
                'name': 'EC2',
                'description': 'Amazon Elastic Compute Cloud',
                'icon': 'fa-server'
            }
            # 추후 다른 서비스 추가 가능
        ]
        return services