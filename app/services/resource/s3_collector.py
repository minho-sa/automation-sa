from datetime import datetime
from typing import Dict, List, Any, Optional
import json
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
            
            # 스토리지 클래스별 요약 정보
            storage_class_summary = {
                'STANDARD': {'count': 0, 'size_bytes': 0},
                'INTELLIGENT_TIERING': {'count': 0, 'size_bytes': 0},
                'STANDARD_IA': {'count': 0, 'size_bytes': 0},
                'ONEZONE_IA': {'count': 0, 'size_bytes': 0},
                'GLACIER': {'count': 0, 'size_bytes': 0},
                'DEEP_ARCHIVE': {'count': 0, 'size_bytes': 0}
            }
            
            # 리전별 버킷 분포
            region_distribution = {}
            
            for bucket_data in response['Buckets']:
                # S3Bucket 객체 생성
                bucket = self._process_bucket(bucket_data, log_prefix)
                if bucket:
                    # datetime 객체를 문자열로 변환
                    bucket_dict = bucket.to_dict()
                    if 'creation_date' in bucket_dict and isinstance(bucket_dict['creation_date'], datetime):
                        bucket_dict['creation_date'] = bucket_dict['creation_date'].isoformat()
                    
                    # 리전별 버킷 분포 업데이트
                    region = bucket.region
                    if region not in region_distribution:
                        region_distribution[region] = {
                            'count': 0,
                            'public': 0,
                            'private': 0
                        }
                    
                    region_distribution[region]['count'] += 1
                    if bucket.public_access:
                        region_distribution[region]['public'] += 1
                    else:
                        region_distribution[region]['private'] += 1
                    
                    # 스토리지 클래스별 요약 정보 업데이트
                    for storage_class, data in bucket_dict.get('storage_class_distribution', {}).items():
                        if storage_class in storage_class_summary:
                            storage_class_summary[storage_class]['count'] += data.get('count', 0)
                            storage_class_summary[storage_class]['size_bytes'] += data.get('size_bytes', 0)
                    
                    buckets.append(bucket_dict)
            
            result = {
                'buckets': buckets,
                'summary': {
                    'total_buckets': len(buckets),
                    'public_buckets': sum(1 for b in buckets if b.get('public_access', False)),
                    'encrypted_buckets': sum(1 for b in buckets if b.get('encryption_enabled', False)),
                    'versioning_enabled': sum(1 for b in buckets if b.get('versioning_enabled', False)),
                    'storage_class_summary': storage_class_summary,
                    'region_distribution': region_distribution
                }
            }
            
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
            
            # 버킷 정책 확인
            self._check_bucket_policy(bucket, log_prefix)
            
            # CORS 설정 확인
            self._check_cors_rules(bucket, log_prefix)
            
            # 웹사이트 설정 확인
            self._check_website_config(bucket, log_prefix)
            
            # 로깅 설정 확인
            self._check_logging_config(bucket, log_prefix)
            
            # 스토리지 클래스별 객체 분포 확인
            self._collect_storage_class_distribution(bucket, log_prefix)
            
            # 액세스 포인트 확인
            self._collect_access_points(bucket, log_prefix)
            
            # 버킷 크기 및 객체 수 확인
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
                    rule_info = {
                        'id': rule.get('ID', ''),
                        'status': rule.get('Status', ''),
                        'prefix': rule.get('Prefix', ''),
                        'filter': rule.get('Filter', {}),
                        'expiration': rule.get('Expiration', {}),
                        'transitions': rule.get('Transitions', []),
                        'noncurrent_version_transitions': rule.get('NoncurrentVersionTransitions', []),
                        'noncurrent_version_expiration': rule.get('NoncurrentVersionExpiration', {})
                    }
                    bucket.lifecycle_rules.append(rule_info)
        except Exception as e:
            if 'NoSuchLifecycleConfiguration' not in str(e):
                self.logger.error(f"{log_prefix}수명 주기 규칙 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _check_bucket_policy(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 정책 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_client.get_bucket_policy(Bucket=bucket.name)
            if 'Policy' in response:
                policy_str = response['Policy']
                bucket.policy = json.loads(policy_str)
        except Exception as e:
            if 'NoSuchBucketPolicy' not in str(e):
                self.logger.error(f"{log_prefix}버킷 정책 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _check_cors_rules(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 CORS 설정 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_client.get_bucket_cors(Bucket=bucket.name)
            if 'CORSRules' in response:
                bucket.cors_rules = response['CORSRules']
        except Exception as e:
            if 'NoSuchCORSConfiguration' not in str(e):
                self.logger.error(f"{log_prefix}CORS 설정 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _check_website_config(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 웹사이트 설정 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_client.get_bucket_website(Bucket=bucket.name)
            bucket.website_enabled = True
            bucket.website_config = response
        except Exception as e:
            if 'NoSuchWebsiteConfiguration' not in str(e):
                self.logger.error(f"{log_prefix}웹사이트 설정 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _check_logging_config(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 로깅 설정 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_client.get_bucket_logging(Bucket=bucket.name)
            if 'LoggingEnabled' in response:
                bucket.logging_enabled = True
                bucket.logging_target_bucket = response['LoggingEnabled'].get('TargetBucket', '')
                bucket.logging_target_prefix = response['LoggingEnabled'].get('TargetPrefix', '')
        except Exception as e:
            self.logger.error(f"{log_prefix}로깅 설정 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _collect_storage_class_distribution(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        스토리지 클래스별 객체 분포 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            # 스토리지 클래스 초기화
            storage_classes = [
                'STANDARD', 'INTELLIGENT_TIERING', 'STANDARD_IA', 
                'ONEZONE_IA', 'GLACIER', 'DEEP_ARCHIVE'
            ]
            
            for storage_class in storage_classes:
                bucket.storage_class_distribution[storage_class] = {
                    'count': 0,
                    'size_bytes': 0
                }
            
            # 객체 목록 조회 (최대 1000개)
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=bucket.name,
                MaxKeys=1000
            )
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        storage_class = obj.get('StorageClass', 'STANDARD')
                        size = obj.get('Size', 0)
                        
                        if storage_class in bucket.storage_class_distribution:
                            bucket.storage_class_distribution[storage_class]['count'] += 1
                            bucket.storage_class_distribution[storage_class]['size_bytes'] += size
                        else:
                            bucket.storage_class_distribution[storage_class] = {
                                'count': 1,
                                'size_bytes': size
                            }
                
                # 최대 1페이지만 처리 (성능 최적화)
                break
                
        except Exception as e:
            self.logger.error(f"{log_prefix}스토리지 클래스 분포 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _collect_access_points(self, bucket: S3Bucket, log_prefix: str) -> None:
        """
        버킷 액세스 포인트 확인
        
        Args:
            bucket: S3 버킷 객체
            log_prefix: 로그 접두사
        """
        try:
            response = self.s3_control.list_access_points(
                AccountId=self._get_account_id(),
                Bucket=bucket.name
            )
            
            if 'AccessPointList' in response:
                for ap in response['AccessPointList']:
                    access_point = {
                        'name': ap.get('Name'),
                        'network_origin': ap.get('NetworkOrigin'),
                        'vpc_configuration': ap.get('VpcConfiguration', {}),
                        'bucket': ap.get('Bucket'),
                        'access_point_arn': ap.get('AccessPointArn')
                    }
                    bucket.access_points.append(access_point)
        except Exception as e:
            self.logger.error(f"{log_prefix}액세스 포인트 확인 중 오류 발생: {bucket.name} - {str(e)}")
    
    def _get_account_id(self) -> str:
        """
        현재 AWS 계정 ID 조회
        
        Returns:
            str: AWS 계정 ID
        """
        try:
            sts_client = self.get_client('sts')
            return sts_client.get_caller_identity()['Account']
        except Exception as e:
            self.logger.error(f"계정 ID 조회 중 오류 발생: {str(e)}")
            return ''
    
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