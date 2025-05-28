from typing import Dict, List, Optional, Any
import logging
from app.services.service_advisor.ec2.ec2_advisor import EC2Advisor

class ServiceAdvisorFactory:
    """
    서비스 어드바이저 팩토리 클래스.
    서비스 이름에 따라 적절한 어드바이저 객체를 생성합니다.
    """
    
    def __init__(self):
        """
        팩토리 초기화 및 서비스 매핑 설정
        """
        self.logger = logging.getLogger(__name__)
        self.service_mapping = {
            'ec2': EC2Advisor
            # 다른 서비스 어드바이저 클래스 추가
            # 's3': S3Advisor,
        }
    
    def get_advisor(self, service_name: str) -> Optional[Any]:
        """
        서비스 이름에 맞는 어드바이저 객체를 반환합니다.
        
        Args:
            service_name: 서비스 이름 (ec2, lambda 등)
            
        Returns:
            Optional[Any]: 서비스 어드바이저 객체 또는 None
        """
        if service_name not in self.service_mapping:
            self.logger.warning(f"지원하지 않는 서비스: {service_name}")
            return None
        
        advisor_class = self.service_mapping[service_name]
        self.logger.info(f"어드바이저 생성: {service_name} ({advisor_class.__name__})")
        return advisor_class()
    
    def get_available_services(self) -> List[Dict[str, str]]:
        """
        사용 가능한 서비스 목록을 반환합니다.
        
        Returns:
            List[Dict[str, str]]: 서비스 목록
        """
        services = []
        
        for service_name in self.service_mapping.keys():
            service_info = {
                'id': service_name,
                'name': self._get_service_display_name(service_name)
            }
            services.append(service_info)
        
        return services
    
    def _get_service_display_name(self, service_name: str) -> str:
        """
        서비스 ID에 해당하는 표시 이름을 반환합니다.
        
        Args:
            service_name: 서비스 ID
            
        Returns:
            str: 서비스 표시 이름
        """
        service_display_names = {
            'ec2': 'Amazon EC2',
            'lambda': 'AWS Lambda',
            's3': 'Amazon S3',
            'rds': 'Amazon RDS',
            'dynamodb': 'Amazon DynamoDB'
        }
        
        return service_display_names.get(service_name, service_name.upper())