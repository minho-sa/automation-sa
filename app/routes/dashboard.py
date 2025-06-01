from flask import render_template, redirect, url_for, flash, session, jsonify, request
from flask_login import login_required, current_user, login_required
from app import app
from app.services.aws_services import aws_services
from datetime import datetime
import json
from app.services.resource.ec2 import get_ec2_data
from app.services.resource.s3 import get_s3_data
from app.services.resource.rds import get_rds_data
from app.services.resource.lambda_service import get_lambda_data
from app.services.resource.cloudwatch import get_cloudwatch_data
from app.services.resource.dynamodb import get_dynamodb_data
from app.services.resource.ecs import get_ecs_data
from app.services.resource.eks import get_eks_data
from app.services.resource.sns import get_sns_data
from app.services.resource.sqs import get_sqs_data
from app.services.resource.apigateway import get_apigateway_data
from app.services.resource.elasticache import get_elasticache_data
from app.services.resource.route53 import get_route53_data
from app.services.resource.iam import get_iam_data
from app.services.s3_storage import S3Storage
import threading
import time
import uuid

# 데이터 수집 상태를 세션별로 추적하기 위한 딕셔너리
collection_statuses = {}

# 기본 수집 상태 템플릿
def get_default_status():
    return {
        'is_collecting': False,
        'current_service': None,
        'completed_services': [],
        'total_services': 0,
        'error': None,
        'all_services_data': {},
        'collection_id': None,
        'selected_services': [],
        'last_collection_time': 0
    }

# 서비스 데이터 수집 함수 매핑
service_collectors = {
    'ec2': get_ec2_data,
    's3': get_s3_data,
    'rds': get_rds_data,
    'lambda': get_lambda_data,
    'cloudwatch': get_cloudwatch_data,
    'dynamodb': get_dynamodb_data,
    'ecs': get_ecs_data,
    'eks': get_eks_data,
    'sns': get_sns_data,
    'sqs': get_sqs_data,
    'apigateway': get_apigateway_data,
    'elasticache': get_elasticache_data,
    'route53': get_route53_data,
    'iam': get_iam_data
}

