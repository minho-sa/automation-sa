from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from app import app
from app.models.user import users
from app.services.aws_utils import get_aws_credentials

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('consolidated_view'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        auth_method = request.form.get('auth_method', 'access_key')
        
        # 사용자 인증
        user = next((u for u in users.values() if u.username == username), None)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            
            try:
                # 선택한 인증 방식에 따라 AWS 자격 증명 처리
                if auth_method == 'access_key':
                    aws_access_key = request.form.get('aws_access_key')
                    aws_secret_key = request.form.get('aws_secret_key')
                    
                    if not aws_access_key or not aws_secret_key:
                        flash('AWS 액세스 키와 시크릿 키를 모두 입력해주세요.')
                        return render_template('login.html')
                    
                    # 세션에 자격 증명 저장
                    session['aws_access_key'] = aws_access_key
                    session['aws_secret_key'] = aws_secret_key
                    session['auth_method'] = 'access_key'
                    
                elif auth_method == 'role_arn':
                    role_arn = request.form.get('role_arn')
                    
                    if not role_arn:
                        flash('역할 ARN을 입력해주세요.')
                        return render_template('login.html')
                    
                    # STS를 통해 자격 증명 획득 및 세션에 저장
                    credentials = get_aws_credentials(role_arn=role_arn)
                    session['aws_access_key'] = credentials['aws_access_key_id']
                    session['aws_secret_key'] = credentials['aws_secret_access_key']
                    session['aws_session_token'] = credentials.get('aws_session_token')
                    session['auth_method'] = 'role_arn'
                    session['role_arn'] = role_arn
                
                return redirect(url_for('consolidated_view'))
                
            except Exception as e:
                flash(f'AWS 자격 증명 처리 중 오류가 발생했습니다: {str(e)}')
                return render_template('login.html')
        else:
            flash('사용자 이름 또는 비밀번호가 올바르지 않습니다.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    # AWS 자격 증명 제거
    session.pop('aws_access_key', None)
    session.pop('aws_secret_key', None)
    session.pop('aws_session_token', None)
    session.pop('auth_method', None)
    session.pop('role_arn', None)
    flash('로그아웃되었습니다.')
    return redirect(url_for('login'))