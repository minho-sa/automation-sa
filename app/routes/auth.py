from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
import logging

logger = logging.getLogger(__name__)
from app import app, login_manager
from app.services.user_storage import UserStorage
from app.models.user import User
import logging
import re

logger = logging.getLogger(__name__)

# 사용자 로더 설정
@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login을 위한 사용자 로더
    
    Args:
        user_id: 사용자 ID
        
    Returns:
        User 객체 또는 None
    """
    try:
        user_storage = UserStorage()
        user_data = user_storage.get_user(user_id)
        
        if user_data:
            return User(user_data)
        return None
    except Exception as e:
        logger.error(f"사용자 로드 중 오류 발생: {str(e)}")
        return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    """회원가입 페이지 및 처리"""
    # 이미 로그인한 경우 대시보드로 리디렉션
    if current_user.is_authenticated:
        return redirect(url_for('consolidated_view'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role_arn = request.form.get('role_arn')
        
        # 입력값 검증
        if not username or not password or not confirm_password or not role_arn:
            flash('모든 필드를 입력해주세요.')
            return render_template('register.html')
        
        # 사용자 ID 형식 검증 (영문, 숫자, 언더스코어만 허용)
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('사용자 ID는 영문, 숫자, 언더스코어(_)만 사용할 수 있습니다.')
            return render_template('register.html')
        
        # 비밀번호 길이 검증
        if len(password) < 8:
            flash('비밀번호는 최소 8자 이상이어야 합니다.')
            return render_template('register.html')
        
        # 비밀번호 복잡성 검증
        if not (re.search(r'[A-Z]', password) and re.search(r'[a-z]', password) and 
                re.search(r'[0-9]', password) and re.search(r'[^A-Za-z0-9]', password)):
            flash('비밀번호는 대문자, 소문자, 숫자, 특수문자를 모두 포함해야 합니다.')
            return render_template('register.html')
        
        # 비밀번호 확인 일치 검증
        if password != confirm_password:
            flash('비밀번호와 비밀번호 확인이 일치하지 않습니다.')
            return render_template('register.html')
        
        # Role ARN 형식 검증
        if not re.match(r'^arn:aws:iam::\d{12}:role/[a-zA-Z0-9+=,.@_-]+$', role_arn):
            flash('올바른 AWS Role ARN 형식이 아닙니다.')
            return render_template('register.html')
        
        # 사용자 등록
        user_storage = UserStorage()
        success, message = user_storage.register_user(username, password, role_arn)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지 및 처리"""
    # 이미 로그인한 경우 대시보드로 리디렉션
    if current_user.is_authenticated:
        return redirect(url_for('consolidated_view'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        # 입력값 검증
        if not username or not password:
            flash('사용자 ID와 비밀번호를 모두 입력해주세요.')
            return render_template('login.html')
        
        # 사용자 인증
        user_storage = UserStorage()
        success, result = user_storage.authenticate_user(username, password)
        
        if success:
            # 사용자 객체 생성 및 로그인
            user = User(result)
            login_user(user, remember=remember)
            
            # AWS 자격증명 정보 세션에 저장
            session['auth_type'] = 'role_arn'
            session['auth_params'] = {'role_arn': user.get_role_arn()}
            
            # 원래 요청한 페이지로 리디렉션 (없으면 대시보드로)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('consolidated_view')
                
            return redirect(next_page)
        else:
            flash(result)
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """로그아웃 처리"""
    logout_user()
    session.pop('auth_type', None)
    session.pop('auth_params', None)
    flash('로그아웃되었습니다.')
    return redirect(url_for('login'))