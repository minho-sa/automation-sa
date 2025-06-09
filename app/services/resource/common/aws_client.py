import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional, Dict, Any
from config import Config

class AWSClient:
    """
    AWS 서비스 클라이언트를 관리하는 클래스
    사용자 인증 정보를 사용하여 AWS 서비스에 접근합니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None, region: str = None):
        """
        AWS 클라이언트 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
            region: AWS 리전 (선택 사항)
        """
        self.logger = logging.getLogger(__name__)
        
        # 세션 설정
        if session:
            self.session = session
        else:
            # .env 파일의 자격 증명 사용
            self.session = boto3.Session(
                aws_access_key_id=Config.AWS_ACCESS_KEY,
                aws_secret_access_key=Config.AWS_SECRET_KEY,
                region_name=region or Config.AWS_REGION
            )
            
        self.clients = {}
    
    def get_client(self, service_name: str) -> Any:
        """
        특정 AWS 서비스의 클라이언트를 반환합니다.
        
        Args:
            service_name: AWS 서비스 이름 (ec2, s3, iam 등)
            
        Returns:
            boto3 클라이언트 객체
        """
        if service_name not in self.clients:
            try:
                self.clients[service_name] = self.session.client(service_name)
                self.logger.debug(f"{service_name} 클라이언트 생성 완료")
            except ClientError as e:
                self.logger.error(f"{service_name} 클라이언트 생성 중 오류 발생: {str(e)}")
                raise
        
        return self.clients[service_name]
    
    def get_resource(self, service_name: str) -> Any:
        """
        특정 AWS 서비스의 리소스를 반환합니다.
        
        Args:
            service_name: AWS 서비스 이름 (ec2, s3, iam 등)
            
        Returns:
            boto3 리소스 객체
        """
        try:
            resource = self.session.resource(service_name)
            self.logger.debug(f"{service_name} 리소스 생성 완료")
            return resource
        except ClientError as e:
            self.logger.error(f"{service_name} 리소스 생성 중 오류 발생: {str(e)}")
            raise
    
    def validate_credentials(self) -> Dict[str, Any]:
        """
        현재 AWS 자격증명이 유효한지 확인합니다.
        
        Returns:
            Dict[str, Any]: 자격증명 정보
        """
        try:
            sts_client = self.get_client('sts')
            identity = sts_client.get_caller_identity()
            self.logger.info(f"유효한 AWS 자격증명: {identity['Arn']}")
            return identity
        except ClientError as e:
            self.logger.error(f"AWS 자격증명 검증 중 오류 발생: {str(e)}")
            raise Exception(f"AWS 자격증명이 유효하지 않습니다: {str(e)}")