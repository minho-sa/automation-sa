import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional, Dict, Any

class AWSClient:
    """
    AWS 서비스 클라이언트를 관리하는 클래스
    사용자 인증 정보를 사용하여 AWS 서비스에 접근합니다.
    """
    
    def __init__(self, session: Optional[boto3.Session] = None):
        """
        AWS 클라이언트 초기화
        
        Args:
            session: AWS 세션 객체 (선택 사항)
        """
        self.logger = logging.getLogger(__name__)
        self.session = session or boto3.Session()
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

# 기존 코드와의 호환성을 위한 함수
def create_boto3_client(service_name, region_name=None, role_arn=None):
    """
    boto3 클라이언트를 생성하는 함수 (기존 코드와의 호환성 유지)
    
    Args:
        service_name: AWS 서비스 이름
        region_name: AWS 리전 이름 (선택 사항)
        role_arn: AWS 역할 ARN (필수 - 사용자 세션의 Role ARN)
        
    Returns:
        boto3 클라이언트 객체
    """
    from config import Config
    
    try:
        # Role ARN이 없으면 오류 발생
        if not role_arn:
            raise Exception("Role ARN이 필요합니다. 사용자가 로그인하지 않았거나 Role ARN이 설정되지 않았습니다.")
        
        # 기본 세션 생성 (.env의 자격증명 사용)
        if not Config.AWS_ACCESS_KEY or not Config.AWS_SECRET_KEY:
            raise Exception(".env 파일에 AWS_ACCESS_KEY와 AWS_SECRET_KEY가 설정되지 않았습니다.")
        
        session = boto3.Session(
            aws_access_key_id=Config.AWS_ACCESS_KEY,
            aws_secret_access_key=Config.AWS_SECRET_KEY,
            region_name=region_name or Config.AWS_REGION
        )
        
        # STS 클라이언트로 역할 전환
        sts_client = session.client('sts')
        logging.info(f"Role ARN으로 인증 시도: {role_arn}")
        
        # 현재 자격증명 확인
        try:
            current_identity = sts_client.get_caller_identity()
            logging.info(f"현재 자격증명: {current_identity['Arn']}")
        except Exception as e:
            logging.error(f"현재 자격증명 확인 실패: {str(e)}")
        
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='ServiceAdvisorSession',
            DurationSeconds=3600  # 1시간
        )
        
        credentials = response['Credentials']
        logging.info(f"Role 전환 성공: {response['AssumedRoleUser']['Arn']}")
        
        # 임시 자격 증명으로 새 세션 생성
        session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=region_name or Config.AWS_REGION
        )
        
        # 클라이언트 생성
        client = session.client(service_name)
        
        # 연결 테스트
        if service_name == 'sts':
            identity = client.get_caller_identity()
            logging.info(f"클라이언트 생성 성공: {identity['Arn']}")
        
        return client
    except Exception as e:
        error_msg = str(e)
        logging.error(f"AWS 클라이언트 생성 중 오류: {error_msg}")
        
        # 오류 유형에 따른 상세 메시지 제공
        if 'AccessDenied' in error_msg:
            if 'AssumeRole' in error_msg:
                raise Exception(f"Role 전환 권한이 없습니다. .env의 project-automation 사용자가 {role_arn} 역할을 assume할 수 있는 권한이 필요합니다.")
            else:
                raise Exception(f"AWS 서비스 접근 권한이 없습니다: {error_msg}")
        elif 'InvalidClientTokenId' in error_msg:
            raise Exception(f".env 파일의 AWS 자격증명이 잘못되었습니다: {error_msg}")
        elif 'SignatureDoesNotMatch' in error_msg:
            raise Exception(f".env 파일의 AWS Secret Key가 잘못되었습니다: {error_msg}")
        else:
            raise Exception(f"AWS 인증 실패: {error_msg}")

