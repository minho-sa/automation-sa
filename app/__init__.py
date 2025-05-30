from flask import Flask
from flask_login import LoginManager
import logging
from logging.handlers import RotatingFileHandler
import os
import config

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config.from_object('config')
app.secret_key = config.SECRET_KEY

# 로그 설정
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('애플리케이션 시작')

# 로그인 매니저 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from app.routes import main, auth, dashboard, service_advisor
from app.models import user

# 블루프린트 등록
app.register_blueprint(service_advisor.service_advisor_bp)

# user_loader는 user.py에 정의되어 있음