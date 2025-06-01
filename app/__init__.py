import os
import logging
from flask import Flask
from flask_login import LoginManager
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/app.log")
    ]
)

# 애플리케이션 생성
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

# 설정 로드
app.config.from_object('config.Config')

# 로그인 매니저 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 사용자 로더 함수
@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return User.get(user_id)

# 시작 로그
logger = logging.getLogger(__name__)
logger.info("애플리케이션 시작")

# 라우트 임포트
from app.routes import auth, dashboard, resource
from app.routes.service_advisor import service_advisor_bp

# 블루프린트 등록
app.register_blueprint(service_advisor_bp, url_prefix='/service_advisor')