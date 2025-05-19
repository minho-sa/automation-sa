from flask import render_template, redirect, url_for, flash, session, jsonify, request
from flask_login import login_required, current_user
from app import app
from app.services.aws_services import aws_services
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
import threading
import time
import uuid

# 데이터 수집 상태를 추적하기 위한 전역 변수
collection_status = {
    'is_collecting': False,
    'current_service': None,
    'completed_services': [],
    'total_services': 0,  # 선택된 서비스 수에 따라 동적으로 설정
    'error': None,
    'all_services_data': {},
    'user_id': None,  # 사용자별 상태 추적을 위한 ID
    'collection_id': None,  # 데이터 수집 ID
    'selected_services': [],  # 사용자가 선택한 서비스 목록
    'last_collection_time': 0  # 마지막 수집 시작 시간
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
def collect_data(aws_access_key, aws_secret_key, region, user_id, selected_services=None):
    global collection_status
    
    # 선택된 서비스가 없으면 오류 로그 기록
    if not selected_services:
        app.logger.error("선택된 서비스가 없습니다. 데이터 수집을 중단합니다.")
        collection_status['is_collecting'] = False
        return
        
    app.logger.info(f"collect_data 함수 내부 - 선택된 서비스: {selected_services}")
    
    # 항상 데이터 초기화 (이전 데이터 유지하지 않음)
    collection_status['all_services_data'] = {}
    
    # 상태 초기화
    collection_status['is_collecting'] = True
    collection_status['current_service'] = None
    collection_status['completed_services'] = []  # 완료된 서비스 목록 초기화
    collection_status['error'] = None
    collection_status['user_id'] = user_id
    collection_status['selected_services'] = selected_services.copy()  # 복사본 사용
    collection_status['total_services'] = len(selected_services)
    collection_status['collection_id'] = str(uuid.uuid4())[:8]  # 고유한 수집 ID 생성
    
    # 로그에 수집 ID 기록
    collection_id = collection_status['collection_id']
    app.logger.info(f"[{collection_id}] 데이터 수집 시작 - 사용자: {user_id}, 선택된 서비스: {selected_services}")
    
    try:
        # 선택된 서비스만 수집
        for service_key in selected_services:
            if service_key in service_collectors:
                service_name = aws_services[service_key]['name']
                collection_status['current_service'] = service_name
                
                app.logger.info(f"[{collection_id}] {service_name} 데이터 수집 시작")
                
                # 해당 서비스의 데이터 수집 함수 호출
                collection_status['all_services_data'][service_key] = service_collectors[service_key](
                    aws_access_key, aws_secret_key, region, collection_status['collection_id']
                )
                
                # 완료된 서비스 추가 (서비스 키를 저장)
                collection_status['completed_services'].append(service_key)
                app.logger.info(f"[{collection_id}] {service_name} 데이터 수집 완료")
        
        # 수집 완료
        collection_status['current_service'] = None
        
    except Exception as e:
        error_msg = str(e)
        collection_status['error'] = error_msg
        app.logger.error(f"[{collection_status['collection_id']}] 데이터 수집 오류: {error_msg}")
    finally:
        collection_status['is_collecting'] = False
        app.logger.info(f"[{collection_status['collection_id']}] 데이터 수집 완료 - 총 {len(collection_status['completed_services'])}개 서비스")

@app.route('/consolidated')
@login_required
def consolidated_view():
    # AWS 자격 증명 가져오기
    aws_access_key = session.get('aws_access_key')
    aws_secret_key = session.get('aws_secret_key')
    
    if not aws_access_key or not aws_secret_key:
        flash('AWS 자격 증명이 없습니다. 다시 로그인해주세요.')
        return redirect(url_for('login'))
    
    region = app.config.get('AWS_DEFAULT_REGION', 'ap-northeast-2')
    user_id = current_user.get_id()
    
    # 데이터 수집 상태 확인
    global collection_status
    
    # 페이지 로드 시 is_collecting 상태 초기화 (서버 재시작 후 상태가 잘못 유지되는 경우 대비)
    current_time = time.time()
    last_collection_time = collection_status.get('last_collection_time', 0)
    
    # 마지막 수집 시작 후 30초 이상 지났으면 초기화
    if current_time - last_collection_time > 30:
        collection_status['is_collecting'] = False
    
    # 수집 중인 경우 진행 상태 표시
    if collection_status['is_collecting'] and collection_status['user_id'] == user_id:
        # 모든 서비스에 대한 빈 데이터 구조 생성
        empty_services_data = {}
        for service_key in aws_services.keys():
            empty_services_data[service_key] = {'status': 'collecting'}
            
        # 이미 수집된 서비스 데이터는 유지
        for service_key, service_data in collection_status['all_services_data'].items():
            empty_services_data[service_key] = service_data
            
        return render_template('consolidated.html', 
                              services=aws_services, 
                              all_services_data=empty_services_data, 
                              resource_recommendations={},
                              is_collecting=collection_status['is_collecting'],
                              current_service=collection_status['current_service'],
                              completed_services=collection_status['completed_services'],
                              total_services=collection_status['total_services'],
                              error=collection_status['error'],
                              show_collection_message=False,
                              selected_services=collection_status['selected_services'])
    
    # 데이터 수집이 완료되지 않은 경우 (completed_services가 비어있는 경우)
    # 또는 현재 사용자의 데이터가 없는 경우
    if not collection_status['completed_services'] or collection_status['user_id'] != user_id:
        # 데이터 수집 버튼을 표시하는 페이지 렌더링
        flash('서비스 정보를 보기 전에 먼저 데이터를 수집해야 합니다. 데이터 수집 버튼을 클릭하세요.')
        return render_template('consolidated.html', 
                              services=aws_services,
                              all_services_data={},
                              is_collecting=False,
                              show_collection_message=True)
                              
    # 데이터가 있는 경우 표시 (선택한 서비스만)
    filtered_services_data = {}
    for service_key in collection_status.get('selected_services', []):
        if service_key in collection_status['all_services_data']:
            filtered_services_data[service_key] = collection_status['all_services_data'][service_key]
    
    return render_template('consolidated.html',
                          services=aws_services,
                          all_services_data=filtered_services_data,  # 선택한 서비스 데이터만 전달
                          resource_recommendations={},
                          is_collecting=False,
                          completed_services=collection_status['completed_services'],
                          total_services=collection_status['total_services'],
                          error=collection_status['error'],
                          show_collection_message=False,
                          selected_services=collection_status.get('selected_services', []))

@app.route('/start_collection', methods=['POST'])
@login_required
def start_collection():
    try:
        # AWS 자격 증명 가져오기
        aws_access_key = session.get('aws_access_key')
        aws_secret_key = session.get('aws_secret_key')
        
        if not aws_access_key or not aws_secret_key:
            return jsonify({'status': 'error', 'message': 'AWS 자격 증명이 없습니다. 다시 로그인해주세요.'}), 401
        
        region = app.config.get('AWS_DEFAULT_REGION', 'ap-northeast-2')
        user_id = current_user.get_id()
        
        # 이미 수집 중인 경우 중복 요청 방지
        global collection_status
        if collection_status['is_collecting']:
            app.logger.warning(f"이미 데이터 수집이 진행 중입니다. 사용자: {user_id}")
            return jsonify({'status': 'error', 'message': '이미 데이터 수집이 진행 중입니다. 완료될 때까지 기다려주세요.'}), 409
        
        # 항상 새로운 수집을 시작할 수 있도록 상태 완전히 초기화
        collection_status['is_collecting'] = False
        collection_status['last_collection_time'] = time.time()
        collection_status['all_services_data'] = {}  # 이전 데이터 완전히 초기화
        collection_status['completed_services'] = []  # 완료된 서비스 목록 초기화
        collection_status['current_service'] = None
        
        # 요청 데이터 확인
        if not request.is_json:
            return jsonify({'status': 'error', 'message': '잘못된 요청 형식입니다.'}), 400
        
        request_data = request.get_json()
        selected_services = request_data.get('selected_services')
        
        # 선택된 서비스가 없는 경우
        if not selected_services:
            return jsonify({'status': 'error', 'message': '최소한 하나 이상의 서비스를 선택해야 합니다.'}), 400
        
        # 수집 상태를 먼저 설정하여 중복 요청 방지
        collection_status['is_collecting'] = True
        
        # 데이터 수집 시작
        thread = threading.Thread(target=collect_data, args=(aws_access_key, aws_secret_key, region, user_id, selected_services))
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'success', 'message': '데이터 수집이 시작되었습니다.'}), 200
    except Exception as e:
        app.logger.error(f"요청 처리 중 오류 발생: {str(e)}")
        return jsonify({'status': 'error', 'message': f'요청 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/collection_status')
@login_required
def get_collection_status():
    user_id = current_user.get_id()
    global collection_status
    
    # 현재 사용자의 수집 상태만 반환
    if collection_status['user_id'] != user_id:
        return jsonify({
            'is_collecting': False,
            'current_service': None,
            'completed_services': [],
            'total_services': 0,
            'error': None,
            'progress': 0
        })
    
    # 서비스 키를 서비스 이름으로 변환 (중복 제거)
    unique_service_keys = set(collection_status['completed_services'])
    completed_service_names = []
    for service_key in unique_service_keys:
        if service_key in aws_services:
            completed_service_names.append(aws_services[service_key]['name'])
    
    # 진행률 계산 (중복 제거된 서비스 수 기준)
    progress = 0
    if collection_status['total_services'] > 0:
        unique_completed = len(set(collection_status['completed_services']))
        progress = min(int(unique_completed / collection_status['total_services'] * 100), 100)
    
    # 선택된 서비스 목록도 함께 반환
    return jsonify({
        'is_collecting': collection_status['is_collecting'],
        'current_service': collection_status['current_service'],
        'completed_services': completed_service_names,  # 서비스 이름 목록 반환
        'total_services': collection_status['total_services'],
        'error': collection_status['error'],
        'progress': progress,
        'selected_services': collection_status.get('selected_services', [])  # 선택된 서비스 목록 추가
    })