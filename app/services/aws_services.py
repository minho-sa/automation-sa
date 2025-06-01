import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.services.resource.collector_factory import CollectorFactory
from app.services.resource.common.data_storage import ResourceDataStorage

logger = logging.getLogger(__name__)

def collect_service_data(username: str, service_name: str, region: str, 
                        auth_type: str = 'access_key', **auth_params) -> Dict[str, Any]:
    """
    AWS 서비스 데이터 수집
    
    Args:
        username: 사용자 ID
        service_name: 서비스 이름
        region: AWS 리전
        auth_type: 인증 유형 ('access_key' 또는 'role_arn')
        **auth_params: 인증 유형에 따른 추가 파라미터
            - access_key 인증: aws_access_key, aws_secret_key, aws_session_token(선택)
            - role_arn 인증: role_arn, aws_access_key, aws_secret_key, aws_session_token(선택)
    
    Returns:
        Dict[str, Any]: 수집 결과
    """
    try:
        # 수집 ID 생성
        collection_id = str(uuid.uuid4())
        log_prefix = f"[{collection_id}] "
        
        logger.info(f"{log_prefix}데이터 수집 시작: 사용자={username}, 서비스={service_name}, 리전={region}")
        
        # 세션 생성
        import boto3
        if auth_type == 'access_key':
            session = boto3.Session(
                aws_access_key_id=auth_params.get('aws_access_key'),
                aws_secret_access_key=auth_params.get('aws_secret_key'),
                aws_session_token=auth_params.get('aws_session_token'),
                region_name=region
            )
        elif auth_type == 'role_arn':
            # STS를 통한 역할 수임
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=auth_params.get('aws_access_key'),
                aws_secret_access_key=auth_params.get('aws_secret_key'),
                aws_session_token=auth_params.get('aws_session_token'),
                region_name=region
            )
            
            response = sts_client.assume_role(
                RoleArn=auth_params.get('role_arn'),
                RoleSessionName=f"CollectionSession-{collection_id}"
            )
            
            credentials = response['Credentials']
            session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=region
            )
        else:
            return {
                'success': False,
                'error': f"지원하지 않는 인증 유형: {auth_type}"
            }
        
        # 수집기 생성 및 데이터 수집
        try:
            collector = CollectorFactory.get_collector(service_name, region=region, session=session)
            result = collector.collect(collection_id=collection_id)
            
            # 수집 결과 저장
            storage = ResourceDataStorage(region=region)
            storage.save_resource_data(username, service_name, collection_id, result)
            
            # 수집 결과 반환
            return {
                'success': True,
                'collection_id': collection_id,
                'timestamp': datetime.now().isoformat(),
                'service_name': service_name,
                'region': region,
                'result': result
            }
        except ValueError as ve:
            # 지원하지 않는 서비스인 경우 빈 결과 반환
            logger.warning(f"{log_prefix}지원하지 않는 서비스: {service_name} - {str(ve)}")
            return {
                'success': True,
                'collection_id': collection_id,
                'timestamp': datetime.now().isoformat(),
                'service_name': service_name,
                'region': region,
                'result': {'message': f'지원하지 않는 서비스: {service_name}'}
            }
        
    except Exception as e:
        logger.error(f"데이터 수집 중 오류 발생: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_available_services() -> Dict[str, str]:
    """
    사용 가능한 서비스 목록 조회
    
    Returns:
        Dict[str, str]: 서비스 이름과 설명 매핑
    """
    try:
        return CollectorFactory.get_available_services()
    except Exception as e:
        logger.error(f"서비스 목록 조회 중 오류 발생: {str(e)}")
        # 기본 서비스 목록 반환
        return {
            'ec2': 'EC2 인스턴스',
            's3': 'S3 버킷'
        }

def get_service_data(username: str, service_name: str, collection_id: str) -> Optional[Dict[str, Any]]:
    """
    저장된 서비스 데이터 조회
    
    Args:
        username: 사용자 ID
        service_name: 서비스 이름
        collection_id: 수집 ID
        
    Returns:
        Optional[Dict[str, Any]]: 저장된 서비스 데이터 또는 None
    """
    try:
        storage = ResourceDataStorage()
        return storage.get_resource_data(username, service_name, collection_id)
    except Exception as e:
        logger.error(f"서비스 데이터 조회 중 오류 발생: {str(e)}")
        return None

def list_collections(username: str, service_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    사용자의 수집 목록 조회
    
    Args:
        username: 사용자 ID
        service_name: 서비스 이름 (선택 사항)
        limit: 최대 조회 개수
        
    Returns:
        List[Dict[str, Any]]: 수집 목록
    """
    try:
        storage = ResourceDataStorage()
        return storage.list_collections(username, service_name, limit)
    except Exception as e:
        logger.error(f"수집 목록 조회 중 오류 발생: {str(e)}")
        return []