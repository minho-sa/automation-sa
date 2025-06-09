from typing import Dict, Optional
import boto3
from app.services.resource.common.base_collector import BaseCollector
from app.services.resource.ec2_collector import EC2Collector
from app.services.resource.s3_collector import S3Collector
from config import Config

class CollectorFactory:
    """
    리소스 수집기 팩토리 클래스
    """
    
    # 서비스 이름과 수집기 클래스 매핑
    _collectors = {
        'ec2': EC2Collector,
        's3': S3Collector,
        # 다른 서비스 수집기 추가 예정
    }
    
    @classmethod
    def get_collector(cls, service_name: str, region: str = None, 
                     session: Optional[boto3.Session] = None) -> BaseCollector:
        """
        서비스 이름에 해당하는 수집기 인스턴스를 반환합니다.
        
        Args:
            service_name: AWS 서비스 이름
            region: AWS 리전 (선택 사항)
            session: AWS 세션 객체 (선택 사항)
            
        Returns:
            BaseCollector: 수집기 인스턴스
            
        Raises:
            ValueError: 지원하지 않는 서비스 이름인 경우
        """
        collector_class = cls._collectors.get(service_name.lower())
        if not collector_class:
            raise ValueError(f"지원하지 않는 서비스 이름: {service_name}")
        
        # 세션이 없는 경우 .env 파일의 자격 증명으로 세션 생성
        if not session:
            session = boto3.Session(
                aws_access_key_id=Config.AWS_ACCESS_KEY,
                aws_secret_access_key=Config.AWS_SECRET_KEY,
                region_name=region or Config.AWS_REGION
            )
        
        return collector_class(region=region, session=session)
    
    @classmethod
    def get_available_services(cls) -> Dict[str, str]:
        """
        사용 가능한 서비스 목록을 반환합니다.
        
        Returns:
            Dict[str, str]: 서비스 이름과 설명 매핑
        """
        return {
            'ec2': 'EC2 인스턴스',
            's3': 'S3 버킷',
            # 다른 서비스 추가 예정
        }