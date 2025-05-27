from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import boto3
import json
from app.services.service_advisor.advisor_factory import ServiceAdvisorFactory

service_advisor_bp = Blueprint('service_advisor', __name__)

@service_advisor_bp.route('/service-advisor')
@login_required
def service_advisor_view():
    """서비스 어드바이저 메인 페이지를 렌더링합니다."""
    return render_template('service_advisor/index.html')

@service_advisor_bp.route('/service-advisor/<service_name>')
@login_required
def service_advisor_detail(service_name):
    """특정 서비스에 대한 어드바이저 페이지를 렌더링합니다."""
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return render_template('service_advisor/not_found.html', service_name=service_name)
    
    checks = advisor.get_available_checks()
    return render_template(f'service_advisor/{service_name}.html', checks=checks, service_name=service_name)

@service_advisor_bp.route('/api/service-advisor/<service_name>/run-check', methods=['POST'])
@login_required
def run_service_check(service_name):
    """특정 서비스의 검사를 실행합니다."""
    data = request.json
    check_id = data.get('check_id')
    
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return jsonify({'error': f'서비스 {service_name}에 대한 어드바이저를 찾을 수 없습니다.'}), 404
    
    try:
        result = advisor.run_check(check_id)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"검사 실행 중 오류 발생: {str(e)}")
        return jsonify({'error': f'검사 실행 중 오류가 발생했습니다: {str(e)}'}), 500

@service_advisor_bp.route('/api/service-advisor/services')
@login_required
def get_available_services():
    """사용 가능한 서비스 목록을 반환합니다."""
    advisor_factory = ServiceAdvisorFactory()
    services = advisor_factory.get_available_services()
    return jsonify(services)