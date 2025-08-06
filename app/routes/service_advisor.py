from flask import Blueprint, render_template, request, jsonify, current_app, session, abort, redirect, url_for, send_file
from flask_login import login_required, current_user
import boto3
import json
import io
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
        
        # 개발 환경에서는 자격증명 검사를 건너뜁니다
        if current_app.config.get('ENV') == 'development':
            return f(*args, **kwargs)
        
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

@service_advisor_bp.route('')
@service_advisor_access_required
def service_advisor_view():
    """서비스 어드바이저 메인 페이지를 렌더링합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 서비스 어드바이저에 접근했습니다.")
    return render_template('service_advisor/index.html')

@service_advisor_bp.route('/<service_name>')
@service_advisor_access_required
def service_advisor_detail(service_name):
    """특정 서비스에 대한 어드바이저 페이지를 렌더링합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 {service_name} 서비스 어드바이저에 접근했습니다.")
    
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return render_template('service_advisor/common/not_found.html', service_name=service_name, base_url='/advisor')
    
    checks = advisor.get_available_checks()
    try:
        # 서비스별 템플릿이 있는지 확인
        template_path = f'service_advisor/{service_name}/{service_name}.html'
        return render_template(template_path, checks=checks, service_name=service_name, base_url='/advisor')
    except Exception as e:
        # 템플릿이 없으면 공통 템플릿 사용
        current_app.logger.warning(f"서비스 템플릿을 찾을 수 없음: {service_name}, 공통 템플릿 사용")
        return render_template('service_advisor/service_template.html', checks=checks, service_name=service_name, base_url='/advisor')

@service_advisor_bp.route('/<service_name>/checks')
@service_advisor_access_required
def get_service_checks(service_name):
    """특정 서비스의 검사 항목 목록을 반환합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 {service_name} 서비스의 검사 항목을 요청했습니다.")
    
    advisor_factory = ServiceAdvisorFactory()
    advisor = advisor_factory.get_advisor(service_name)
    
    if not advisor:
        return jsonify({'error': f'서비스 {service_name}에 대한 어드바이저를 찾을 수 없습니다.'}), 404
    
    checks = advisor.get_available_checks()
    return jsonify({'checks': checks})

@service_advisor_bp.route('/<service_name>/run-check', methods=['POST'])
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
        
        # S3에 검사 결과 저장 (한글 인코딩 문제 해결)
        history_storage = AdvisorHistoryStorage()
        history_storage.save_check_result(
            username=current_user.username,
            service_name=service_name,
            check_id=check_id,
            result=result
        )
        
        # 현재 시간 추가
        result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"사용자 {current_user.username}의 검사 실행 중 오류 발생: {str(e)}")
        return jsonify({'error': f'검사 실행 중 오류가 발생했습니다: {str(e)}'}), 500

@service_advisor_bp.route('/<service_name>/scan', methods=['POST'])
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
            'redirect_url': f'/advisor/{service_name}'
        })
    except Exception as e:
        current_app.logger.error(f"사용자 {current_user.username}의 {service_name} 스캔 중 오류 발생: {str(e)}")
        return jsonify({'error': f'스캔 중 오류가 발생했습니다: {str(e)}'}), 500

@service_advisor_bp.route('/services')
@service_advisor_access_required
def get_available_services():
    """사용 가능한 서비스 목록을 반환합니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 서비스 목록을 요청했습니다.")
    advisor_factory = ServiceAdvisorFactory()
    services = advisor_factory.get_available_services()
    return jsonify(services)

@service_advisor_bp.route('/history')
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
        service_name=service_name,
        base_url='/advisor'
    )

@service_advisor_bp.route('/history/<path:key>')
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
        key=key,
        base_url='/advisor'
    )

@service_advisor_bp.route('/history/delete/<path:key>', methods=['DELETE'])
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

@service_advisor_bp.route('/history/<service_name>/<check_id>', methods=['GET'])
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

