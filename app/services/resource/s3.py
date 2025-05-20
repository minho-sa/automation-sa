import boto3
from typing import Dict, List, Any
import logging
from datetime import datetime, timedelta
import pytz
from app.services.resource.base_service import create_boto3_client

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_s3_data(region: str, collection_id: str = None, auth_type: str = 'access_key', **auth_params) -> Dict:
    """
    S3 버킷 데이터 수집
    
    Args:
        region: AWS 리전
        collection_id: 수집 ID (선택 사항)
        auth_type: 인증 유형 ('access_key' 또는 'role_arn')
        **auth_params: 인증 유형에 따른 추가 파라미터
            - access_key 인증: aws_access_key, aws_secret_key, aws_session_token(선택)
            - role_arn 인증: role_arn, server_access_key, server_secret_key
    
    Returns:
        수집된 S3 데이터
    """
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.info(f"{log_prefix}Starting S3 data collection using {auth_type} authentication")
    try:
        # S3 클라이언트 생성
        s3_client = create_boto3_client('s3', region, auth_type=auth_type, **auth_params)
        
        # 버킷 목록 가져오기
        response = s3_client.list_buckets()
        buckets = []
        
        logger.info(f"{log_prefix}Found {len(response.get('Buckets', []))} S3 buckets")
        
        # 각 버킷에 대한 정보 수집
        for bucket in response.get('Buckets', []):
            bucket_name = bucket['Name']
            logger.debug(f"{log_prefix}Processing bucket: {bucket_name}")
            
            # 기본 버킷 정보
            bucket_data = {
                'name': bucket_name,
                'creation_date': bucket['CreationDate'],
                'region': None,
                'public_access': False,
                'versioning': False,
                'encryption': False,
                'lifecycle_rules': [],
                'tags': {},
                'size': 0,
                'object_count': 0
            }
            
            # 버킷 리전 확인
            try:
                location = s3_client.get_bucket_location(Bucket=bucket_name)
                bucket_data['region'] = location.get('LocationConstraint') or 'us-east-1'
            except Exception as e:
                logger.error(f"Error getting bucket location for {bucket_name}: {str(e)}")
            
            # 퍼블릭 액세스 설정 확인
            try:
                public_access = s3_client.get_public_access_block(Bucket=bucket_name)
                bucket_data['public_access'] = not (
                    public_access['PublicAccessBlockConfiguration']['BlockPublicAcls'] and
                    public_access['PublicAccessBlockConfiguration']['BlockPublicPolicy'] and
                    public_access['PublicAccessBlockConfiguration']['IgnorePublicAcls'] and
                    public_access['PublicAccessBlockConfiguration']['RestrictPublicBuckets']
                )
            except Exception as e:
                # 퍼블릭 액세스 블록 설정이 없는 경우 잠재적으로 퍼블릭으로 간주
                logger.error(f"Error getting public access block for {bucket_name}: {str(e)}")
                bucket_data['public_access'] = True
            
            # 버저닝 설정 확인
            try:
                versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
                bucket_data['versioning'] = versioning.get('Status') == 'Enabled'
            except Exception as e:
                logger.error(f"Error getting versioning for {bucket_name}: {str(e)}")
            
            # 암호화 설정 확인
            try:
                encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                bucket_data['encryption'] = True
            except Exception as e:
                # 암호화 설정이 없는 경우 예외 발생, 무시
                bucket_data['encryption'] = False
            
            # 라이프사이클 규칙 확인
            try:
                lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                bucket_data['lifecycle_rules'] = lifecycle.get('Rules', [])
            except Exception as e:
                # 라이프사이클 설정이 없는 경우 예외 발생, 무시
                pass
            
            # 태그 확인
            try:
                tags = s3_client.get_bucket_tagging(Bucket=bucket_name)
                bucket_data['tags'] = {tag['Key']: tag['Value'] for tag in tags.get('TagSet', [])}
            except Exception as e:
                # 태그가 없는 경우 예외 발생, 무시
                pass
            
            # 버킷 크기 및 객체 수 확인 (CloudWatch 메트릭 사용)
            try:
                cloudwatch = create_boto3_client('cloudwatch', region, auth_type=auth_type, **auth_params)
                
                # 버킷 크기 메트릭
                # 현재 시간과 24시간 전 시간을 사용하여 시간 범위 설정
                current_time = datetime.now(pytz.UTC)
                start_time = current_time - timedelta(days=1)
                
                size_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/S3',
                    MetricName='BucketSizeBytes',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': bucket_name},
                        {'Name': 'StorageType', 'Value': 'StandardStorage'}
                    ],
                    StartTime=start_time,
                    EndTime=current_time,
                    Period=86400,
                    Statistics=['Average']
                )
                
                if size_response['Datapoints']:
                    bucket_data['size'] = size_response['Datapoints'][0]['Average']
                
                # 객체 수 메트릭
                # 현재 시간과 24시간 전 시간을 사용 (위에서 이미 설정한 시간 사용)
                count_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/S3',
                    MetricName='NumberOfObjects',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': bucket_name},
                        {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
                    ],
                    StartTime=start_time,
                    EndTime=current_time,
                    Period=86400,
                    Statistics=['Average']
                )
                
                if count_response['Datapoints']:
                    bucket_data['object_count'] = count_response['Datapoints'][0]['Average']
            except Exception as e:
                logger.error(f"{log_prefix}Error getting metrics for {bucket_name}: {str(e)}")
            
            buckets.append(bucket_data)
        
        result = {'buckets': buckets}
        logger.info(f"{log_prefix}Successfully collected data for {len(buckets)} S3 buckets")
        return result
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_s3_data: {str(e)}")
        return {'error': str(e)}