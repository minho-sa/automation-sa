import boto3
import logging
from typing import Dict, List, Any, Optional
from config import Config

class BaseCollector:
    """
    모든 리소스 수집기의 기본 클래스입니다.
    각 서비스별 수집기는 이 클래스를 상속받아 구현합니다.
    """
    
    def __init__(self, region: str = None, session: Optional[boto3.Session] = None):
        """
        수집기 초기화
        
        Args:
            region: AWS 리전 (기본값: Config에서 가져옴)
            session: AWS 세션 객체 (선택 사항)
        """
        self.region = region or Config.AWS_REGION
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 세션 설정
        if session:
            self.session = session
        else:
            self.session = boto3.Session(
                aws_access_key_id=Config.AWS_ACCESS_KEY,
                aws_secret_access_key=Config.AWS_SECRET_KEY,
                region_name=self.region
            )
        
        # 클라이언트 초기화
        self._init_clients()
    
    def _init_clients(self) -> None:
        """
        필요한 AWS 클라이언트를 초기화하는 메서드.
        각 서비스 수집기에서 오버라이드해야 합니다.
        """
        pass
    
    def collect(self, collection_id: str = None) -> Dict[str, Any]:
        """
        리소스 데이터를 수집합니다.
        각 서비스 수집기에서 오버라이드해야 합니다.
        
        Args:
            collection_id: 수집 ID (선택 사항)
            
        Returns:
            Dict[str, Any]: 수집된 리소스 데이터
        """
        raise NotImplementedError("이 메서드는 하위 클래스에서 구현해야 합니다.")
    
    def get_client(self, service_name: str) -> boto3.client:
        """
        AWS 서비스 클라이언트를 생성합니다.
        
        Args:
            service_name: AWS 서비스 이름
            
        Returns:
            boto3.client: AWS 서비스 클라이언트
        """
        return self.session.client(service_name)
    
    def assume_role_session(self, role_arn: str, session_name: str = "CollectorSession") -> boto3.Session:
        """
        지정된 IAM 역할을 수임하여 새 세션을 생성합니다.
        
        Args:
            role_arn: 수임할 역할의 ARN
            session_name: 세션 이름
            
        Returns:
            boto3.Session: 새 세션 객체
        """
        sts_client = self.session.client('sts')
        
        # 역할 수임
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=session_name
        )
        
        # 임시 자격 증명으로 새 세션 생성
        credentials = response['Credentials']
        return boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=self.region
        )