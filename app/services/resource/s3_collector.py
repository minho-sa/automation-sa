from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from app.services.resource.common.base_collector import BaseCollector
from app.services.resource.common.resource_model import S3Bucket

class S3Collector(BaseCollector):
    """
    S3 버킷 데이터 수집기
    """
    
    def _init_clients(self) -> None:
        """
        필요한 AWS 클라이언트 초기화
        """
        self.s3_client = self.get_client('s3')
        self.s3_control = self.get_client('s3control')
    
    def collect(self, collection_id: str = None) -> Dict[str, Any]:
        """
        S3 버킷 데이터 수집
        
        Args:
            collection_id: 수집 ID (선택 사항)
            
        Returns:
            Dict[str, Any]: 수집된 S3 데이터
        """
        log_prefix = f"[{collection_id}] " if collection_id else ""
        self.logger.info(f"{log_prefix}S3 데이터 수집 시작")
        
        try:
            response = self.s3_client.list_buckets()
            buckets = []
            
            self.logger.info(f"{log_prefix}S3 버킷 {len(response['Buckets'])}개 발견")
            
            for bucket_data in response['Buckets']:
                # S3Bucket 객체 생성
                bucket = self._process_bucket(bucket_data, log_prefix)
                if bucket:
                    # datetime 객체를 문자열로 변환
                    bucket_dict = bucket.to_dict()
                    if 'creation_date' in bucket_dict and isinstance(bucket_dict['creation_date'], datetime):
                        bucket_dict['creation_date'] = bucket_dict['creation_date'].isoformat()
                    buckets.append(bucket_dict)
            
            result = {'buckets': buckets}
            self.logger.info(f"{log_prefix}S3 버킷 {len(buckets)}개 데이터 수집 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"{log_prefix}S3 데이터 수집 중 오류 발생: {str(e)}")
            return {'error': str(e)}
    
    def _process_bucket(self, bucket_data: Dict[str, Any], log_prefix: str) -> Optional[S3Bucket]:
        """
        S3 버킷 데이터 처리
        
        Args:
            bucket_data: S3 버킷 원시 데이터
            log_prefix: 로그 접두사
            
        Returns:
            Optional[S3Bucket]: 처리된 S3 버킷 객체 또는 None
        """
        bucket_name = bucket_data['Name']
        self.logger.debug(f"{log_prefix}버킷 처리 중: {bucket_name}")
        
        try:
            # 버킷 리전 확인
            location = self.s3_client.get_bucket_location(Bucket=bucket_name)
            region = location['LocationConstraint'] or 'us-east-1'  # None인 경우 us-east-1
            
            # 기본 버킷 정보로 객체 생성
            bucket = S3Bucket(
                id=bucket_name,
                name=bucket_name,
                region=region,
                creation_date=bucket_data.get('CreationDate')
            )
            
            # 태그 수집
            self._collect_tags(bucket, log_prefix)
            
            # 버전 관리 상태 확인
            self._check_versioning(bucket, log_prefix)
            
            # 공개 액세스 설정 확인
            self._check_public_access(bucket, log_prefix)
            
            # 암호화 설정 확인
            self._check_encryption(bucket, log_prefix)
            
            # 수명 주기 규칙 확인
            self._check_lifecycle_rules(bucket, log_prefix)
            
            # 버킷 크기 및 객체 수 확인 (CloudWatch 메트릭 사용)
            self._collect_size_metrics(bucket, log_prefix)
            
            return bucket
            
        except Exception as e:
            self.logger.error(f"{log_prefix}버킷 처리 중 오류 발생: {bucket_name} - {str(e)}")
            return None
    
    def _collect_tags(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 태그 수집
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_client.get_bucket_tagging(Bucket=bucket.name)
            if 'TagSet' in response:
                bucket.tags = [{'Key': tag['Key'], 'Value': tag['Value']} for tag in response['TagSet']]
        except Exception as e:
            # 태그가 없는 경우 NoSuchTagSet 예외 발생 (정상)
            if 'NoSuchTagSet' not in str(e):
                self.logger.error(f"{log_prefix}태그 수집 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _check_versioning(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 버전 관리 상태 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_client.get_bucket_versioning(Bucket=bucket.name)
            bucket.versioning_enabled = response.get('Status') == 'Enabled'
        except Exception as e:
            self.logger.error(f"{log_prefix}버전 관리 상태 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _check_public_access(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 공개 액세스 설정 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            # 버킷 정책 확인
            try:
                self.s3_client.get_bucket_policy(Bucket=bucket.name)
                # 정책이 있으면 추가 확인 필요
                bucket.public_access = True
            except Exception as e:
                if 'NoSuchBucketPolicy' in str(e):
                    # 정책이 없으면 공개 액세스 아님
                    bucket.public_access = False
            
            # 퍼블릭 액세스 차단 설정 확인
            try:
                response = self.s3_client.get_public_access_block(Bucket=bucket.name)
                block_config = response.get('PublicAccessBlockConfiguration', {})
                
                # 모든 퍼블릭 액세스 차단 설정이 True이면 비공개
                if (block_config.get('BlockPublicAcls', False) and
                    block_config.get('BlockPublicPolicy', False) and
                    block_config.get('IgnorePublicAcls', False) and
                    block_config.get('RestrictPublicBuckets', False)):
                    bucket.public_access = False
            except Exception:
                # 설정이 없으면 기본값 유지
                pass
                
        except Exception as e:
            self.logger.error(f"{log_prefix}공개 액세스 설정 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _check_encryption(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 암호화 설정 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_client.get_bucket_encryption(Bucket=bucket.name)
            if 'ServerSideEncryptionConfiguration' in response:
                bucket.encryption_enabled = True
        except Exception as e:
            if 'ServerSideEncryptionConfigurationNotFoundError' in str(e):
                bucket.encryption_enabled = False
            else:
                self.logger.error(f"{log_prefix}암호화 설정 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _check_lifecycle_rules(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 수명 주기 규칙 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_client.get_bucket_lifecycle_configuration(Bucket=bucket.name)
            if 'Rules' in response:
                # 필요한 정보만 추출
                for rule in response['Rules']:
                    if rule.get('Status') == 'Enabled':
                        rule_info = {
                            'id': rule.get('ID', ''),
                            'prefix': rule.get('Prefix', ''),
                            'has_expiration': 'Expiration' in rule,
                            'has_transition': 'Transitions' in rule
                        }
                        bucket.lifecycle_rules.append(rule_info)
        except Exception as e:
            if 'NoSuchLifecycleConfiguration' not in str(e):
                self.logger.error(f"{log_prefix}수명 주기 규칙 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _collect_size_metrics(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 크기 및 객체 수 수집
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            # 버킷 크기 추정 (첫 100개 객체만)
            paginator = self.s3_client.get_paginator('list_objects_v2')
            total_size = 0
            object_count = 0
            
            # 최대 1페이지만 조회 (성능 최적화)
            for page in paginator.paginate(Bucket=bucket.name, MaxKeys=100):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj.get('Size', 0)
                        object_count += 1
                break  # 첫 페이지만 처리
            
            bucket.size_bytes = total_size
            bucket.object_count = object_count
            
        except Exception as e:
            self.logger.error(f"{log_prefix}버킷 크기 수집 중 오류 발생: {bucket.name} - {str(e)}")