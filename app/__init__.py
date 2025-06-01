from flask import Flask
from flask_login import LoginManager
import logging
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Flask 앱 생성
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# 설정 로드
app.config.from_object('config.Config')

# 비밀키 설정
app.secret_key = app.config.get('SECRET_KEY', 'default-secret-key')

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '이 페이지에 접근하려면 로그인이 필요합니다.'
login_manager.login_message_category = 'info'

# 로그 메시지
app.logger.info('애플리케이션 시작')

# 라우트 임포트 (순환 임포트 방지를 위해 여기서 임포트)
from app.routes import auth, dashboard