@service_advisor_bp.route('/export-pdf/<service_name>/<check_id>', methods=['GET'])
@service_advisor_access_required
def export_pdf(service_name, check_id):
    """특정 서비스와 검사 ID에 대한 검사 결과를 PDF로 내보냅니다."""
    current_app.logger.info(f"사용자 {current_user.username}이 {service_name} 서비스의 {check_id} 검사 결과를 PDF로 내보냅니다.")
    
    # 최신 검사 결과 조회
    history_storage = AdvisorHistoryStorage()
    result = history_storage.get_latest_check_result(
        username=current_user.username,
        service_name=service_name,
        check_id=check_id
    )
    
    if not result or 'result' not in result or 'metadata' not in result:
        current_app.logger.warning(f"PDF 내보내기 실패: 검사 기록을 찾을 수 없음: {service_name}/{check_id}")
        return jsonify({
            'success': False,
            'message': '검사 기록을 찾을 수 없습니다.'
        }), 404
    
    try:
        # 한글 지원 PDF 생성 유틸리티 사용
        from app.utils.pdf_generator import generate_check_result_pdf
        
        # 검사 결과 데이터
        check_result = result.get('result', {})
        metadata = result.get('metadata', {})
        timestamp = metadata.get('timestamp', datetime.now().isoformat())
        
        # 검사 정보 가져오기
        advisor_factory = ServiceAdvisorFactory()
        advisor = advisor_factory.get_advisor(service_name)
        checks = advisor.get_available_checks()
        check_info = next((check for check in checks if check.get('id') == check_id), {})
        
        # PDF 생성 유틸리티 사용
        pdf_data = generate_check_result_pdf(
            check_result=check_result,
            service_name=service_name,
            check_id=check_id,
            check_info=check_info,
            username=current_user.username,
            timestamp=timestamp
        )
        
        if not pdf_data:
            return jsonify({
                'success': False,
                'message': 'PDF 생성에 실패했습니다.'
            }), 500
        
        # 바이트 데이터를 BytesIO 객체로 변환
        buffer = io.BytesIO(pdf_data)
        buffer.seek(0)
        
        filename = f"aws-advisor-{service_name}-{check_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        current_app.logger.error(f"PDF 내보내기 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'PDF 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500

@service_advisor_bp.route('/export-multiple-pdf', methods=['POST'])
@service_advisor_access_required
def export_multiple_pdf():
    """여러 검사 항목을 하나의 PDF로 내보냅니다."""
    data = request.json
    check_items = data.get('check_items', [])
    
    if not check_items or len(check_items) == 0:
        return jsonify({
            'success': False,
            'message': '선택된 검사 항목이 없습니다.'
        }), 400
    
    current_app.logger.info(f"사용자 {current_user.username}이 {len(check_items)}개의 검사 항목을 PDF로 내보냅니다.")
    
    try:
        # 한글 지원 PDF 생성 유틸리티 사용
        from app.utils.pdf_generator import generate_multiple_check_results_pdf
        
        history_storage = AdvisorHistoryStorage()
        advisor_factory = ServiceAdvisorFactory()
        
        check_results = []
        
        for item in check_items:
            service_name = item.get('service_name')
            check_id = item.get('check_id')
            
            # 최신 검사 결과 조회
            result = history_storage.get_latest_check_result(
                username=current_user.username,
                service_name=service_name,
                check_id=check_id
            )
            
            if result and 'result' in result and 'metadata' in result:
                # 검사 정보 가져오기
                advisor = advisor_factory.get_advisor(service_name)
                checks = advisor.get_available_checks()
                check_info = next((check for check in checks if check.get('id') == check_id), {})
                
                check_results.append({
                    'result': result.get('result', {}),
                    'service_name': service_name,
                    'check_id': check_id,
                    'check_info': check_info,
                    'timestamp': result.get('metadata', {}).get('timestamp', datetime.now().isoformat())
                })
        
        if not check_results:
            return jsonify({
                'success': False,
                'message': '검사 결과를 찾을 수 없습니다.'
            }), 404
        
        # 여러 PDF 생성 및 병합
        pdf_data = generate_multiple_check_results_pdf(
            check_results=check_results,
            username=current_user.username
        )
        
        if not pdf_data:
            return jsonify({
                'success': False,
                'message': 'PDF 생성에 실패했습니다.'
            }), 500
        
        # 바이트 데이터를 BytesIO 객체로 변환
        buffer = io.BytesIO(pdf_data)
        buffer.seek(0)
        
        filename = f"aws-advisor-multiple-checks-{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        current_app.logger.error(f"여러 PDF 내보내기 중 오류 발생: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'PDF 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500

@service_advisor_bp.route('/check-results-status', methods=['POST'])
@service_advisor_access_required
def check_results_status():
    """선택한 검사 항목들의 결과 상태를 확인합니다."""
    data = request.json
    check_items = data.get('check_items', [])
    
    if not check_items or len(check_items) == 0:
        return jsonify({
            'success': False,
            'message': '선택된 검사 항목이 없습니다.'
        }), 400
    
    current_app.logger.info(f"사용자 {current_user.username}이 {len(check_items)}개의 검사 항목 상태를 확인합니다.")
    
    history_storage = AdvisorHistoryStorage()
    results_status = []
    
    for item in check_items:
        service_name = item.get('service_name')
        check_id = item.get('check_id')
        
        # 최신 검사 결과 조회
        result = history_storage.get_latest_check_result(
            username=current_user.username,
            service_name=service_name,
            check_id=check_id
        )
        
        if result and 'result' in result and 'metadata' in result:
            results_status.append({
                'service_name': service_name,
                'check_id': check_id,
                'has_result': True,
                'timestamp': result.get('metadata', {}).get('timestamp')
            })
        else:
            results_status.append({
                'service_name': service_name,
                'check_id': check_id,
                'has_result': False
            })
    
    return jsonify({
        'success': True,
        'results_status': results_status
    })

# PDF 생성 유틸리티로 이동