# 데이터 수집 함수
def collect_data(region, user_id, session_id, selected_services=None, auth_type='access_key', auth_params=None):
    # 세션의 수집 상태 가져오기 또는 생성
    if session_id not in collection_statuses:
        collection_statuses[session_id] = get_default_status()
    
    status = collection_statuses[session_id]
    
    # 선택된 서비스가 없으면 오류 로그 기록
    if not selected_services:
        app.logger.error("선택된 서비스가 없습니다. 데이터 수집을 중단합니다.")
        status['is_collecting'] = False
        return
        
    app.logger.info(f"collect_data 함수 내부 - 선택된 서비스: {selected_services}")
    
    # 항상 데이터 초기화 (이전 데이터 유지하지 않음)
    status['all_services_data'] = {}
    
    # 상태 초기화
    status['is_collecting'] = True
    status['current_service'] = None
    status['completed_services'] = []  # 완료된 서비스 목록 초기화
    status['error'] = None
    status['selected_services'] = selected_services.copy()  # 복사본 사용
    status['total_services'] = len(selected_services)
    status['collection_id'] = str(uuid.uuid4())[:8]  # 고유한 수집 ID 생성
    status['last_collection_time'] = time.time()
    
    # 로그에 수집 ID 기록
    collection_id = status['collection_id']
    app.logger.info(f"[{collection_id}] 데이터 수집 시작 - 사용자: {user_id}, 선택된 서비스: {selected_services}")
    
    try:
        # 선택된 서비스만 수집
        for service_key in selected_services:
            if service_key in service_collectors:
                service_name = aws_services[service_key]['name']
                status['current_service'] = service_name
                
                app.logger.info(f"[{collection_id}] {service_name} 데이터 수집 시작")
                
                # 해당 서비스의 데이터 수집 함수 호출 (키워드 인자 사용)
                service_data = service_collectors[service_key](
                    region=region, 
                    collection_id=status['collection_id'], 
                    auth_type=auth_type, 
                    **auth_params
                )
                
                # 데이터가 None이 아닌지 확인
                if service_data is not None:
                    status['all_services_data'][service_key] = service_data
                    app.logger.info(f"[{collection_id}] {service_name} 데이터 수집 성공: {type(service_data)}")
                else:
                    app.logger.warning(f"[{collection_id}] {service_name} 데이터 수집 결과가 None입니다.")
                
                # 완료된 서비스 추가 (서비스 키를 저장)
                status['completed_services'].append(service_key)
                app.logger.info(f"[{collection_id}] {service_name} 데이터 수집 완료")
        
        # 수집 완료
        status['current_service'] = None
        
        # S3에 수집 데이터 저장
        try:
            # 수집된 데이터 확인
            data_to_save = status['all_services_data']
            app.logger.info(f"[{collection_id}] 저장할 데이터 키: {list(data_to_save.keys())}")
            
            # 데이터가 비어있는지 확인
            if not data_to_save:
                app.logger.warning(f"[{collection_id}] 저장할 데이터가 없습니다!")
            
            # 각 서비스 데이터 확인
            for service_key, service_data in data_to_save.items():
                if service_data is None:
                    app.logger.warning(f"[{collection_id}] 서비스 {service_key}의 데이터가 None입니다.")
                elif not service_data:
                    app.logger.warning(f"[{collection_id}] 서비스 {service_key}의 데이터가 비어있습니다.")
            
            # 데이터가 비어있으면 빈 객체라도 저장
            for service_key in selected_services:
                if service_key not in data_to_save:
                    app.logger.warning(f"[{collection_id}] 서비스 {service_key}의 데이터가 없어 빈 객체로 저장합니다.")
                    data_to_save[service_key] = {"status": "collected", "data": {}}
            
            # S3에 저장
            s3_storage = S3Storage()
            save_result = s3_storage.save_collection_data(
                user_id=user_id,
                collection_id=collection_id,
                data=data_to_save,
                selected_services=selected_services
            )
            
            if save_result:
                app.logger.info(f"[{collection_id}] 수집 데이터를 S3에 성공적으로 저장했습니다.")
            else:
                app.logger.error(f"[{collection_id}] S3에 데이터 저장 실패")
        except Exception as e:
            app.logger.error(f"[{collection_id}] S3에 데이터 저장 중 오류 발생: {str(e)}")
        
    except Exception as e:
        error_msg = str(e)
        status['error'] = error_msg
        app.logger.error(f"[{status['collection_id']}] 데이터 수집 오류: {error_msg}")
    finally:
        # 데이터 수집 완료
        status['is_collecting'] = False
        app.logger.info(f"[{status['collection_id']}] 데이터 수집 완료 - 총 {len(status['completed_services'])}개 서비스")

