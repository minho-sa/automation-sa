import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import hashlib
import time

class ResourceDataStorage:
    """
    리소스 데이터 저장소 클래스
    """
    
    def __init__(self, region: str = None):
        """
        초기화
        
        Args:
            region: AWS 리전 (선택 사항)
        """
        self.logger = logging.getLogger(__name__)
        self.region = region or 'ap-northeast-2'
        self.bucket_name = 'saltware-console-data'
        self.s3_client = boto3.client('s3', region_name=self.region)
        
        # 메모리 캐시
        self.cache = {
            'collections': {},  # 컬렉션 목록 캐시
            'metadata': {},     # 메타데이터 캐시
            'data': {}          # 데이터 캐시
        }
        
        # 캐시 만료 시간 (초)
        self.cache_ttl = 300  # 5분
        
        # 캐시 타임스탬프
        self.cache_timestamp = {
            'collections': {},
            'metadata': {},
            'data': {}
        }
        
        self.logger.info(f"ResourceDataStorage 초기화: 버킷={self.bucket_name}, 리전={self.region}")
        
        # S3 버킷 접근 확인
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.logger.info(f"S3 버킷 {self.bucket_name} 접근 확인 완료")
        except ClientError as e:
            self.logger.error(f"S3 버킷 접근 오류: {str(e)}")
    
    def save_resource_data(self, username: str, service_name: str, collection_id: str, data: Dict[str, Any]) -> bool:
        """
        리소스 데이터 저장
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름
            collection_id: 수집 ID
            data: 저장할 데이터
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 메타데이터 생성
            metadata = {
                'username': username,
                'service_name': service_name,
                'collection_id': collection_id,
                'timestamp': datetime.now().isoformat(),
                'data_size': len(str(data))
            }
            
            # JSON 직렬화 가능한지 확인
            try:
                json.dumps(data)
            except TypeError as e:
                self.logger.error(f"리소스 데이터 저장 중 오류 발생: {str(e)}")
                
                # datetime 객체를 문자열로 변환
                self._convert_datetime_to_str(data)
                
                # 다시 시도
                try:
                    json.dumps(data)
                except TypeError as e:
                    self.logger.error(f"리소스 데이터 변환 후에도 오류 발생: {str(e)}")
                    return False
            
            # 데이터 저장 경로
            data_key = f"users/{username}/collections/{collection_id}/{service_name}.json"
            metadata_key = f"users/{username}/collections/{collection_id}/metadata.json"
            
            # 데이터 저장
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=data_key,
                Body=json.dumps(data),
                ContentType='application/json'
            )
            
            # 메타데이터 저장
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata),
                ContentType='application/json'
            )
            
            # 캐시 무효화
            self._invalidate_cache('collections', username)
            
            return True
        except Exception as e:
            self.logger.error(f"리소스 데이터 저장 중 오류 발생: {str(e)}")
            return False
    
    def get_resource_data(self, username: str, service_name: str, collection_id: str) -> Optional[Dict[str, Any]]:
        """
        리소스 데이터 조회
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름
            collection_id: 수집 ID
            
        Returns:
            Optional[Dict[str, Any]]: 조회된 데이터 또는 None
        """
        try:
            # 캐시 확인
            cache_key = f"{username}:{collection_id}:{service_name}"
            if self._check_cache('data', username, cache_key):
                self.logger.info(f"✅ 데이터 캐시 히트: {cache_key}")
                return self.cache['data'][username][cache_key]
            
            # 데이터 조회 경로
            data_key = f"users/{username}/collections/{collection_id}/{service_name}.json"
            metadata_key = f"users/{username}/collections/{collection_id}/metadata.json"
            
            # 데이터 조회
            try:
                data_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=data_key)
                data = json.loads(data_response['Body'].read().decode('utf-8'))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    self.logger.warning(f"데이터 파일을 찾을 수 없음: {data_key}")
                    data = {}
                else:
                    raise
            
            # 메타데이터 조회
            try:
                metadata_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    self.logger.warning(f"메타데이터 파일을 찾을 수 없음: {metadata_key}")
                    metadata = {}
                else:
                    raise
            
            # 결과 구성
            result = {
                'data': data,
                'metadata': metadata
            }
            
            # 캐시 저장
            self._set_in_cache('data', username, result, cache_key)
            
            return result
        except Exception as e:
            self.logger.error(f"리소스 데이터 조회 중 오류 발생: {str(e)}")
            return None
    
    def list_collections(self, username: str, service_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        수집 목록 조회
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름 (선택 사항)
            limit: 최대 조회 개수
            
        Returns:
            List[Dict[str, Any]]: 수집 목록
        """
        try:
            # 캐시 확인
            cache_key = f"{username}"
            if self._check_cache('collections', username, cache_key):
                self.logger.info(f"✅ 컬렉션 목록 캐시 히트: {username}")
                collections = self.cache['collections'][username][cache_key]
                
                # 서비스 이름으로 필터링
                if service_name:
                    collections = [c for c in collections if service_name in c.get('selected_services', [])]
                
                # 최대 개수 제한
                return collections[:limit]
            
            self.logger.info(f"❌ 컬렉션 목록 캐시 히트 실패: {username}")
            self.logger.info(f"📥 S3에서 컬렉션 목록 조회 시작")
            
            # 메타데이터 조회 경로
            prefix = f"users/{username}/collections/"
            
            # 메타데이터 조회
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            collections = []
            
            # 컬렉션 ID 추출
            if 'CommonPrefixes' in response:
                for common_prefix in response['CommonPrefixes']:
                    collection_prefix = common_prefix['Prefix']
                    collection_id = collection_prefix.split('/')[-2]
                    
                    # 메타데이터 조회
                    metadata_key = f"{collection_prefix}metadata.json"
                    try:
                        metadata_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
                        metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
                        
                        # 서비스 파일 목록 조회
                        service_files = self.s3_client.list_objects_v2(
                            Bucket=self.bucket_name,
                            Prefix=collection_prefix,
                            Delimiter='/'
                        )
                        
                        # 서비스 이름 추출
                        selected_services = []
                        if 'Contents' in service_files:
                            for content in service_files['Contents']:
                                key = content['Key']
                                if key.endswith('.json') and not key.endswith('metadata.json'):
                                    service_name = key.split('/')[-1].replace('.json', '')
                                    selected_services.append(service_name)
                        
                        # 컬렉션 정보 구성
                        collection_info = {
                            'collection_id': collection_id,
                            'timestamp': metadata.get('timestamp', ''),
                            'selected_services': selected_services
                        }
                        
                        collections.append(collection_info)
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'NoSuchKey':
                            self.logger.warning(f"메타데이터 파일을 찾을 수 없음: {metadata_key}")
                        else:
                            raise
            
            # 시간순 정렬 (최신순)
            collections.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # 캐시 저장
            self._set_in_cache('collections', username, collections, cache_key)
            
            self.logger.info(f"📊 데이터 소스: S3 (컬렉션 목록)")
            
            # 서비스 이름으로 필터링
            if service_name:
                collections = [c for c in collections if service_name in c.get('selected_services', [])]
            
            # 최대 개수 제한
            return collections[:limit]
        except Exception as e:
            self.logger.error(f"수집 목록 조회 중 오류 발생: {str(e)}")
            return []
    
    def delete_collection(self, username: str, collection_id: str) -> bool:
        """
        수집 데이터 삭제
        
        Args:
            username: 사용자 ID
            collection_id: 수집 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 삭제 경로
            prefix = f"users/{username}/collections/{collection_id}/"
            
            # 삭제할 객체 목록 조회
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            # 객체가 없는 경우
            if 'Contents' not in response:
                self.logger.warning(f"삭제할 객체가 없음: {prefix}")
                return False
            
            # 객체 삭제
            delete_objects = {'Objects': [{'Key': obj['Key']} for obj in response['Contents']]}
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete=delete_objects
            )
            
            # 캐시 무효화
            self._invalidate_cache('collections', username)
            self._invalidate_cache('data', username, f"{username}:{collection_id}")
            
            return True
        except Exception as e:
            self.logger.error(f"수집 데이터 삭제 중 오류 발생: {str(e)}")
            return False
    
    def _check_cache(self, cache_type: str, username: str, cache_key: str = None) -> bool:
        """
        캐시 확인
        
        Args:
            cache_type: 캐시 유형 ('collections', 'metadata', 'data')
            username: 사용자 ID
            cache_key: 캐시 키 (선택 사항)
            
        Returns:
            bool: 캐시 존재 여부
        """
        # 사용자 캐시 초기화
        if username not in self.cache[cache_type]:
            self.cache[cache_type][username] = {}
            self.cache_timestamp[cache_type][username] = {}
            return False
        
        # 캐시 키가 없는 경우
        if cache_key is None:
            cache_key = username
        
        # 캐시 존재 여부 확인
        if cache_key not in self.cache[cache_type][username]:
            return False
        
        # 캐시 만료 확인
        if cache_key not in self.cache_timestamp[cache_type][username]:
            return False
        
        # 캐시 만료 시간 확인
        if time.time() - self.cache_timestamp[cache_type][username][cache_key] > self.cache_ttl:
            # 캐시 삭제
            del self.cache[cache_type][username][cache_key]
            del self.cache_timestamp[cache_type][username][cache_key]
            return False
        
        return True
    
    def _set_in_cache(self, cache_type: str, username: str, data: Any, cache_key: str = None, sub_key: str = None) -> None:
        """
        캐시 저장
        
        Args:
            cache_type: 캐시 유형 ('collections', 'metadata', 'data')
            username: 사용자 ID
            data: 저장할 데이터
            cache_key: 캐시 키 (선택 사항)
            sub_key: 하위 키 (선택 사항)
        """
        # 사용자 캐시 초기화
        if username not in self.cache[cache_type]:
            self.cache[cache_type][username] = {}
            self.cache_timestamp[cache_type][username] = {}
        
        # 캐시 키가 없는 경우
        if cache_key is None:
            cache_key = username
        
        # 하위 키가 있는 경우
        if sub_key:
            if cache_key not in self.cache[cache_type][username]:
                self.cache[cache_type][username][cache_key] = {}
            
            self.cache[cache_type][username][cache_key][sub_key] = data
        else:
            self.cache[cache_type][username][cache_key] = data
        
        # 캐시 타임스탬프 갱신
        self.cache_timestamp[cache_type][username][cache_key] = time.time()
        
        self.logger.info(f"💾 {cache_type} 캐시 저장 완료: {username}")
    
    def _invalidate_cache(self, cache_type: str, username: str, cache_key_prefix: str = None) -> None:
        """
        캐시 무효화
        
        Args:
            cache_type: 캐시 유형 ('collections', 'metadata', 'data')
            username: 사용자 ID
            cache_key_prefix: 캐시 키 접두사 (선택 사항)
        """
        # 사용자 캐시가 없는 경우
        if username not in self.cache[cache_type]:
            return
        
        # 캐시 키 접두사가 있는 경우
        if cache_key_prefix:
            # 접두사로 시작하는 모든 캐시 키 삭제
            keys_to_delete = []
            for key in self.cache[cache_type][username]:
                if key.startswith(cache_key_prefix):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.cache[cache_type][username][key]
                if key in self.cache_timestamp[cache_type][username]:
                    del self.cache_timestamp[cache_type][username][key]
        else:
            # 모든 캐시 삭제
            self.cache[cache_type][username] = {}
            self.cache_timestamp[cache_type][username] = {}
    
    def _convert_datetime_to_str(self, data: Any) -> None:
        """
        데이터 내의 datetime 객체를 문자열로 변환
        
        Args:
            data: 변환할 데이터
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, datetime):
                    data[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    self._convert_datetime_to_str(value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, datetime):
                    data[i] = item.isoformat()
                elif isinstance(item, (dict, list)):
                    self._convert_datetime_to_str(item)