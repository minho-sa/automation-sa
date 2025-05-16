import logging
import traceback
from typing import Dict, List, Any

# 개별 체크 함수 직접 임포트
from app.services.recommendation.check.lambda_service.memory_size import check_memory_size
from app.services.recommendation.check.lambda_service.timeout_setting import check_timeout_setting
from app.services.recommendation.check.lambda_service.runtime_version import check_runtime_version
from app.services.recommendation.check.lambda_service.code_size import check_code_size
from app.services.recommendation.check.lambda_service.xray_tracing import check_xray_tracing
from app.services.recommendation.check.lambda_service.vpc_configuration import check_vpc_configuration
from app.services.recommendation.check.lambda_service.arm64_architecture import check_arm64_architecture
from app.services.recommendation.check.lambda_service.environment_encryption import check_environment_encryption
from app.services.recommendation.check.lambda_service.tag_management import check_tag_management
from app.services.recommendation.check.lambda_service.public_url_endpoint import check_public_url_endpoint
from app.services.recommendation.check.lambda_service.public_layers import check_public_layers
from app.services.recommendation.check.lambda_service.debug_logs_output import check_debug_logs_output
from app.services.recommendation.check.lambda_service.reserved_concurrency import check_reserved_concurrency
from app.services.recommendation.check.lambda_service.dead_letter_queue import check_dead_letter_queue
from app.services.recommendation.check.lambda_service.version_alias_usage import check_version_alias_usage

# 로깅 설정
logger = logging.getLogger(__name__)

def get_lambda_recommendations(functions: List[Dict], collection_id: str = None) -> List[Dict]:
    """Lambda 함수에 대한 권장사항 수집"""
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.info(f"{log_prefix}Starting Lambda recommendations collection")
    
    try:
        # functions 데이터 형식 처리
        if isinstance(functions, dict) and 'functions' in functions:
            function_list = functions['functions']
        elif isinstance(functions, dict):
            function_list = [functions]
        elif isinstance(functions, list):
            function_list = functions
        else:
            logger.error(f"{log_prefix}Unexpected data type: {type(functions)}")
            return []
            
        logger.info(f"{log_prefix}Analyzing {len(function_list)} functions for recommendations")
        
        # 권장사항 수집
        recommendations = []
        
        for function in function_list:
            function_name = function.get('FunctionName', 'unknown')
            logger.debug(f"{log_prefix}Checking recommendations for function {function_name}")
            
            # 각 체크 함수 실행
            function_recommendations = []
            
            try:
                # 메모리 크기 체크
                if function.get('MemorySize', 0) > 512:
                    memory_rec = check_memory_size(function, collection_id)
                    if memory_rec:
                        function_recommendations.append(memory_rec)
                
                # 타임아웃 설정 체크
                if function.get('Timeout', 0) > 60:
                    timeout_rec = check_timeout_setting(function, collection_id)
                    if timeout_rec:
                        function_recommendations.append(timeout_rec)
                
                # 런타임 버전 체크
                if function.get('Runtime'):
                    runtime_rec = check_runtime_version(function, collection_id)
                    if runtime_rec:
                        function_recommendations.append(runtime_rec)
                
                # 코드 크기 체크
                if function.get('CodeSize', 0) > 5 * 1024 * 1024:
                    code_size_rec = check_code_size(function, collection_id)
                    if code_size_rec:
                        function_recommendations.append(code_size_rec)
                
                # X-Ray 추적 체크
                if function.get('TracingConfig') == 'PassThrough':
                    xray_rec = check_xray_tracing(function, collection_id)
                    if xray_rec:
                        function_recommendations.append(xray_rec)
                
                # VPC 구성 체크
                vpc_config = function.get('VpcConfig')
                if not (vpc_config and isinstance(vpc_config, dict) and vpc_config.get('VpcId')):
                    vpc_rec = check_vpc_configuration(function, collection_id)
                    if vpc_rec:
                        function_recommendations.append(vpc_rec)
                
                # 환경 변수 암호화 체크
                env = function.get('Environment')
                if env and isinstance(env, dict):
                    env_rec = check_environment_encryption(function, collection_id)
                    if env_rec:
                        function_recommendations.append(env_rec)
                
                # ARM64 아키텍처 체크
                if 'arm64' not in function.get('Architectures', []):
                    arm64_rec = check_arm64_architecture(function, collection_id)
                    if arm64_rec:
                        function_recommendations.append(arm64_rec)
                
                # 태그 관리 체크
                if not function.get('Tags'):
                    tag_rec = check_tag_management(function, collection_id)
                    if tag_rec:
                        function_recommendations.append(tag_rec)
                
                # 공개 URL 엔드포인트 체크
                url_config = function.get('UrlConfig')
                if url_config and isinstance(url_config, dict) and url_config.get('AuthType') == 'NONE':
                    url_rec = check_public_url_endpoint(function, collection_id)
                    if url_rec:
                        function_recommendations.append(url_rec)
                
                # 공개 레이어 체크
                layers = function.get('Layers')
                if layers and isinstance(layers, list) and len(layers) > 0:
                    layer_rec = check_public_layers(function, collection_id)
                    if layer_rec:
                        function_recommendations.append(layer_rec)
                
                # 디버그 로그 출력 체크
                if function.get('DebugLogsDetected'):
                    debug_rec = check_debug_logs_output(function, collection_id)
                    if debug_rec:
                        function_recommendations.append(debug_rec)
                
                # 예약된 동시성 체크
                if function.get('ReservedConcurrency') is None:
                    concurrency_rec = check_reserved_concurrency(function, collection_id)
                    if concurrency_rec:
                        function_recommendations.append(concurrency_rec)
                
                # 데드 레터 큐 체크
                dlq_config = function.get('DeadLetterConfig')
                if not (dlq_config and isinstance(dlq_config, dict) and dlq_config.get('TargetArn')):
                    dlq_rec = check_dead_letter_queue(function, collection_id)
                    if dlq_rec:
                        function_recommendations.append(dlq_rec)
                
                # 버전 별칭 사용 체크
                versions_info = function.get('VersionsInfo')
                if versions_info and isinstance(versions_info, list) and len(versions_info) > 0:
                    version_rec = check_version_alias_usage(function, collection_id)
                    if version_rec:
                        function_recommendations.append(version_rec)
                
            except Exception as e:
                logger.error(f"{log_prefix}Error checking function {function_name}: {str(e)}")
                logger.error(traceback.format_exc())
                continue
            
            if function_recommendations:
                logger.info(f"{log_prefix}Found {len(function_recommendations)} recommendations for function {function_name}")
                recommendations.extend(function_recommendations)
        
        logger.info(f"{log_prefix}Successfully collected {len(recommendations)} recommendations")
        return recommendations
        
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_lambda_recommendations: {str(e)}")
        logger.error(traceback.format_exc())
        return []