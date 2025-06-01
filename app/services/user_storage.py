import boto3
import json
import uuid
import hashlib
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError
from config import Config

logger = logging.getLogger(__name__)

class UserStorage:
    """S3를 사용하여 사용자 정보를 관리하는 클래스"""
    
    def __init__(self, region=None):
        """
        UserStorage 클래스 초기화
        
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
    
    def _get_users_prefix(self):
        """사용자 정보 저장 경로 접두사"""
        return "users_data/"
    
    def _get_user_key(self, username):
        """사용자 정보 파일 키"""
        return f"{self._get_users_prefix()}{username}.json"
    
    def _hash_password(self, password, salt=None):
        """
        비밀번호를 안전하게 해시화
        
        Args:
            password: 해시화할 비밀번호
            salt: 사용할 솔트 (없으면 새로 생성)
            
        Returns:
            (해시된 비밀번호, 솔트)
        """
        if salt is None:
            salt = os.urandom(32)  # 32바이트 랜덤 솔트 생성
        
        # PBKDF2 알고리즘으로 비밀번호 해시화 (100,000회 반복)
        key = hashlib.pbkdf2_hmac(
            'sha256',  # 해시 알고리즘
            password.encode('utf-8'),  # 비밀번호를 바이트로 변환
            salt,  # 솔트
            100000,  # 반복 횟수
            dklen=128  # 결과 길이
        )
        
        return key, salt
    
    def register_user(self, username, password, role_arn):
        """
        새 사용자 등록
        
        Args:
            username: 사용자 ID
            password: 비밀번호
            role_arn: AWS 자격증명용 ARN
            
        Returns:
            성공 여부와 메시지
        """
        try:
            # 사용자 ID 중복 확인
            if self.user_exists(username):
                return False, "이미 존재하는 사용자 ID입니다."
            
            # 비밀번호 해시화
            key, salt = self._hash_password(password)
            
            # 사용자 정보 생성
            user_data = {
                "username": username,
                "password_hash": key.hex(),  # 바이너리를 16진수 문자열로 변환
                "salt": salt.hex(),
                "role_arn": role_arn,
                "created_at": datetime.now().isoformat(),
                "last_login": None
            }
            
            # S3에 저장
            user_key = self._get_user_key(username)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=user_key,
                Body=json.dumps(user_data),
                ContentType='application/json'
            )
            
            logger.info(f"사용자 등록 성공: {username}")
            return True, "사용자 등록이 완료되었습니다."
            
        except Exception as e:
            logger.error(f"사용자 등록 중 오류 발생: {str(e)}")
            return False, f"사용자 등록 중 오류가 발생했습니다: {str(e)}"
    
    def user_exists(self, username):
        """
        사용자 ID 존재 여부 확인
        
        Args:
            username: 확인할 사용자 ID
            
        Returns:
            존재 여부
        """
        try:
            user_key = self._get_user_key(username)
            self.s3_client.head_object(Bucket=self.bucket_name, Key=user_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"사용자 존재 여부 확인 중 오류: {str(e)}")
                raise
    
    def authenticate_user(self, username, password):
        """
        사용자 인증
        
        Args:
            username: 사용자 ID
            password: 비밀번호
            
        Returns:
            (인증 성공 여부, 사용자 정보 또는 오류 메시지)
        """
        try:
            # 사용자 정보 가져오기
            user_data = self.get_user(username)
            
            if not user_data:
                return False, "사용자를 찾을 수 없습니다."
            
            # 비밀번호 검증
            stored_hash = bytes.fromhex(user_data["password_hash"])
            salt = bytes.fromhex(user_data["salt"])
            
            key, _ = self._hash_password(password, salt)
            
            if key == stored_hash:
                # 로그인 시간 업데이트
                user_data["last_login"] = datetime.now().isoformat()
                
                # 업데이트된 정보 저장
                user_key = self._get_user_key(username)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=user_key,
                    Body=json.dumps(user_data),
                    ContentType='application/json'
                )
                
                return True, user_data
            else:
                return False, "비밀번호가 일치하지 않습니다."
                
        except Exception as e:
            logger.error(f"사용자 인증 중 오류 발생: {str(e)}")
            return False, f"인증 중 오류가 발생했습니다: {str(e)}"
    
    def get_user(self, username):
        """
        사용자 정보 조회
        
        Args:
            username: 사용자 ID
            
        Returns:
            사용자 정보 또는 None
        """
        try:
            user_key = self._get_user_key(username)
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=user_key)
            user_data = json.loads(response['Body'].read().decode('utf-8'))
            return user_data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            else:
                logger.error(f"사용자 정보 조회 중 오류: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"사용자 정보 조회 중 오류: {str(e)}")
            return None