from flask import Blueprint, render_template, request, jsonify, current_app, session, abort, redirect, url_for
from flask_login import login_required, current_user
import boto3
import json
from datetime import datetime
from app.services.service_advisor.advisor_factory import ServiceAdvisorFactory
from app.services.service_advisor.common.history_storage import AdvisorHistoryStorage
from functools import wraps

service_advisor_bp = Blueprint('service_advisor', __name__)

def service_advisor_access_required(f):
    """
    서비스 어드바이저 접근 권한을 확인하는 데코레이터
    사용자 인증 및 AWS 자격증명 확인
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 사용자 인증 확인
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        
        # AWS 자격증명 확인
        if 'auth_type' not in session or 'auth_params' not in session:
            current_app.logger.warning(f"사용자 {current_user.username}의 AWS 자격증명이 없습니다.")
            abort(403, description="AWS 자격증명이 필요합니다. 다시 로그인해주세요.")
        
        # 서비스 어드바이저 접근 권한 확인
        role_arn = current_user.get_role_arn()
        if not role_arn:
            current_app.logger.warning(f"사용자 {current_user.username}의 Role ARN이 없습니다.")
            abort(403, description="서비스 어드바이저 접근 권한이 없습니다.")
        
        return f(*args, **kwargs)
    return decorated_function

@service_advisor_bp.route('/service-advisor')
@service_advisor_access_required
def service_advisor_view():
    """서비스 어드바이저 메인 페이지를 렌더링합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 서비스 어드바이저에 접근했습니다.")
    return render_template('service_advisor/index.html')

@service_advisor_bp.route('/service-advisor/<service_name>')
@service_advisor_access_required
def service_advisor_detail(service_name):
    """특정 서비스에 대한 어드바이저 페이지를 렌더링합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 {service_name} 서비스 어드바이저에 접근했습니다.")
    
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return render_template('service_advisor/not_found.html', service_name=service_name)
    
    checks = advisor.get_available_checks()
    return render_template(f'service_advisor/{service_name}/{service_name}.html', checks=checks, service_name=service_name)

@service_advisor_bp.route('/api/service-advisor/<service_name>/run-check', methods=['POST'])
@service_advisor_access_required
def run_service_check(service_name):
    """특정 서비스의 검사를 실행합니다."""
    data = request.json
    check_id = data.get('check_id')
    
    current_app.logger.info(f"사용자 {current_user.username}이 {service_name} 서비스의 {check_id} 검사를 실행합니다.")
    
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return jsonify({'error': f'서비스 {service_name}에 대한 어드바이저를 찾을 수 없습니다.'}), 404
    
    try:
        # AWS 자격증명 정보 설정
        role_arn = current_user.get_role_arn()
        result = advisor.run_check(check_id, role_arn=role_arn)
        
        # 검사 실행 로그 기록
        current_app.logger.info(f"사용자 {current_user.username}의 {service_name} 서비스 {check_id} 검사 완료")
        
        # S3에 검사 결과 저장
        history_storage = AdvisorHistoryStorage()
        history_storage.save_check_result(
            username=current_user.username,
            service_name=service_name,
            check_id=check_id,
            result=result
        )
        
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"사용자 {current_user.username}의 검사 실행 중 오류 발생: {str(e)}")
        return jsonify({'error': f'검사 실행 중 오류가 발생했습니다: {str(e)}'}), 500

@service_advisor_bp.route('/api/service-advisor/<service_name>/scan', methods=['POST'])
@service_advisor_access_required
def ec2_scan(service_name):
    """서비스 전체 스캔을 실행합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 {service_name} 서비스 전체 스캔을 실행합니다.")
    
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return jsonify({'error': f'서비스 {service_name}에 대한 어드바이저를 찾을 수 없습니다.'}), 404
    
    try:
        # AWS 자격증명 정보 설정
        role_arn = current_user.get_role_arn()
        
        # 모든 검사 실행
        checks = advisor.get_available_checks()
        results = {}
        
        for check in checks:
            check_id = check.get('id')
            result = advisor.run_check(check_id, role_arn=role_arn)
            results[check_id] = result
            
            # 검사 결과 저장
            history_storage = AdvisorHistoryStorage()
            history_storage.save_check_result(
                username=current_user.username,
                service_name=service_name,
                check_id=check_id,
                result=result
            )
        
        current_app.logger.info(f"사용자 {current_user.username}의 {service_name} 서비스 전체 스캔 완료")
        
        return jsonify({
            'success': True,
            'message': f'{service_name} 서비스 스캔이 완료되었습니다.',
            'redirect_url': url_for('service_advisor.service_advisor_detail', service_name=service_name)
        })
    except Exception as e:
        current_app.logger.error(f"사용자 {current_user.username}의 {service_name} 스캔 중 오류 발생: {str(e)}")
        return jsonify({'error': f'스캔 중 오류가 발생했습니다: {str(e)}'}), 500

