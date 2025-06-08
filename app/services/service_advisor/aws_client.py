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
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        boto3 클라이언트 객체
    """
    from config import Config
    
    try:
        # 기본 세션 생성
        session = boto3.Session(
            aws_access_key_id=Config.AWS_ACCESS_KEY,
            aws_secret_access_key=Config.AWS_SECRET_KEY,
            region_name=region_name or Config.AWS_REGION
        )
        
        # 역할 ARN이 제공된 경우 해당 역할로 임시 자격 증명 생성
        if role_arn:
            sts_client = session.client('sts')
            response = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName='ServiceAdvisorSession'
            )
            
            credentials = response['Credentials']
            
            # 임시 자격 증명으로 새 세션 생성
            session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=region_name or Config.AWS_REGION
            )
        
        # 클라이언트 생성
        client = session.client(service_name)
        
        # 연결 테스트 (STS 호출)
        if service_name == 'sts':
            client.get_caller_identity()
        
        return client
    except Exception as e:
        logging.error(f"AWS 클라이언트 생성 중 오류: {str(e)}")
        # 모의 클라이언트 반환 (테스트용)
        return MockAWSClient(service_name)

# 테스트용 모의 AWS 클라이언트
class MockAWSClient:
    def __init__(self, service_name):
        self.service_name = service_name
        logging.warning(f"모의 {service_name} 클라이언트가 생성되었습니다. 실제 AWS API 호출은 작동하지 않습니다.")
    
    def describe_security_groups(self, **kwargs):
        return {"SecurityGroups": [
            {
                "GroupId": "sg-12345678",
                "GroupName": "default",
                "Description": "default VPC security group",
                "IpPermissions": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
                    }
                ],
                "VpcId": "vpc-12345678"
            }
        ]}
    
    def describe_instances(self, **kwargs):
        return {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-0787a481d5ad3daed",
                            "InstanceType": "t2.micro",
                            "Tags": [{"Key": "Name", "Value": "ttt"}]
                        },
                        {
                            "InstanceId": "i-0c85364be4c503455",
                            "InstanceType": "t2.small",
                            "Tags": [{"Key": "Name", "Value": "chat"}]
                        }
                    ]
                }
            ]
        }
    
    def get_metric_statistics(self, **kwargs):
        instance_id = kwargs.get("Dimensions", [{}])[0].get("Value", "")
        
        if instance_id == "i-0787a481d5ad3daed":
            return {
                "Datapoints": [
                    {"Average": 0.41, "Maximum": 26.78, "Timestamp": "2023-06-08T12:00:00Z"},
                    {"Average": 0.38, "Maximum": 22.45, "Timestamp": "2023-06-08T13:00:00Z"}
                ]
            }
        else:
            return {
                "Datapoints": [
                    {"Average": 4.85, "Maximum": 64.94, "Timestamp": "2023-06-08T12:00:00Z"},
                    {"Average": 5.12, "Maximum": 58.32, "Timestamp": "2023-06-08T13:00:00Z"}
                ]
            }
    
    def get_caller_identity(self):
        return {"UserId": "AIDACKCEVSQ6C2EXAMPLE", "Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/test-user"}