@app.route('/consolidated')
@login_required
def consolidated_view():
    # AWS 자격 증명 가져오기
    auth_type = session.get('auth_type')
    auth_params = session.get('auth_params', {})
    
    if not auth_type or not auth_params:
        flash('AWS 자격 증명이 없습니다. 다시 로그인해주세요.')
        return redirect(url_for('login'))
    
    region = app.config.get('AWS_DEFAULT_REGION', 'ap-northeast-2')
    user_id = current_user.get_id()
    session_id = get_session_id()
    
    # 세션의 수집 상태 가져오기 또는 생성
    if session_id not in collection_statuses:
        collection_statuses[session_id] = get_default_status()
    
    status = collection_statuses[session_id]
    
    # 페이지 로드 시 is_collecting 상태 초기화 (서버 재시작 후 상태가 잘못 유지되는 경우 대비)
    current_time = time.time()
    last_collection_time = status.get('last_collection_time', 0)
    
    # 마지막 수집 시작 후 30초 이상 지났으면 초기화
    if current_time - last_collection_time > 30:
        status['is_collecting'] = False
    
    # 수집 중인 경우 진행 상태 표시
    if status['is_collecting']:
        # 모든 서비스에 대한 빈 데이터 구조 생성
        empty_services_data = {}
        for service_key in aws_services.keys():
            empty_services_data[service_key] = {'status': 'collecting'}
            
        # 이미 수집된 서비스 데이터는 유지
        for service_key, service_data in status['all_services_data'].items():
            empty_services_data[service_key] = service_data
            
        return render_template('consolidated.html', 
                              services=aws_services, 
                              all_services_data=empty_services_data, 
                              is_collecting=status['is_collecting'],
                              current_service=status['current_service'],
                              completed_services=status['completed_services'],
                              total_services=status['total_services'],
                              error=status['error'],
                              show_collection_message=False,
                              selected_services=status['selected_services'],
                              collection_id=status['collection_id'])
    
    # 요청된 수집 ID 확인
    requested_collection_id = request.args.get('collection_id')
    
    # 수집 ID가 지정된 경우 S3에서 해당 데이터 로드
    if requested_collection_id:
        try:
            app.logger.info(f"수집 ID {requested_collection_id}의 데이터 로드 시도")
            s3_storage = S3Storage()
            collection_data = s3_storage.get_collection_data(user_id, requested_collection_id)
            
            if collection_data and 'metadata' in collection_data:
                app.logger.info(f"수집 ID {requested_collection_id}의 메타데이터 로드 성공")
                
                # 서비스 데이터가 있는지 확인 (빈 객체라도 있으면 표시)
                if 'services_data' in collection_data:
                    app.logger.info(f"수집 ID {requested_collection_id}의 서비스 데이터 로드 성공: {list(collection_data['services_data'].keys())}")
                    
                    # 현재 메모리에 있는 데이터를 S3에서 로드한 데이터로 업데이트
                    status['all_services_data'] = collection_data['services_data']
                    status['selected_services'] = collection_data['metadata'].get('selected_services', [])
                    status['completed_services'] = list(collection_data['services_data'].keys())
                    status['collection_id'] = requested_collection_id
                    
                    # S3에서 로드한 데이터로 표시
                    return render_template('consolidated.html',
                                          services=aws_services,
                                          all_services_data=collection_data['services_data'],
                                          is_collecting=False,
                                          completed_services=list(collection_data['services_data'].keys()),
                                          total_services=len(collection_data['metadata'].get('selected_services', [])),
                                          error=None,
                                          show_collection_message=False,
                                          selected_services=collection_data['metadata'].get('selected_services', []),
                                          collection_id=requested_collection_id,
                                          collection_timestamp=collection_data['metadata'].get('timestamp'),
                                          user_collections=s3_storage.list_user_collections(user_id))
                else:
                    app.logger.warning(f"수집 ID {requested_collection_id}의 서비스 데이터가 비어있습니다")
                    flash(f'수집 ID {requested_collection_id}의 서비스 데이터가 비어있습니다. 다시 데이터를 수집해주세요.')
            else:
                app.logger.warning(f"요청한 수집 ID {requested_collection_id}의 데이터를 찾을 수 없습니다.")
                flash(f'요청한 수집 ID {requested_collection_id}의 데이터를 찾을 수 없습니다.')
        except Exception as e:
            app.logger.error(f"S3에서 데이터 로드 중 오류 발생: {str(e)}")
            flash(f'데이터 로드 중 오류가 발생했습니다: {str(e)}')
    
    # 데이터 수집이 완료되지 않은 경우 (completed_services가 비어있는 경우)
    if not status['completed_services']:
        # 사용자의 이전 수집 목록 가져오기
        user_collections = get_user_collections(user_id)
        
        if user_collections:
            # 이전 수집 데이터가 있으면 목록 표시
            return render_template('consolidated.html', 
                                  services=aws_services,
                                  all_services_data={},
                                  is_collecting=False,
                                  show_collection_message=True,
                                  user_collections=user_collections)
        else:
            # 이전 수집 데이터가 없으면 데이터 수집 버튼만 표시
            flash('서비스 정보를 보기 전에 먼저 데이터를 수집해야 합니다. 데이터 수집 버튼을 클릭하세요.')
            return render_template('consolidated.html', 
                                  services=aws_services,
                                  all_services_data={},
                                  is_collecting=False,
                                  show_collection_message=True)
                              
    # 현재 메모리에 있는 데이터 표시 (선택한 서비스만)
    filtered_services_data = {}
    for service_key in status.get('selected_services', []):
        if service_key in status['all_services_data']:
            filtered_services_data[service_key] = status['all_services_data'][service_key]
    
    # 사용자의 이전 수집 목록도 함께 가져오기
    user_collections = get_user_collections(user_id)
    
    # 현재 시간을 수집 시간으로 사용
    collection_timestamp = datetime.now().isoformat()
    
    return render_template('consolidated.html',
                          services=aws_services,
                          all_services_data=filtered_services_data,  # 선택한 서비스 데이터만 전달
                          is_collecting=False,
                          completed_services=status['completed_services'],
                          total_services=status['total_services'],
                          error=status['error'],
                          show_collection_message=False,
                          selected_services=status.get('selected_services', []),
                          collection_id=status.get('collection_id'),
                          collection_timestamp=collection_timestamp,  # 수집 시간 추가
                          user_collections=user_collections)

