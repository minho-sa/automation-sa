from flask import render_template, redirect, url_for, flash, session, jsonify, request
from flask_login import login_required, current_user
from app import app
from app.services.aws_services import collect_service_data, get_available_services, get_service_data, list_collections
from app.services.s3_storage import S3Storage
from datetime import datetime
import json
import logging
import uuid

# 로깅 설정
logger = logging.getLogger('resource')
logger.setLevel(logging.INFO)

# 수집 상태를 세션별로 추적하기 위한 딕셔너리
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

@app.route('/resource/collections')
@login_required
def resource_collections_view():
    """수집 데이터 관리 페이지"""
    user_id = current_user.get_id()
    
    # 사용자의 수집 데이터 목록 가져오기
    user_collections = get_user_collections(user_id)
    
    # 사용 가능한 서비스 목록 가져오기
    services = get_available_services()
    
    # 서비스 아이콘 매핑
    service_icons = {
        'ec2': 'fa-server',
        's3': 'fa-database',
        'rds': 'fa-database',
        'lambda': 'fa-code',
        'cloudwatch': 'fa-chart-line',
        'iam': 'fa-users',
        'dynamodb': 'fa-table',
        'ecs': 'fa-docker',
        'eks': 'fa-cubes',
        'sns': 'fa-bell',
        'sqs': 'fa-envelope',
        'apigateway': 'fa-network-wired',
        'elasticache': 'fa-memory',
        'route53': 'fa-globe'
    }
    
    # 서비스 정보 구성
    services_with_icons = {}
    for service_key, service_name in services.items():
        services_with_icons[service_key] = {
            'name': service_name,
            'icon': service_icons.get(service_key, 'fa-cloud')
        }
    
    return render_template('resource/collections.html',
                          services=services_with_icons,
                          user_collections=user_collections)

@app.route('/resource/service/<collection_id>')
@login_required
def resource_service_view(collection_id):
    """특정 수집 데이터의 서비스 정보 보기"""
    user_id = current_user.get_id()
    
    try:
        # S3에서 해당 수집 데이터 로드
        s3_storage = S3Storage()
        collection_data = s3_storage.get_collection_data(user_id, collection_id)
        
        if collection_data and 'metadata' in collection_data and 'services_data' in collection_data:
            # 서비스 데이터 표시
            return render_template('resource/service_view.html',
                                  services=get_available_services(),
                                  all_services_data=collection_data['services_data'],
                                  selected_services=collection_data['metadata'].get('selected_services', []),
                                  collection_id=collection_id,
                                  collection_timestamp=collection_data['metadata'].get('timestamp'))
        else:
            flash('요청한 수집 데이터를 찾을 수 없습니다.')
            return redirect(url_for('resource_collections_view'))
    except Exception as e:
        logger.error(f"서비스 정보 로드 중 오류 발생: {str(e)}")
        flash(f'서비스 정보 로드 중 오류가 발생했습니다: {str(e)}')
        return redirect(url_for('resource_collections_view'))

