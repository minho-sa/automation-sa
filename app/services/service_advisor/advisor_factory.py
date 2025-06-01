from typing import Dict, List, Optional, Any
import logging
import boto3
from botocore.exceptions import ClientError
from config import Config

# 서비스별 어드바이저 임포트
from app.services.service_advisor.ec2.ec2_advisor import EC2Advisor
from app.services.service_advisor.lambda_service.lambda_advisor import LambdaAdvisor
from app.services.service_advisor.iam.iam_advisor import IAMAdvisor
from app.services.service_advisor.rds.rds_advisor import RDSAdvisor
from app.services.service_advisor.s3.s3_advisor import S3Advisor

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
            'ec2': EC2Advisor,
            'lambda': LambdaAdvisor,
            'iam': IAMAdvisor,
            'rds': RDSAdvisor,
            's3': S3Advisor
        }
    
    def get_advisor(self, service_name: str, role_arn: str = None) -> Optional[Any]:
        """
        서비스 이름에 맞는 어드바이저 객체를 반환합니다.
        
        Args:
            service_name: 서비스 이름 (ec2, lambda, iam, rds, s3 등)
            role_arn: AWS 자격증명용 Role ARN (선택 사항)
            
        Returns:
            Optional[Any]: 서비스 어드바이저 객체 또는 None
        """
        if service_name not in self.service_mapping:
            self.logger.warning(f"지원하지 않는 서비스: {service_name}")
            return None
        
        advisor_class = self.service_mapping[service_name]
        self.logger.info(f"어드바이저 생성: {service_name} ({advisor_class.__name__})")
        
        # AWS 자격증명 설정
        session = self._create_aws_session(role_arn)
        
        return advisor_class(session=session)
    
    def _create_aws_session(self, role_arn: str = None) -> boto3.Session:
        """
        AWS 세션을 생성합니다.
        
        Args:
            role_arn: 사용할 Role ARN (없으면 기본 자격증명 사용)
            
        Returns:
            boto3.Session: AWS 세션 객체
        """
        try:
            if role_arn:
                # STS 클라이언트 생성
                sts_client = boto3.client(
                    'sts',
                    region_name=Config.AWS_REGION,
                    aws_access_key_id=Config.AWS_ACCESS_KEY,
                    aws_secret_access_key=Config.AWS_SECRET_KEY
                )
                
                # 역할 수임
                response = sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName='ServiceAdvisorSession',
                    DurationSeconds=3600  # 1시간
                )
                
                # 임시 자격증명 가져오기
                credentials = response['Credentials']
                
                # 세션 생성
                session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    region_name=Config.AWS_REGION
                )
                
                self.logger.info(f"Role ARN {role_arn}을 사용하여 AWS 세션 생성 완료")
                return session
            else:
                # 기본 자격증명 사용
                session = boto3.Session(
                    aws_access_key_id=Config.AWS_ACCESS_KEY,
                    aws_secret_access_key=Config.AWS_SECRET_KEY,
                    region_name=Config.AWS_REGION
                )
                
                self.logger.info("기본 자격증명으로 AWS 세션 생성 완료")
                return session
                
        except ClientError as e:
            self.logger.error(f"AWS 세션 생성 중 오류 발생: {str(e)}")
            raise Exception(f"AWS 자격증명 오류: {str(e)}")
    
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
            'iam': 'AWS IAM',
            'rds': 'Amazon RDS',
            's3': 'Amazon S3'
        }
        
        return service_display_names.get(service_name, service_name.upper())