@app.route('/start_collection', methods=['POST'])
@login_required
def start_collection():
    try:
        # AWS 자격 증명 가져오기
        auth_type = session.get('auth_type')
        auth_params = session.get('auth_params', {})
        
        if not auth_type or not auth_params:
            return jsonify({'status': 'error', 'message': 'AWS 자격 증명이 없습니다. 다시 로그인해주세요.'}), 401
        
        region = app.config.get('AWS_DEFAULT_REGION', 'ap-northeast-2')
        user_id = current_user.get_id()
        session_id = get_session_id()
        
        # 세션의 수집 상태 가져오기 또는 생성
        if session_id not in collection_statuses:
            collection_statuses[session_id] = get_default_status()
        
        status = collection_statuses[session_id]
        
        # 이미 수집 중인 경우 중복 요청 방지
        if status['is_collecting']:
            app.logger.warning(f"이미 데이터 수집이 진행 중입니다. 사용자: {user_id}")
            return jsonify({'status': 'error', 'message': '이미 데이터 수집이 진행 중입니다. 완료될 때까지 기다려주세요.'}), 409
        
        # 항상 새로운 수집을 시작할 수 있도록 상태 완전히 초기화
        status['is_collecting'] = False
        status['last_collection_time'] = time.time()
        status['all_services_data'] = {}  # 이전 데이터 완전히 초기화
        status['completed_services'] = []  # 완료된 서비스 목록 초기화
        status['current_service'] = None
        
        # 요청 데이터 확인
        if not request.is_json:
            return jsonify({'status': 'error', 'message': '잘못된 요청 형식입니다.'}), 400
        
        request_data = request.get_json()
        selected_services = request_data.get('selected_services')
        
        # 선택된 서비스가 없는 경우
        if not selected_services:
            return jsonify({'status': 'error', 'message': '최소한 하나 이상의 서비스를 선택해야 합니다.'}), 400
        
        # 수집 상태를 먼저 설정하여 중복 요청 방지
        status['is_collecting'] = True
        
        # 데이터 수집 시작 (키워드 인자 사용)
        thread = threading.Thread(
            target=collect_data, 
            kwargs={
                'region': region, 
                'user_id': user_id,
                'session_id': session_id,
                'selected_services': selected_services, 
                'auth_type': auth_type, 
                'auth_params': auth_params
            }
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'success', 'message': '데이터 수집이 시작되었습니다.'}), 200
    except Exception as e:
        app.logger.error(f"요청 처리 중 오류 발생: {str(e)}")
        return jsonify({'status': 'error', 'message': f'요청 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/collection_status')
@login_required
def get_collection_status():
    session_id = get_session_id()
    
    # 세션의 수집 상태가 없으면 기본 상태 반환
    if session_id not in collection_statuses:
        return jsonify({
            'is_collecting': False,
            'current_service': None,
            'completed_services': [],
            'total_services': 0,
            'error': None,
            'progress': 0,
            'selected_services': []
        })
    
    # 세션의 수집 상태 가져오기
    status = collection_statuses[session_id]
    
    # 서비스 키를 서비스 이름으로 변환 (중복 제거)
    unique_service_keys = set(status['completed_services'])
    completed_service_names = []
    for service_key in unique_service_keys:
        if service_key in aws_services:
            completed_service_names.append(aws_services[service_key]['name'])
    
    # 진행률 계산 (중복 제거된 서비스 수 기준)
    progress = 0
    if status['total_services'] > 0:
        unique_completed = len(set(status['completed_services']))
        progress = min(int(unique_completed / status['total_services'] * 100), 100)
    
    # 선택된 서비스 목록도 함께 반환
    return jsonify({
        'is_collecting': status['is_collecting'],
        'current_service': status['current_service'],
        'completed_services': completed_service_names,  # 서비스 이름 목록 반환
        'total_services': status['total_services'],
        'error': status['error'],
        'progress': progress,
        'selected_services': status.get('selected_services', [])  # 선택된 서비스 목록 추가
    })

@app.route('/collections')
@login_required
def list_collections():
    """사용자의 모든 수집 데이터 목록 조회"""
    user_id = current_user.get_id()
    
    try:
        s3_storage = S3Storage()
        collections = s3_storage.list_user_collections(user_id)
        return jsonify({
            'status': 'success',
            'collections': collections
        })
    except Exception as e:
        app.logger.error(f"수집 목록 조회 중 오류 발생: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'수집 목록 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/collections/<collection_id>', methods=['DELETE'])
@login_required
def delete_collection(collection_id):
    """특정 수집 데이터 삭제"""
    user_id = current_user.get_id()
    
    try:
        s3_storage = S3Storage()
        success = s3_storage.delete_collection(user_id, collection_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'수집 ID {collection_id}의 데이터가 삭제되었습니다.'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'수집 ID {collection_id}의 데이터 삭제에 실패했습니다.'
            }), 500
    except Exception as e:
        app.logger.error(f"수집 데이터 삭제 중 오류 발생: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'수집 데이터 삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500

def get_session_id():
    """현재 세션의 고유 ID를 생성하거나 가져옵니다."""
    if 'dashboard_session_id' not in session:
        session['dashboard_session_id'] = str(uuid.uuid4())
    return session['dashboard_session_id']

@app.route('/reset_view')
@login_required
def reset_view():
    """현재 보고 있는 collection_id를 초기화하고 처음 화면으로 돌아갑니다."""
    session_id = get_session_id()
    
    # 세션의 수집 상태가 있으면 초기화
    if session_id in collection_statuses:
        # 수집 중이 아닌 경우에만 초기화
        if not collection_statuses[session_id]['is_collecting']:
            collection_statuses[session_id]['completed_services'] = []
            collection_statuses[session_id]['all_services_data'] = {}
            collection_statuses[session_id]['collection_id'] = None
    
    return redirect(url_for('consolidated_view'))

@app.route('/')
def index():
    """메인 페이지 - 로그인 페이지로 리디렉션"""
    if current_user.is_authenticated:
        return redirect(url_for('consolidated_view'))
    return redirect(url_for('login'))

def get_user_collections(user_id):
    """사용자의 수집 데이터 목록을 안전하게 가져옵니다."""
    try:
        s3_storage = S3Storage()
        return s3_storage.list_user_collections(user_id)
    except Exception as e:
        app.logger.error(f"사용자 수집 목록 조회 중 오류 발생: {str(e)}")
        return []