@app.route('/resource/start_collection', methods=['POST'])
@login_required
def resource_start_collection():
    try:
        # AWS 자격 증명 가져오기
        auth_type = session.get('auth_type')
        auth_params = session.get('auth_params', {})
        
        region = app.config.get('AWS_DEFAULT_REGION', 'ap-northeast-2')
        user_id = current_user.get_id()
        session_id = get_session_id()
        
        # 세션의 수집 상태 가져오기 또는 생성
        if session_id not in collection_statuses:
            collection_statuses[session_id] = get_default_status()
        
        status = collection_statuses[session_id]
        
        # 이미 수집 중인 경우 중복 요청 방지
        if status['is_collecting']:
            logger.warning(f"이미 데이터 수집이 진행 중입니다. 사용자: {user_id}")
            return jsonify({'status': 'error', 'message': '이미 데이터 수집이 진행 중입니다. 완료될 때까지 기다려주세요.'}), 409
        
        # 항상 새로운 수집을 시작할 수 있도록 상태 완전히 초기화
        status['is_collecting'] = False
        status['last_collection_time'] = datetime.now().timestamp()
        status['all_services_data'] = {}
        status['completed_services'] = []
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
        status['selected_services'] = selected_services
        status['total_services'] = len(selected_services)
        status['collection_id'] = str(uuid.uuid4())[:8]
        
        # 데이터 수집 시작 (백그라운드 스레드에서)
        import threading
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
        logger.error(f"요청 처리 중 오류 발생: {str(e)}")
        return jsonify({'status': 'error', 'message': f'요청 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/resource/collection_status')
@login_required
def resource_collection_status():
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
    
    # 진행률 계산
    progress = 0
    if status['total_services'] > 0:
        unique_completed = len(set(status['completed_services']))
        progress = min(int(unique_completed / status['total_services'] * 100), 100)
    
    # 선택된 서비스 목록도 함께 반환
    return jsonify({
        'is_collecting': status['is_collecting'],
        'current_service': status['current_service'],
        'completed_services': status['completed_services'],
        'total_services': status['total_services'],
        'error': status['error'],
        'progress': progress,
        'selected_services': status.get('selected_services', [])
    })

@app.route('/resource/collections/<collection_id>', methods=['DELETE'])
@login_required
def resource_delete_collection(collection_id):
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
        logger.error(f"수집 데이터 삭제 중 오류 발생: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'수집 데이터 삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500

def get_session_id():
    """현재 세션의 고유 ID를 생성하거나 가져옵니다."""
    if 'resource_session_id' not in session:
        session['resource_session_id'] = str(uuid.uuid4())
    return session['resource_session_id']

def collect_data(region, user_id, session_id, selected_services=None, auth_type='access_key', auth_params=None):
    """데이터 수집 함수"""
    # 세션의 수집 상태 가져오기
    if session_id not in collection_statuses:
        collection_statuses[session_id] = get_default_status()
    
    status = collection_statuses[session_id]
    
    # 선택된 서비스가 없으면 오류 로그 기록
    if not selected_services:
        logger.error("선택된 서비스가 없습니다. 데이터 수집을 중단합니다.")
        status['is_collecting'] = False
        status['error'] = "선택된 서비스가 없습니다."
        return
    
    logger.info(f"데이터 수집 시작: 사용자={user_id}, 서비스={selected_services}")
    
    try:
        # 선택된 서비스만 수집
        for service_key in selected_services:
            # 현재 수집 중인 서비스 업데이트
            status['current_service'] = service_key
            
            logger.info(f"서비스 데이터 수집 시작: {service_key}")
            
            # 데이터 수집
            result = collect_service_data(
                username=user_id,
                service_name=service_key,
                region=region,
                auth_type=auth_type,
                **auth_params
            )
            
            # 결과 처리
            if result and result.get('success'):
                status['all_services_data'][service_key] = result.get('result', {})
                status['completed_services'].append(service_key)
                logger.info(f"서비스 데이터 수집 완료: {service_key}")
            else:
                logger.warning(f"서비스 데이터 수집 실패: {service_key} - {result.get('error', '알 수 없는 오류')}")
        
        # 수집 완료
        status['current_service'] = None
        status['is_collecting'] = False
        logger.info(f"모든 서비스 데이터 수집 완료: {len(status['completed_services'])}개 서비스")
        
        # S3에 수집 데이터 저장
        try:
            # 수집된 데이터 확인
            data_to_save = status['all_services_data']
            
            # 데이터가 비어있는지 확인
            if not data_to_save:
                logger.warning(f"저장할 데이터가 없습니다!")
                return
            
            # 데이터가 비어있으면 빈 객체라도 저장
            for service_key in selected_services:
                if service_key not in data_to_save:
                    logger.warning(f"서비스 {service_key}의 데이터가 없어 빈 객체로 저장합니다.")
                    data_to_save[service_key] = {"status": "collected", "data": {}}
            
            # S3에 저장
            s3_storage = S3Storage()
            collection_id = status['collection_id']
            save_result = s3_storage.save_collection_data(
                user_id=user_id,
                collection_id=collection_id,
                data=data_to_save,
                selected_services=selected_services
            )
            
            if save_result:
                logger.info(f"수집 데이터를 S3에 성공적으로 저장했습니다.")
                
                # 수집 직후 데이터를 명시적으로 캐시에 저장
                try:
                    # 메타데이터 캐시에 저장
                    metadata = {
                        'user_id': user_id,
                        'collection_id': collection_id,
                        'timestamp': datetime.now().isoformat(),
                        'selected_services': selected_services
                    }
                    s3_storage._set_in_cache('metadata', user_id, metadata, collection_id)
                    
                    # 서비스 데이터 캐시에 저장
                    s3_storage._set_in_cache('data', user_id, data_to_save, collection_id, 'all')
                    
                    # 컬렉션 목록 캐시 무효화 (새로운 컬렉션이 추가되었으므로)
                    s3_storage._invalidate_cache('collections', user_id)
                    
                    logger.info(f"수집 데이터를 캐시에 직접 저장 완료")
                except Exception as cache_err:
                    logger.warning(f"캐시 저장 중 오류 (무시): {str(cache_err)}")
            else:
                logger.error(f"S3에 데이터 저장 실패")
        except Exception as e:
            logger.error(f"S3에 데이터 저장 중 오류 발생: {str(e)}")
        
    except Exception as e:
        error_msg = str(e)
        status['error'] = error_msg
        status['is_collecting'] = False
        logger.error(f"데이터 수집 중 오류 발생: {error_msg}")

def get_user_collections(user_id):
    """사용자의 수집 데이터 목록을 안전하게 가져옵니다."""
    try:
        s3_storage = S3Storage()
        return s3_storage.list_user_collections(user_id)
    except Exception as e:
        logger.error(f"사용자 수집 목록 조회 중 오류 발생: {str(e)}")
        return []