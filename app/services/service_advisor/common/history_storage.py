import boto3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
from config import Config

logger = logging.getLogger(__name__)

class AdvisorHistoryStorage:
    """
    서비스 어드바이저 검사 기록을 S3에 저장하고 관리하는 클래스
    """
    
    def __init__(self, region=None):
        """
        AdvisorHistoryStorage 클래스 초기화
        
        Args:
            region: AWS 리전 (기본값: Config에서 가져옴)
        """
        self.region = region or Config.AWS_REGION
        self.bucket_name = Config.DATA_BUCKET_NAME
        
        # S3 클라이언트 생성
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=Config.AWS_ACCESS_KEY,
            aws_secret_access_key=Config.AWS_SECRET_KEY
        )
    
    def _get_history_prefix(self, username: str, service_name: str = None) -> str:
        """
        기록 저장 경로 접두사 생성
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름 (선택 사항)
            
        Returns:
            str: S3 경로 접두사
        """
        base_prefix = f"advisor_history/{username}/"
        if service_name:
            return f"{base_prefix}{service_name}/"
        return base_prefix
    
    def _get_history_key(self, username: str, service_name: str, check_id: str) -> str:
        """
        기록 파일 키 생성 - 검사 항목별로 최신 결과를 저장
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름
            check_id: 검사 ID
            
        Returns:
            str: S3 파일 키
        """
        # 검사 항목별로 고정된 키 사용 (최신 결과만 유지)
        return f"{self._get_history_prefix(username, service_name)}{check_id}/latest.json"
    
    def _get_history_archive_key(self, username: str, service_name: str, check_id: str) -> str:
        """
        기록 아카이브 파일 키 생성 - 모든 검사 결과 보관
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름
            check_id: 검사 ID
            
        Returns:
            str: S3 파일 키
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{self._get_history_prefix(username, service_name)}{check_id}/archive/{timestamp}.json"
    
    def save_check_result(self, username: str, service_name: str, check_id: str, result: Dict[str, Any]) -> bool:
        """
        검사 결과를 S3에 저장
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름
            check_id: 검사 ID
            result: 검사 결과 데이터
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 메타데이터 추가
            timestamp = datetime.now().isoformat()
            result_with_meta = {
                "metadata": {
                    "username": username,
                    "service_name": service_name,
                    "check_id": check_id,
                    "timestamp": timestamp,
                },
                "result": result
            }
            
            # 한글 인코딩 문제 해결을 위해 ensure_ascii=False 설정
            json_data = json.dumps(result_with_meta, ensure_ascii=False)
            
            # 최신 결과 저장 (검사 항목별로 최신 결과만 유지)
            latest_key = self._get_history_key(username, service_name, check_id)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=latest_key,
                Body=json_data.encode('utf-8'),  # UTF-8로 명시적 인코딩
                ContentType='application/json; charset=utf-8'  # 문자셋 명시
            )
            
            # 아카이브에도 저장 (모든 검사 결과 보관)
            archive_key = self._get_history_archive_key(username, service_name, check_id)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=archive_key,
                Body=json_data.encode('utf-8'),  # UTF-8로 명시적 인코딩
                ContentType='application/json; charset=utf-8'  # 문자셋 명시
            )
            
            logger.info(f"검사 결과 저장 완료: {latest_key} (아카이브: {archive_key})")
            return True
            
        except Exception as e:
            logger.error(f"검사 결과 저장 중 오류 발생: {str(e)}")
            return False
    
    def get_check_history(self, username: str, service_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        사용자의 검사 기록 조회
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름 (선택 사항)
            limit: 최대 조회 개수
            
        Returns:
            List[Dict[str, Any]]: 검사 기록 목록
        """
        try:
            prefix = self._get_history_prefix(username, service_name)
            logger.info(f"검사 기록 조회: 사용자={username}, 서비스={service_name}, 접두사={prefix}")
            
            # 모든 아카이브 결과 조회
            history_list = []
            
            # S3 객체 목록 조회 (최대 1000개까지 가져옴)
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=1000
            )
            
            if 'Contents' in response:
                # 모든 객체 처리
                for obj in response['Contents']:
                    key = obj['Key']
                    
                    # 아카이브 파일만 처리 (latest.json 제외)
                    if 'archive' in key and key.endswith('.json'):
                        try:
                            # 객체 내용 가져오기
                            obj_response = self.s3_client.get_object(
                                Bucket=self.bucket_name,
                                Key=key
                            )
                            
                            data = json.loads(obj_response['Body'].read().decode('utf-8'))
                            
                            # 기록 정보 추출
                            metadata = data.get('metadata', {})
                            result_summary = {
                                'key': key,
                                'service_name': metadata.get('service_name', ''),
                                'check_id': metadata.get('check_id', ''),
                                'timestamp': metadata.get('timestamp', ''),
                                'status': data.get('result', {}).get('status', ''),
                                'message': data.get('result', {}).get('message', '')
                            }
                            
                            history_list.append(result_summary)
                            
                        except Exception as e:
                            logger.error(f"기록 항목 처리 중 오류 발생: {key} - {str(e)}")
            
            # 최신 순으로 정렬
            history_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # 제한된 개수만 반환
            return history_list[:limit]
            
        except Exception as e:
            logger.error(f"검사 기록 조회 중 오류 발생: {str(e)}")
            return []
    
    def _list_service_folders(self, prefix: str) -> List[str]:
        """
        서비스 폴더 목록 조회
        
        Args:
            prefix: 기준 경로
            
        Returns:
            List[str]: 서비스 폴더 목록
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            if 'CommonPrefixes' in response:
                return [p.get('Prefix') for p in response.get('CommonPrefixes', [])]
            return []
        except Exception as e:
            logger.error(f"서비스 폴더 목록 조회 중 오류 발생: {str(e)}")
            return []
    
    def _list_check_folders(self, prefix: str) -> List[str]:
        """
        검사 항목 폴더 목록 조회
        
        Args:
            prefix: 기준 경로
            
        Returns:
            List[str]: 검사 항목 폴더 목록
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            if 'CommonPrefixes' in response:
                return [p.get('Prefix') for p in response.get('CommonPrefixes', [])]
            return []
        except Exception as e:
            logger.error(f"검사 항목 폴더 목록 조회 중 오류 발생: {str(e)}")
            return []
    
    def _get_latest_check_result(self, username: str, service_name: str, check_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 검사 항목의 최신 결과 조회
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름
            check_id: 검사 ID
            
        Returns:
            Optional[Dict[str, Any]]: 검사 결과 요약 또는 None
        """
        try:
            key = self._get_history_key(username, service_name, check_id)
            
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                
                data = json.loads(response['Body'].read().decode('utf-8'))
                metadata = data.get('metadata', {})
                
                return {
                    'key': key,
                    'service_name': metadata.get('service_name', ''),
                    'check_id': metadata.get('check_id', ''),
                    'timestamp': metadata.get('timestamp', ''),
                    'status': data.get('result', {}).get('status', ''),
                    'message': data.get('result', {}).get('message', '')
                }
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.warning(f"최신 검사 결과를 찾을 수 없음: {key}")
                    return None
                else:
                    raise
        except Exception as e:
            logger.error(f"최신 검사 결과 조회 중 오류 발생: {str(e)}")
            return None
    
    def get_check_result(self, key: str) -> Optional[Dict[str, Any]]:
        """
        특정 검사 결과 상세 조회
        
        Args:
            key: S3 객체 키
            
        Returns:
            Optional[Dict[str, Any]]: 검사 결과 또는 None
        """
        try:
            # S3에서 객체 가져오기
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            # UTF-8로 명시적 디코딩하여 한글 처리
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            return data
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"검사 결과를 찾을 수 없음: {key}")
                return None
            else:
                logger.error(f"검사 결과 조회 중 오류 발생: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"검사 결과 조회 중 오류 발생: {str(e)}")
            return None
    
    def get_latest_check_result(self, username: str, service_name: str, check_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 검사 항목의 최신 결과 상세 조회
        
        Args:
            username: 사용자 ID
            service_name: 서비스 이름
            check_id: 검사 ID
            
        Returns:
            Optional[Dict[str, Any]]: 검사 결과 또는 None
        """
        key = self._get_history_key(username, service_name, check_id)
        return self.get_check_result(key)
    
    def delete_check_result(self, key: str) -> bool:
        """
        특정 검사 결과 삭제
        
        Args:
            key: S3 객체 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # S3에서 객체 삭제
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"검사 결과 삭제 완료: {key}")
            return True
            
        except Exception as e:
            logger.error(f"검사 결과 삭제 중 오류 발생: {str(e)}")
            return False