@service_advisor_bp.route('/api/service-advisor/services')
@service_advisor_access_required
def get_available_services():
    """사용 가능한 서비스 목록을 반환합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 서비스 목록을 요청했습니다.")
    advisor_factory = ServiceAdvisorFactory()
    services = advisor_factory.get_available_services()
    return jsonify(services)

@service_advisor_bp.route('/service-advisor/history')
@service_advisor_access_required
def service_advisor_history():
    """서비스 어드바이저 검사 기록을 표시합니다."""
    service_name = request.args.get('service_name')
    limit = int(request.args.get('limit', 100))  # 기본값을 100으로 증가
    
    current_app.logger.info(f"사용자 {current_user.username}이 서비스 어드바이저 기록을 조회합니다.")
    
    # 기록 조회
    history_storage = AdvisorHistoryStorage()
    history_list = history_storage.get_check_history(
        username=current_user.username,
        service_name=service_name,
        limit=limit
    )
    
    return render_template(
        'service_advisor/common/history.html',
        history_list=history_list,
        service_name=service_name
    )

@service_advisor_bp.route('/service-advisor/history/<path:key>')
@service_advisor_access_required
def service_advisor_history_detail(key):
    """서비스 어드바이저 검사 기록 상세 정보를 표시합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 검사 기록 상세 정보를 조회합니다: {key}")
    
    # 기록 상세 조회
    history_storage = AdvisorHistoryStorage()
    result = history_storage.get_check_result(key)
    
    if not result:
        current_app.logger.warning(f"검사 기록을 찾을 수 없음: {key}")
        return render_template('service_advisor/common/not_found.html', message="요청한 검사 기록을 찾을 수 없습니다.")
    
    # 메타데이터 추출
    metadata = result.get('metadata', {})
    service_name = metadata.get('service_name')
    check_id = metadata.get('check_id')
    timestamp = metadata.get('timestamp')
    
    # 결과 데이터 추출
    check_result = result.get('result', {})
    
    return render_template(
        'service_advisor/common/history_detail.html',
        service_name=service_name,
        check_id=check_id,
        timestamp=timestamp,
        result=check_result,
        key=key
    )

@service_advisor_bp.route('/api/service-advisor/history/delete/<path:key>', methods=['DELETE'])
@service_advisor_access_required
def delete_history(key):
    """서비스 어드바이저 검사 기록을 삭제합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 검사 기록을 삭제합니다: {key}")
    
    # 기록 삭제
    history_storage = AdvisorHistoryStorage()
    success = history_storage.delete_check_result(key)
    
    if success:
        return jsonify({'success': True, 'message': '검사 기록이 삭제되었습니다.'})
    else:
        return jsonify({'success': False, 'message': '검사 기록 삭제 중 오류가 발생했습니다.'}), 500

@service_advisor_bp.route('/api/service-advisor/history/<service_name>/<check_id>', methods=['GET'])
@service_advisor_access_required
def get_check_history(service_name, check_id):
    """특정 서비스와 검사 ID에 대한 최신 검사 기록을 반환합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 {service_name} 서비스의 {check_id} 검사 기록을 요청했습니다.")
    
    # 최신 검사 결과 조회
    history_storage = AdvisorHistoryStorage()
    result = history_storage.get_latest_check_result(
        username=current_user.username,
        service_name=service_name,
        check_id=check_id
    )
    
    if result and 'result' in result and 'metadata' in result:
        current_app.logger.info(f"검사 기록 찾음: {check_id}, 타임스탬프: {result['metadata'].get('timestamp')}")
        return jsonify({
            'success': True,
            'timestamp': result['metadata'].get('timestamp'),
            'result': result.get('result')
        })
    
    current_app.logger.warning(f"검사 기록을 찾을 수 없음: {service_name}/{check_id}")
    return jsonify({
        'success': False,
        'message': '검사 기록을 찾을 수 없습니다.'
    })