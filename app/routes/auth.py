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
                    session['auth_type'] = 'access_key'
                    session['auth_params'] = {
                        'aws_access_key': aws_access_key,
                        'aws_secret_key': aws_secret_key
                    }
                    
                elif auth_method == 'role_arn':
                    role_arn = request.form.get('role_arn')
                    server_access_key = app.config['AWS_ACCESS_KEY']
                    server_secret_key = app.config['AWS_SECRET_KEY']
                    
                    if not role_arn:
                        flash('역할 ARN을 입력해주세요.')
                        return render_template('login.html')
                    
                    # 세션에 역할 ARN과 서버 자격 증명 저장
                    session['auth_type'] = 'role_arn'
                    session['auth_params'] = {
                        'role_arn': role_arn,
                        'server_access_key': server_access_key,
                        'server_secret_key': server_secret_key
                    }
                
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
    session.pop('auth_type', None)
    session.pop('auth_params', None)
    flash('로그아웃되었습니다.')
    return redirect(url_for('login'))