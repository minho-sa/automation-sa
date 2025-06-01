import boto3
import json
import logging
import time
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from config import Config

# 로깅 설정 - 중복 로그 방지
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# 기존 핸들러 제거
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
# 새 핸들러 추가
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# 상위 로거로 전파 방지
logger.propagate = False

class S3Storage:
    """
    S3를 데이터베이스처럼 사용하여 통합 대시보드 결과를 관리하는 클래스
    """
    # 메모리 캐시 (클래스 변수)
    _cache = {
        'collections': {},  # 사용자별 컬렉션 목록 캐시
        'metadata': {},     # 메타데이터 캐시
        'data': {}          # 서비스 데이터 캐시
    }
    
    # 캐시 만료 시간 (초)
    CACHE_TTL = 300  # 5분
    
    # 클래스 인스턴스 캐시
    _instances = {}
    
    def __new__(cls, region=None):
        """
        싱글톤 패턴 구현 - 동일한 리전에 대해 하나의 인스턴스만 생성
        """
        region_key = region or Config.AWS_REGION
        if region_key not in cls._instances:
            cls._instances[region_key] = super(S3Storage, cls).__new__(cls)
            cls._instances[region_key]._initialized = False
        return cls._instances[region_key]
    
    def __init__(self, region=None):
        """
        S3Storage 클래스 초기화
        
        Args:
            region: AWS 리전 (기본값: Config에서 가져옴)
        """
        # 이미 초기화된 인스턴스는 다시 초기화하지 않음
        if hasattr(self, '_initialized') and self._initialized:
            return
            
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
            
        self._initialized = True
    
    def _get_user_prefix(self, user_id):
        """사용자별 S3 경로 접두사 생성"""
        return f"users/{user_id}/dashboard_data/"
    
    def _get_cache_key(self, key_type, user_id, collection_id=None, service_key=None):
        """캐시 키 생성"""
        if key_type == 'collections':
            return f"collections:{user_id}"
        elif key_type == 'metadata':
            return f"metadata:{user_id}:{collection_id}"
        elif key_type == 'data':
            return f"data:{user_id}:{collection_id}:{service_key}"
        return None
    
    def _get_from_cache(self, key_type, user_id, collection_id=None, service_key=None):
        """캐시에서 데이터 가져오기"""
        cache_key = self._get_cache_key(key_type, user_id, collection_id, service_key)
        if not cache_key:
            return None, False
        
        cache_entry = S3Storage._cache.get(key_type, {}).get(cache_key)
        if not cache_entry:
            return None, False
        
        # 캐시 만료 확인
        if time.time() - cache_entry['timestamp'] > S3Storage.CACHE_TTL:
            # 캐시 만료
            return None, False
        
        return cache_entry['data'], True
    
    def _set_in_cache(self, key_type, user_id, data, collection_id=None, service_key=None):
        """캐시에 데이터 저장"""
        cache_key = self._get_cache_key(key_type, user_id, collection_id, service_key)
        if not cache_key:
            return
        
        if key_type not in S3Storage._cache:
            S3Storage._cache[key_type] = {}
        
        S3Storage._cache[key_type][cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def _invalidate_cache(self, key_type, user_id, collection_id=None):
        """캐시 무효화"""
        if key_type == 'collections':
            cache_key = self._get_cache_key('collections', user_id)
            if cache_key in S3Storage._cache.get('collections', {}):
                del S3Storage._cache['collections'][cache_key]
        elif key_type == 'all':
            # 사용자의 모든 캐시 무효화
            for cache_type in S3Storage._cache:
                keys_to_delete = []
                for key in S3Storage._cache[cache_type]:
                    if f":{user_id}:" in key or key.endswith(f":{user_id}"):
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    if key in S3Storage._cache[cache_type]:
                        del S3Storage._cache[cache_type][key]
        elif collection_id:
            # 특정 컬렉션 관련 캐시 무효화
            for cache_type in ['metadata', 'data']:
                keys_to_delete = []
                for key in S3Storage._cache.get(cache_type, {}):
                    if f":{user_id}:{collection_id}" in key:
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    if key in S3Storage._cache.get(cache_type, {}):
                        del S3Storage._cache[cache_type][key]
    
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
            
            # 서비스 데이터 통합 파일 생성 (모든 서비스 데이터를 하나의 파일로 저장)
            all_services_data = {}
            
            # 각 서비스 데이터 처리
            for service_key, service_data in data.items():
                # 데이터가 None이 아닌지 확인
                if service_data is None:
                    logger.warning(f"서비스 {service_key}의 데이터가 None입니다. 빈 객체로 저장합니다.")
                    service_data = {"status": "collected", "data": {}}
                
                # 데이터 직렬화 가능한지 확인
                try:
                    # datetime 객체를 문자열로 변환하는 JSON 인코더
                    class DateTimeEncoder(json.JSONEncoder):
                        def default(self, obj):
                            if isinstance(obj, datetime):
                                return obj.isoformat()
                            return super().default(obj)
                    
                    # 테스트 직렬화 (오류 확인용)
                    json.dumps(service_data, cls=DateTimeEncoder)
                    
                    # 통합 데이터에 추가
                    all_services_data[service_key] = service_data
                    
                except TypeError as e:
                    logger.error(f"서비스 {service_key} 데이터 직렬화 중 오류: {str(e)}")
                    # 직렬화 불가능한 객체가 있는 경우 기본 객체로 대체
                    all_services_data[service_key] = {
                        "status": "error", 
                        "message": "직렬화 불가능한 데이터", 
                        "error": str(e)
                    }
            
            # 선택된 서비스 중 데이터가 없는 경우에도 빈 객체 추가
            if selected_services:
                for service_key in selected_services:
                    if service_key not in all_services_data:
                        all_services_data[service_key] = {"status": "collected", "data": {}}
            
            # 통합 데이터 파일 저장
            all_services_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/all_services.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=all_services_key,
                Body=json.dumps(all_services_data, cls=DateTimeEncoder),
                ContentType='application/json'
            )
            logger.info(f"통합 서비스 데이터 저장 완료: {all_services_key}")
            
            # 캐시 무효화 - 기존 캐시 삭제
            self._invalidate_cache('collections', user_id)
            self._invalidate_cache('all', user_id, collection_id)
            
            # 메타데이터를 캐시에 저장
            self._set_in_cache('metadata', user_id, metadata, collection_id)
            logger.info(f"💾 메타데이터 캐시 저장 완료: {collection_id}")
            
            # 서비스 데이터를 캐시에 저장
            self._set_in_cache('data', user_id, all_services_data, collection_id, 'all')
            logger.info(f"💾 서비스 데이터 캐시 저장 완료: {collection_id}")
            
            logger.info(f"사용자 {user_id}의 수집 데이터 {collection_id}를 S3에 저장했습니다.")
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
            data_source = {'metadata': None, 'services_data': None}  # 데이터 소스 추적
            
            # 메타데이터 캐시 확인
            metadata, cache_hit = self._get_from_cache('metadata', user_id, collection_id)
            if cache_hit:
                logger.info(f"✅ 메타데이터 캐시 히트 성공: {collection_id}")
                result['metadata'] = metadata
                data_source['metadata'] = 'cache'
            else:
                logger.info(f"❌ 메타데이터 캐시 히트 실패: {collection_id}")
                # 메타데이터 조회
                metadata_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/metadata.json"
                logger.info(f"📥 S3에서 메타데이터 조회 시도: {metadata_key}")
                
                try:
                    metadata_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                    result['metadata'] = json.loads(metadata_obj['Body'].read().decode('utf-8'))
                    logger.info(f"📥 S3에서 메타데이터 로드 성공")
                    data_source['metadata'] = 'S3'
                    
                    # 메타데이터 캐시에 저장
                    self._set_in_cache('metadata', user_id, result['metadata'], collection_id)
                    logger.info(f"💾 메타데이터 캐시 저장 완료")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        logger.warning(f"❌ S3에서 메타데이터를 찾을 수 없습니다: {metadata_key}")
                        return None
                    else:
                        logger.error(f"❌ S3에서 메타데이터 로드 중 오류: {str(e)}")
                        raise
            
            # 서비스 데이터 캐시 확인
            services_data, cache_hit = self._get_from_cache('data', user_id, collection_id, 'all')
            if cache_hit:
                logger.info(f"✅ 서비스 데이터 캐시 히트 성공: {collection_id}")
                result['services_data'] = services_data
                data_source['services_data'] = 'cache'
                logger.info(f"📊 데이터 소스 요약 - 메타데이터: {data_source['metadata']}, 서비스 데이터: {data_source['services_data']}")
                return result
            else:
                logger.info(f"❌ 서비스 데이터 캐시 히트 실패: {collection_id}")
            
            # 통합 서비스 데이터 파일 조회
            all_services_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/all_services.json"
            logger.info(f"📥 S3에서 통합 서비스 데이터 조회 시도: {all_services_key}")
            
            try:
                all_services_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=all_services_key)
                result['services_data'] = json.loads(all_services_obj['Body'].read().decode('utf-8'))
                logger.info(f"📥 S3에서 통합 서비스 데이터 로드 성공")
                data_source['services_data'] = 'S3'
                
                # 서비스 데이터 캐시에 저장
                self._set_in_cache('data', user_id, result['services_data'], collection_id, 'all')
                logger.info(f"💾 서비스 데이터 캐시 저장 완료")
                
                logger.info(f"📊 데이터 소스 요약 - 메타데이터: {data_source['metadata']}, 서비스 데이터: {data_source['services_data']}")
                return result
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.warning(f"❌ S3에서 통합 서비스 데이터를 찾을 수 없습니다. 개별 서비스 파일 조회로 전환합니다.")
                    # 이전 방식으로 개별 서비스 파일 조회 (하위 호환성 유지)
                    legacy_result = self._get_collection_data_legacy(user_id, collection_id, result)
                    if legacy_result:
                        data_source['services_data'] = 'S3 (legacy)'
                        logger.info(f"📊 데이터 소스 요약 - 메타데이터: {data_source['metadata']}, 서비스 데이터: {data_source['services_data']}")
                    return legacy_result
                else:
                    logger.error(f"❌ S3에서 통합 서비스 데이터 로드 중 오류: {str(e)}")
                    raise
            
        except Exception as e:
            logger.error(f"❌ 데이터 조회 중 오류 발생: {str(e)}")
            return None
    
    def _get_collection_data_legacy(self, user_id, collection_id, result):
        """
        이전 방식으로 개별 서비스 파일 조회 (하위 호환성 유지)
        """
        try:
            # 선택된 서비스 목록 가져오기
            selected_services = result['metadata'].get('selected_services', [])
            logger.info(f"📋 선택된 서비스 목록: {selected_services}")
            
            # 서비스 데이터 디렉토리 확인
            services_prefix = f"{self._get_user_prefix(user_id)}collections/{collection_id}/services/"
            available_files = []
            
            try:
                # 디렉토리 내 모든 객체 나열
                logger.info(f"📥 S3에서 서비스 디렉토리 조회: {services_prefix}")
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=services_prefix
                )
                
                if 'Contents' in response:
                    available_files = [item['Key'] for item in response['Contents']]
                    logger.info(f"📥 S3 서비스 디렉토리에서 찾은 파일: {len(available_files)}개")
                else:
                    logger.warning(f"⚠️ S3 서비스 디렉토리가 비어있습니다: {services_prefix}")
                    
                    # 서비스 디렉토리가 비어있으면 기본 데이터 생성
                    all_services_data = {}
                    for service_key in selected_services:
                        # 빈 데이터 생성
                        all_services_data[service_key] = {"status": "collected", "data": {}}
                    
                    # 통합 데이터 파일 저장
                    all_services_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/all_services.json"
                    logger.info(f"📤 S3에 빈 통합 서비스 데이터 생성 시작")
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=all_services_key,
                        Body=json.dumps(all_services_data),
                        ContentType='application/json'
                    )
                    logger.info(f"📤 S3에 통합 서비스 데이터 생성 완료: {all_services_key}")
                    
                    # 결과에 추가
                    result['services_data'] = all_services_data
                    
                    # 서비스 데이터 캐시에 저장
                    self._set_in_cache('data', user_id, all_services_data, collection_id, 'all')
                    logger.info(f"💾 서비스 데이터 캐시 저장 완료 (빈 데이터)")
                    
                    return result
            except Exception as e:
                logger.error(f"❌ S3 서비스 디렉토리 조회 중 오류: {str(e)}")
            
            # 각 서비스 데이터 조회
            all_services_data = {}
            for service_key in selected_services:
                try:
                    service_data_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/services/{service_key}.json"
                    logger.info(f"📥 S3에서 서비스 데이터 조회 시도: {service_key}")
                    
                    service_data_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=service_data_key)
                    service_data = json.loads(service_data_obj['Body'].read().decode('utf-8'))
                    all_services_data[service_key] = service_data
                    logger.info(f"📥 S3에서 서비스 {service_key} 데이터 로드 성공")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        logger.warning(f"⚠️ S3에서 서비스 {service_key} 데이터를 찾을 수 없습니다")
                        # 데이터가 없으면 빈 데이터 생성
                        all_services_data[service_key] = {"status": "collected", "data": {}}
                    else:
                        logger.error(f"❌ S3에서 서비스 {service_key} 데이터 로드 중 오류: {str(e)}")
            
            # 데이터가 비어있는지 확인
            if not all_services_data:
                logger.warning(f"⚠️ 수집 ID {collection_id}에 대한 서비스 데이터가 없습니다")
                # 빈 데이터라도 생성
                for service_key in selected_services:
                    all_services_data[service_key] = {"status": "collected", "data": {}}
            
            # 통합 데이터 파일 저장 (향후 조회를 위해)
            try:
                all_services_key = f"{self._get_user_prefix(user_id)}collections/{collection_id}/all_services.json"
                logger.info(f"📤 S3에 통합 서비스 데이터 저장 시작")
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=all_services_key,
                    Body=json.dumps(all_services_data),
                    ContentType='application/json'
                )
                logger.info(f"📤 S3에 통합 서비스 데이터 저장 완료: {all_services_key}")
            except Exception as e:
                logger.error(f"❌ S3에 통합 서비스 데이터 저장 중 오류: {str(e)}")
            
            result['services_data'] = all_services_data
            
            # 서비스 데이터 캐시에 저장
            self._set_in_cache('data', user_id, all_services_data, collection_id, 'all')
            logger.info(f"💾 서비스 데이터 캐시 저장 완료 (레거시 방식)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 레거시 방식으로 데이터 조회 중 오류 발생: {str(e)}")
            return None
    
    def list_user_collections(self, user_id):
        """
        사용자의 모든 수집 데이터 목록 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            list: 수집 데이터 메타데이터 목록 (최신순)
        """
        # 캐시 확인
        collections, cache_hit = self._get_from_cache('collections', user_id)
        if cache_hit:
            logger.info(f"✅ 컬렉션 목록 캐시 히트 성공: {user_id}")
            logger.info(f"📊 데이터 소스: 캐시 (컬렉션 목록)")
            return collections
        else:
            logger.info(f"❌ 컬렉션 목록 캐시 히트 실패: {user_id}")
            logger.info(f"📥 S3에서 컬렉션 목록 조회 시작")
        
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
                            # 캐시 확인
                            metadata, cache_hit = self._get_from_cache('metadata', user_id, collection_id)
                            if cache_hit:
                                collections.append(metadata)
                                continue
                            
                            metadata_key = f"{collection_prefix}metadata.json"
                            metadata_obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
                            collections.append(metadata)
                            
                            # 메타데이터 캐시에 저장
                            self._set_in_cache('metadata', user_id, metadata, collection_id)
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'NoSuchKey':
                                logger.warning(f"수집 ID {collection_id}의 메타데이터를 찾을 수 없습니다.")
                            else:
                                raise
            
            # 최신순으로 정렬
            collections.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # 캐시에 저장
            self._set_in_cache('collections', user_id, collections)
            logger.info(f"💾 컬렉션 목록 캐시 저장 완료: {user_id}")
            logger.info(f"📊 데이터 소스: S3 (컬렉션 목록)")
            
            return collections
            
        except Exception as e:
            logger.error(f"사용자 수집 목록 조회 중 오류 발생: {str(e)}")
            return []
    
    def get_service_data(self, user_id, collection_id, service_type):
        """
        특정 수집 ID의 특정 서비스 데이터만 조회
        
        Args:
            user_id: 사용자 ID
            collection_id: 수집 ID
            service_type: 서비스 타입 (ec2, s3 등)
            
        Returns:
            dict: 해당 서비스의 데이터
        """
        try:
            # 캐시 확인
            service_data, cache_hit = self._get_from_cache('data', user_id, collection_id, service_type)
            if cache_hit:
                logger.info(f"✅ 서비스 데이터 캐시 히트 성공: {collection_id}/{service_type}")
                return service_data
            
            # 전체 데이터 조회
            collection_data = self.get_collection_data(user_id, collection_id)
            if not collection_data or 'services_data' not in collection_data:
                logger.warning(f"❌ 수집 ID {collection_id}의 데이터를 찾을 수 없습니다.")
                return None
            
            # 해당 서비스 데이터만 추출
            if service_type in collection_data['services_data']:
                service_data = collection_data['services_data'][service_type]
                
                # 캐시에 저장
                self._set_in_cache('data', user_id, service_data, collection_id, service_type)
                logger.info(f"💾 서비스 데이터 캐시 저장 완료: {collection_id}/{service_type}")
                
                return service_data
            else:
                logger.warning(f"❌ 수집 ID {collection_id}에 서비스 {service_type} 데이터가 없습니다.")
                return None
                
        except Exception as e:
            logger.error(f"❌ 서비스 데이터 조회 중 오류 발생: {str(e)}")
            return None
    
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
            
            # 캐시 무효화
            self._invalidate_cache('collections', user_id)
            self._invalidate_cache('all', user_id, collection_id)
            
            logger.info(f"사용자 {user_id}의 수집 데이터 {collection_id}를 삭제했습니다.")
            return True
            
        except Exception as e:
            logger.error(f"수집 데이터 삭제 중 오류 발생: {str(e)}")
            return False