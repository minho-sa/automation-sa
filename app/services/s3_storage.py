import boto3
import json
import logging
from datetime import datetime
from botocore.exceptions import ClientError
from config import Config

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class S3Storage:
    """
    S3를 데이터베이스처럼 사용하여 통합 대시보드 결과를 관리하는 클래스
    """
    def __init__(self, region=None):
        """
        S3Storage 클래스 초기화
        
        Args:
            region: AWS 리전 (기본값: Config에서 가져옴)
        """
        self.region = region or Config.AWS_REGION
        self.bucket_name = Config.DATA_BUCKET_NAME
        
        # 버킷 이름 로깅
        logger.info(f"S3Storage 초기화: 버킷={self.bucket_name}, 리전={self.region}")
        
        # S3 클라이언트 생성
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=Config.AWS_ACCESS_KEY,
                aws_secret_access_key=Config.AWS_SECRET_KEY
            )
            # 버킷이 존재하는지 확인
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 버킷 {self.bucket_name} 접근 확인 완료")
        except Exception as e:
            logger.error(f"S3 클라이언트 초기화 또는 버킷 접근 중 오류: {str(e)}")
            # 오류를 다시 발생시키지 않고 계속 진행 (실패 시 나중에 처리)
        
    def _get_user_prefix(self, user_id):
        """사용자별 S3 경로 접두사 생성"""
        return f"users/{user_id}/dashboard_data/"
        
    def save_collection_data(self, user_id, collection_id, data, selected_services=None):
        """
        수집된 데이터를 S3에 저장
        
        Args:
            user_id: 사용자 ID
            collection_id: 수집 ID
            data: 저장할 데이터 (dict)
            selected_services: 선택된 서비스 목록 (list)
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 타임스탬프 추가
            timestamp = datetime.now().isoformat()
            
            # 메타데이터 생성
            metadata = {
                'user_id': user_id,
                'collection_id': collection_id,
                'timestamp': timestamp,
                'selected_services': selected_services or []
            }
            
            # 메타데이터 저장
            metadata_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/metadata.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata),
                ContentType='application/json'
            )
            logger.info(f"메타데이터 저장 완료: {metadata_key}")
            
            # 서비스 디렉토리 생성 (빈 파일로)
            services_dir_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/services/"
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=services_dir_key,
                    Body="",
                    ContentType='application/json'
                )
                logger.info(f"서비스 디렉토리 생성 완료: {services_dir_key}")
            except Exception as e:
                logger.warning(f"서비스 디렉토리 생성 중 오류 (무시): {str(e)}")
            
            # 각 서비스 데이터 개별 저장
            saved_services = []
            for service_key, service_data in data.items():
                try:
                    service_data_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/services/{service_key}.json"
                    # 데이터가 None이 아닌지 확인
                    if service_data is None:
                        logger.warning(f"서비스 {service_key}의 데이터가 None입니다. 빈 객체로 저장합니다.")
                        service_data = {"status": "collected", "data": {}}
                    
                    # 데이터 직렬화
                    try:
                        # datetime 객체를 문자열로 변환하는 JSON 인코더
                        class DateTimeEncoder(json.JSONEncoder):
                            def default(self, obj):
                                if isinstance(obj, datetime):
                                    return obj.isoformat()
                                return super().default(obj)
                        
                        service_data_json = json.dumps(service_data, cls=DateTimeEncoder)
                    except TypeError as e:
                        logger.error(f"서비스 {service_key} 데이터 직렬화 중 오류: {str(e)}")
                        # 직렬화 불가능한 객체가 있는 경우 기본 객체로 대체
                        service_data = {"status": "error", "message": "직렬화 불가능한 데이터", "error": str(e)}
                        service_data_json = json.dumps(service_data)
                    
                    # S3에 저장
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=service_data_key,
                        Body=service_data_json,
                        ContentType='application/json'
                    )
                    saved_services.append(service_key)
                    logger.info(f"서비스 {service_key} 데이터 저장 완료: {service_data_key}")
                except Exception as e:
                    logger.error(f"서비스 {service_key} 데이터 저장 중 오류: {str(e)}")
            
            # 선택된 서비스 중 데이터가 없는 경우에도 빈 객체 저장
            if selected_services:
                for service_key in selected_services:
                    if service_key not in data:
                        try:
                            service_data_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/services/{service_key}.json"
                            empty_data = {"status": "collected", "data": {}}
                            self.s3_client.put_object(
                                Bucket=self.bucket_name,
                                Key=service_data_key,
                                Body=json.dumps(empty_data),
                                ContentType='application/json'
                            )
                            saved_services.append(service_key)
                            logger.info(f"서비스 {service_key}의 빈 데이터 저장 완료: {service_data_key}")
                        except Exception as e:
                            logger.error(f"서비스 {service_key}의 빈 데이터 저장 중 오류: {str(e)}")
            
            logger.info(f"사용자 {user_id}의 수집 데이터 {collection_id}를 S3에 저장했습니다. 저장된 서비스: {saved_services}")
            return True
            
        except Exception as e:
            logger.error(f"S3에 데이터 저장 중 오류 발생: {str(e)}")
            return False
            
    def get_collection_data(self, user_id, collection_id):
        """
        S3에서 특정 수집 ID의 데이터 조회
        
        Args:
            user_id: 사용자 ID
            collection_id: 수집 ID
            
        Returns:
            dict: 수집된 데이터와 메타데이터
        """
        try:
            result = {'metadata': None, 'services_data': {}}
            
            # 메타데이터 조회
            metadata_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/metadata.json"
            logger.info(f"메타데이터 조회 시도: {metadata_key}")
            
            try:
                metadata_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                result['metadata'] = json.loads(metadata_obj['Body'].read().decode('utf-8'))
                logger.info(f"메타데이터 로드 성공: {result['metadata']}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.warning(f"메타데이터를 찾을 수 없습니다: {metadata_key}")
                    return None
                else:
                    logger.error(f"메타데이터 로드 중 오류: {str(e)}")
                    raise
            
            # 선택된 서비스 목록 가져오기
            selected_services = result['metadata'].get('selected_services', [])
            logger.info(f"선택된 서비스 목록: {selected_services}")
            
            # 서비스 데이터 디렉토리 확인
            services_prefix = f"{self._get_user_prefix(user_id)}collections/{collection_id}/services/"
            available_files = []
            
            try:
                # 디렉토리 내 모든 객체 나열
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=services_prefix
                )
                
                if 'Contents' in response:
                    available_files = [item['Key'] for item in response['Contents']]
                    logger.info(f"서비스 디렉토리에서 찾은 파일들: {available_files}")
                else:
                    logger.warning(f"서비스 데이터 디렉토리가 비어있습니다: {services_prefix}")
                    
                    # 서비스 디렉토리가 비어있으면 기본 데이터 생성
                    for service_key in selected_services:
                        # 빈 데이터 생성
                        empty_data = {"status": "collected", "data": {}}
                        
                        # S3에 저장
                        service_data_key = f"{services_prefix}{service_key}.json"
                        self.s3_client.put_object(
                            Bucket=self.bucket_name,
                            Key=service_data_key,
                            Body=json.dumps(empty_data),
                            ContentType='application/json'
                        )
                        logger.info(f"서비스 {service_key}의 빈 데이터 생성 완료: {service_data_key}")
                        
                        # 결과에 추가
                        result['services_data'][service_key] = empty_data
                    
                    # 빈 데이터를 생성했으므로 바로 반환
                    return result
            except Exception as e:
                logger.error(f"서비스 디렉토리 조회 중 오류: {str(e)}")
            
            # 각 서비스 데이터 조회
            for service_key in selected_services:
                try:
                    service_data_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/services/{service_key}.json"
                    logger.info(f"서비스 데이터 조회 시도: {service_data_key}")
                    
                    service_data_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=service_data_key)
                    service_data = json.loads(service_data_obj['Body'].read().decode('utf-8'))
                    result['services_data'][service_key] = service_data
                    logger.info(f"서비스 {service_key}의 데이터를 성공적으로 로드했습니다.")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        logger.warning(f"서비스 {service_key}의 데이터를 찾을 수 없습니다. 경로: {service_data_key}")
                        # 데이터가 없으면 빈 데이터 생성
                        empty_data = {"status": "collected", "data": {}}
                        result['services_data'][service_key] = empty_data
                        
                        # S3에도 저장
                        try:
                            self.s3_client.put_object(
                                Bucket=self.bucket_name,
                                Key=service_data_key,
                                Body=json.dumps(empty_data),
                                ContentType='application/json'
                            )
                            logger.info(f"서비스 {service_key}의 빈 데이터 생성 완료: {service_data_key}")
                        except Exception as save_err:
                            logger.error(f"빈 데이터 저장 중 오류: {str(save_err)}")
                    else:
                        logger.error(f"서비스 {service_key} 데이터 로드 중 오류: {str(e)}")
            
            # 데이터가 비어있는지 확인
            if not result['services_data']:
                logger.warning(f"수집 ID {collection_id}에 대한 서비스 데이터가 없습니다.")
                # 빈 데이터라도 생성
                for service_key in selected_services:
                    result['services_data'][service_key] = {"status": "collected", "data": {}}
            
            return result
            
        except Exception as e:
            logger.error(f"S3에서 데이터 조회 중 오류 발생: {str(e)}")
            return None
            
    def list_user_collections(self, user_id):
        """
        사용자의 모든 수집 데이터 목록 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            list: 수집 데이터 메타데이터 목록 (최신순)
        """
        try:
            collections = []
            prefix = f"{self._get_user_prefix(user_id)}collections/"
            
            # S3에서 메타데이터 파일 목록 조회
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix, Delimiter='/'):
                if 'CommonPrefixes' in page:
                    for common_prefix in page['CommonPrefixes']:
                        collection_prefix = common_prefix['Prefix']
                        collection_id = collection_prefix.split('/')[-2]  # collections/{collection_id}/
                        
                        # 메타데이터 조회
                        try:
                            metadata_key = f"{collection_prefix}metadata.json"
                            metadata_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
                            collections.append(metadata)
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'NoSuchKey':
                                logger.warning(f"수집 ID {collection_id}의 메타데이터를 찾을 수 없습니다.")
                            else:
                                raise
            
            # 최신순으로 정렬
            collections.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return collections
            
        except Exception as e:
            logger.error(f"사용자 수집 목록 조회 중 오류 발생: {str(e)}")
            return []
            
    def delete_collection(self, user_id, collection_id):
        """
        특정 수집 데이터 삭제
        
        Args:
            user_id: 사용자 ID
            collection_id: 수집 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            prefix = f"{self._get_user_prefix(user_id)}collections/{collection_id}/"
            
            # 해당 접두사의 모든 객체 삭제
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects_to_delete:
                        self.s3_client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={'Objects': objects_to_delete}
                        )
            
            logger.info(f"사용자 {user_id}의 수집 데이터 {collection_id}를 삭제했습니다.")
            return True
            
        except Exception as e:
            logger.error(f"수집 데이터 삭제 중 오류 발생: {str(e)}")
            return False