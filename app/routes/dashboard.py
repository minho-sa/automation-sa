from flask import render_template, redirect, url_for, flash, session, jsonify, request
from flask_login import login_required, current_user, login_required
from app import app
from app.services.aws_services import collect_service_data, get_available_services
from datetime import datetime
import json
import logging
from app.services.s3_storage import S3Storage
import threading
import time
import uuid
from functools import wraps

# 로깅 설정 - 중복 로그 방지
logger = logging.getLogger('dashboard')
logger.setLevel(logging.INFO)
# 기존 핸들러 제거
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
# 새 핸들러 추가
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# 상위 로거로 전파 방지
logger.propagate = False

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

# 사용 가능한 서비스 목록
aws_services = get_available_services()

# 사용자 인증 데코레이터
def user_authenticated(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # AWS 자격 증명 가져오기
        auth_type = session.get('auth_type')
        auth_params = session.get('auth_params', {})
        
        if not auth_type or not auth_params:
            flash('AWS 자격 증명이 없습니다. 다시 로그인해주세요.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 데이터 수집 함수
def collect_data(region, user_id, session_id, selected_services=None, auth_type='access_key', auth_params=None):
    # 세션의 수집 상태 가져오기 또는 생성
    if session_id not in collection_statuses:
        collection_statuses[session_id] = get_default_status()
    
    status = collection_statuses[session_id]
    
    # 선택된 서비스가 없으면 오류 로그 기록
    if not selected_services:
        logger.error("선택된 서비스가 없습니다. 데이터 수집을 중단합니다.")
        status['is_collecting'] = False
        return
        
    logger.info(f"collect_data 함수 내부 - 선택된 서비스: {selected_services}")
    
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
    logger.info(f"[{collection_id}] 데이터 수집 시작 - 사용자: {user_id}, 선택된 서비스: {selected_services}")
    
    try:
        # 선택된 서비스만 수집
        for service_key in selected_services:
            if service_key in aws_services:
                service_name = aws_services[service_key]
                status['current_service'] = service_name
                
                logger.info(f"[{collection_id}] {service_name} 데이터 수집 시작")
                
                # 새로운 수집 함수 호출
                service_data = collect_service_data(
                    username=user_id,
                    service_name=service_key,
                    region=region,
                    auth_type=auth_type,
                    **auth_params
                )
                
                # 결과에서 실제 데이터 추출
                if service_data and service_data.get('success'):
                    service_data = service_data.get('result', {})
                
                # 데이터가 None이 아닌지 확인
                if service_data is not None:
                    status['all_services_data'][service_key] = service_data
                    logger.info(f"[{collection_id}] {service_name} 데이터 수집 성공: {type(service_data)}")
                else:
                    logger.warning(f"[{collection_id}] {service_name} 데이터 수집 결과가 None입니다.")
                
                # 완료된 서비스 추가 (서비스 키를 저장)
                status['completed_services'].append(service_key)
                logger.info(f"[{collection_id}] {service_name} 데이터 수집 완료")
        
        # 수집 완료
        status['current_service'] = None
        
        # S3에 수집 데이터 저장
        try:
            # 수집된 데이터 확인
            data_to_save = status['all_services_data']
            logger.info(f"[{collection_id}] 저장할 데이터 키: {list(data_to_save.keys())}")
            
            # 데이터가 비어있는지 확인
            if not data_to_save:
                logger.warning(f"[{collection_id}] 저장할 데이터가 없습니다!")
            
            # 각 서비스 데이터 확인
            for service_key, service_data in data_to_save.items():
                if service_data is None:
                    logger.warning(f"[{collection_id}] 서비스 {service_key}의 데이터가 None입니다.")
                elif not service_data:
                    logger.warning(f"[{collection_id}] 서비스 {service_key}의 데이터가 비어있습니다.")
            
            # 데이터가 비어있으면 빈 객체라도 저장
            for service_key in selected_services:
                if service_key not in data_to_save:
                    logger.warning(f"[{collection_id}] 서비스 {service_key}의 데이터가 없어 빈 객체로 저장합니다.")
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
                logger.info(f"[{collection_id}] 수집 데이터를 S3에 성공적으로 저장했습니다.")
                
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
                    
                    logger.info(f"[{collection_id}] 수집 데이터를 캐시에 직접 저장 완료")
                except Exception as cache_err:
                    logger.warning(f"[{collection_id}] 캐시 저장 중 오류 (무시): {str(cache_err)}")
            else:
                logger.error(f"[{collection_id}] S3에 데이터 저장 실패")
        except Exception as e:
            logger.error(f"[{collection_id}] S3에 데이터 저장 중 오류 발생: {str(e)}")
        
    except Exception as e:
        error_msg = str(e)
        status['error'] = error_msg
        logger.error(f"[{status['collection_id']}] 데이터 수집 오류: {error_msg}")
    finally:
        # 데이터 수집 완료
        status['is_collecting'] = False
        logger.info(f"[{status['collection_id']}] 데이터 수집 완료 - 총 {len(status['completed_services'])}개 서비스")

@app.route('/collections')
@login_required
@user_authenticated
def collections_view():
    """수집 데이터 관리 페이지"""
    # 리소스 경로로 리디렉션
    return redirect(url_for('resource_collections_view'))

@app.route('/service/<collection_id>')
@login_required
@user_authenticated
def service_view(collection_id):
    """특정 수집 데이터의 서비스 정보 보기 (SSR)"""
    # 리소스 경로로 리디렉션
    return redirect(url_for('resource_service_view', collection_id=collection_id))

@app.route('/consolidated')
@login_required
def consolidated_view():
    """기존 통합 대시보드 (이전 버전 호환성 유지)"""
    # 이제 collections_view로 리디렉션
    return redirect(url_for('resource_collections_view'))

@app.route('/start_collection', methods=['POST'])
@login_required
@user_authenticated
def start_collection():
    # 리소스 경로로 리디렉션
    return redirect(url_for('resource_start_collection'))

@app.route('/collection_status')
@login_required
def get_collection_status():
    # 리소스 경로로 리디렉션
    return redirect(url_for('resource_collection_status'))

@app.route('/collections/api')
@login_required
def list_collections():
    """사용자의 모든 수집 데이터 목록 조회 API"""
    user_id = current_user.get_id()
    
    try:
        s3_storage = S3Storage()
        collections = s3_storage.list_user_collections(user_id)
        return jsonify({
            'status': 'success',
            'collections': collections
        })
    except Exception as e:
        logger.error(f"수집 목록 조회 중 오류 발생: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'수집 목록 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/collections/<collection_id>', methods=['DELETE'])
@login_required
def delete_collection(collection_id):
    """특정 수집 데이터 삭제"""
    # 리소스 경로로 리디렉션
    return redirect(url_for('resource_delete_collection', collection_id=collection_id))

def get_session_id():
    """현재 세션의 고유 ID를 생성하거나 가져옵니다."""
    if 'dashboard_session_id' not in session:
        session['dashboard_session_id'] = str(uuid.uuid4())
    return session['dashboard_session_id']

@app.route('/reset_view')
@login_required
def reset_view():
    """현재 보고 있는 collection_id를 초기화하고 처음 화면으로 돌아갑니다."""
    return redirect(url_for('resource_collections_view'))

@app.route('/')
def index():
    """메인 페이지 - 로그인 페이지로 리디렉션"""
    if current_user.is_authenticated:
        return redirect(url_for('resource_collections_view'))
    return redirect(url_for('login'))

def get_user_collections(user_id):
    """사용자의 수집 데이터 목록을 안전하게 가져옵니다."""
    try:
        s3_storage = S3Storage()
        return s3_storage.list_user_collections(user_id)
    except Exception as e:
        logger.error(f"사용자 수집 목록 조회 중 오류 발생: {str(e)}")
        return []