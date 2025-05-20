from app.services.resource.base_service import create_boto3_client
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytz
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_lambda_data(region: str, collection_id: str = None, auth_type: str = 'access_key', **auth_params) -> Dict:
    """
    Lambda 함수 데이터 수집
    
    Args:
        region: AWS 리전
        collection_id: 수집 ID (선택 사항)
        auth_type: 인증 유형 ('access_key' 또는 'role_arn')
        **auth_params: 인증 유형에 따른 추가 파라미터
            - access_key 인증: aws_access_key, aws_secret_key, aws_session_token(선택)
            - role_arn 인증: role_arn, server_access_key, server_secret_key
    
    Returns:
        수집된 Lambda 데이터
    """
    # collection_id가 None이 아닌지 확인
    if collection_id is None:
        collection_id = "lambda-collection"
    
    log_prefix = f"[{collection_id}]"
    logger.info(f"{log_prefix} Starting Lambda data collection using {auth_type} authentication")
    try:
        lambda_client = create_boto3_client('lambda', region, auth_type=auth_type, **auth_params)
        cloudwatch = create_boto3_client('cloudwatch', region, auth_type=auth_type, **auth_params)

        response = lambda_client.list_functions()
        functions = []
        
        logger.info(f"{log_prefix} Found {len(response.get('Functions', []))} Lambda functions")
        
        for function in response.get('Functions', []):
            logger.debug(f"{log_prefix} Processing function {function['FunctionName']}")
            
            # 기본 함수 정보
            function_data = {
                'FunctionName': function['FunctionName'],
                'FunctionArn': function['FunctionArn'],
                'Runtime': function['Runtime'],
                'MemorySize': function['MemorySize'],
                'Timeout': function['Timeout'],
                'CodeSize': function['CodeSize'],
                'LastModified': function['LastModified'],
                'Handler': function['Handler'],
                'Environment': function.get('Environment', {}).get('Variables', {}),
                'TracingConfig': function.get('TracingConfig', {}).get('Mode', 'PassThrough'),
                'Architectures': function.get('Architectures', ['x86_64']),
                'Tags': {},
                'ReservedConcurrency': None,
                'DeadLetterConfig': function.get('DeadLetterConfig', {}),
                'Layers': function.get('Layers', []),
                'VersionsInfo': [],
                'UrlConfig': None,
                'VpcConfig': function.get('VpcConfig', {})
            }
            
            # 태그 정보 수집
            logger.debug(f"{log_prefix} Collecting tags for {function['FunctionName']}")
            try:
                tags_response = lambda_client.list_tags(Resource=function['FunctionArn'])
                function_data['Tags'] = tags_response.get('Tags', {})
            except Exception as e:
                logger.error(f"{log_prefix} Error collecting tags: {str(e)}")
            
            # 예약된 동시성 정보 수집
            logger.debug(f"{log_prefix} Collecting concurrency info for {function['FunctionName']}")
            try:
                concurrency = lambda_client.get_function_concurrency(
                    FunctionName=function['FunctionName']
                )
                function_data['ReservedConcurrency'] = concurrency.get('ReservedConcurrentExecutions')
            except Exception as e:
                logger.error(f"{log_prefix} Error collecting concurrency info: {str(e)}")
            
            # 함수 URL 구성 정보 수집
            logger.debug(f"{log_prefix} Collecting URL config for {function['FunctionName']}")
            try:
                url_config = lambda_client.get_function_url_config(
                    FunctionName=function['FunctionName']
                )
                function_data['UrlConfig'] = {
                    'AuthType': url_config.get('AuthType'),
                    'Url': url_config.get('FunctionUrl')
                }
            except Exception as e:
                # URL이 구성되지 않은 경우 예외 발생, 무시
                pass
            
            # 버전 정보 수집
            logger.debug(f"{log_prefix} Collecting versions for {function['FunctionName']}")
            try:
                versions = lambda_client.list_versions_by_function(
                    FunctionName=function['FunctionName']
                )
                function_data['VersionsInfo'] = [
                    {'Version': v.get('Version')} for v in versions.get('Versions', [])
                ]
            except Exception as e:
                logger.error(f"{log_prefix} Error collecting versions: {str(e)}")
            
            # 로그 출력 검사
            logger.debug(f"{log_prefix} Checking debug logs for {function['FunctionName']}")
            function_data['DebugLogsDetected'] = _check_debug_logs(
                region, function['FunctionName'], collection_id, auth_type, **auth_params
            )
            
            functions.append(function_data)
        
        result = {'functions': functions}
        logger.info(f"{log_prefix} Completed Lambda data collection")
        return result
    except Exception as e:
        logger.error(f"{log_prefix} Error in get_lambda_data: {str(e)}")
        return {'error': str(e)}

def _check_debug_logs(region: str, function_name: str, collection_id: str = None, auth_type: str = 'access_key', **auth_params) -> bool:
    """
    디버깅 로그 출력 검사
    
    Args:
        region: AWS 리전
        function_name: Lambda 함수 이름
        collection_id: 수집 ID (선택 사항)
        auth_type: 인증 유형 ('access_key' 또는 'role_arn')
        **auth_params: 인증 유형에 따른 추가 파라미터
    
    Returns:
        디버깅 로그 존재 여부
    """
    # collection_id가 None이 아닌지 확인
    if collection_id is None:
        collection_id = "lambda-collection"
        
    log_prefix = f"[{collection_id}]"
    try:
        logs_client = create_boto3_client('logs', region, auth_type=auth_type, **auth_params)
        
        # 로그 그룹 이름 형식
        log_group_name = f"/aws/lambda/{function_name}"
        
        # 로그 그룹 존재 여부 확인
        log_groups = logs_client.describe_log_groups(
            logGroupNamePrefix=log_group_name,
            limit=1
        )
        
        # 로그 그룹이 존재하지 않으면 디버깅 로그가 없다고 판단
        if not log_groups.get('logGroups'):
            logger.info(f"{log_prefix} Log group {log_group_name} does not exist for function {function_name}")
            return False
            
        # 최근 로그 이벤트 검색
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            limit=100
        )
        
        # 디버깅 로그 패턴 검색
        debug_patterns = ['console.log(', 'print(', 'logger.debug(', 'System.out.println(']
        for event in response.get('events', []):
            message = event.get('message', '')
            for pattern in debug_patterns:
                if pattern in message:
                    return True
        
        return False
    except Exception as e:
        logger.error(f"{log_prefix} Error checking debug logs: {str(e)}")
        return False