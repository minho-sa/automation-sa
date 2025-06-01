import os
from dotenv import load_dotenv
import re

# .env 파일 로드
load_dotenv()

# Flask 애플리케이션 설정
SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'

# 서버의 AWS 자격 증명을 .env 파일에서 가져옴
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')

# AWS 리전 형식 검증
AWS_REGION = os.environ.get('AWS_REGION') or "ap-northeast-2"

# S3 버킷 이름
DATA_BUCKET_NAME = os.environ.get('DATA_BUCKET_NAME') or 'saltware-console-data'

# Config 클래스 정의
class Config:
    SECRET_KEY = SECRET_KEY
    AWS_ACCESS_KEY = AWS_ACCESS_KEY
    AWS_SECRET_KEY = AWS_SECRET_KEY
    AWS_REGION = AWS_REGION
    DATA_BUCKET_NAME = DATA_BUCKET_NAME
    
    # 세션 설정
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 86400  # 24시간
    SESSION_USE_SIGNER = True  # 세션 쿠키 서명
    SESSION_KEY_PREFIX = 'again_console:'  # 세션 키 접두사
    
    # 보안 설정
    REMEMBER_COOKIE_DURATION = 2592000  # 30일
    REMEMBER_COOKIE_SECURE = True  # HTTPS에서만 쿠키 전송
    REMEMBER_COOKIE_HTTPONLY = True  # JavaScript에서 쿠키 접근 방지
    REMEMBER_COOKIE_SAMESITE = 'Lax'  # CSRF 방지