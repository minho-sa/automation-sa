from typing import Dict, List, Any
import logging

# Import check functions from individual files
from app.services.recommendation.check.lambda_service import (
    check_memory_size,
    check_timeout_setting,
    check_runtime_version,
    check_code_size,
    check_xray_tracing,
    check_vpc_configuration,
    check_arm64_architecture,
    check_environment_encryption,
    check_tag_management,
    check_public_url_endpoint,
    check_public_layers,
    check_debug_logs_output,
    check_reserved_concurrency,
    check_dead_letter_queue,
    check_version_alias_usage
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_lambda_recommendations(functions: Dict, collection_id: str = None) -> List[Dict]:
    """Lambda 함수 추천 사항 수집"""
    # collection_id가 None이 아닌지 확인
    if collection_id is None:
        collection_id = "lambda-recommendation"
        
    log_prefix = f"[{collection_id}]"
    logger.info(f"{log_prefix} Starting Lambda recommendations analysis")
    try:
        recommendations = []

        if not functions:
            logger.warning(f"{log_prefix} No Lambda functions data provided")
            return []

        # functions가 리스트인 경우
        if isinstance(functions, list):
            function_list = functions
        # functions가 딕셔너리이고 'functions' 키가 있는 경우
        elif isinstance(functions, dict) and 'functions' in functions:
            function_list = functions['functions']
        # functions가 딕셔너리이지만 'functions' 키가 없는 경우
        elif isinstance(functions, dict):
            function_list = [functions]
        else:
            logger.error(f"{log_prefix} Unexpected data type: {type(functions)}")
            return []

        logger.info(f"{log_prefix} Processing {len(function_list)} functions")

        for function in function_list:
            function_name = function.get('FunctionName', 'unknown')
            logger.info(f"{log_prefix} Processing function: {function_name}")

            try:
                # 1. 메모리 설정 검사
                if function.get('MemorySize', 0) > 512:
                    logger.debug(f"{log_prefix} Checking memory size for {function_name}")
                    memory_rec = check_memory_size(function, collection_id)
                    if memory_rec:
                        recommendations.append(memory_rec)

                # 2. 타임아웃 설정 검사
                if function.get('Timeout', 0) > 60:
                    logger.debug(f"{log_prefix} Checking timeout setting for {function_name}")
                    timeout_rec = check_timeout_setting(function, collection_id)
                    if timeout_rec:
                        recommendations.append(timeout_rec)

                # 3. 런타임 버전 검사
                if function.get('Runtime'):
                    logger.debug(f"{log_prefix} Checking runtime version for {function_name}")
                    runtime_rec = check_runtime_version(function, collection_id)
                    if runtime_rec:
                        recommendations.append(runtime_rec)

                # 4. 코드 크기 검사
                if function.get('CodeSize', 0) > 5 * 1024 * 1024:  # 5MB
                    logger.debug(f"{log_prefix} Checking code size for {function_name}")
                    code_size_rec = check_code_size(function, collection_id)
                    if code_size_rec:
                        recommendations.append(code_size_rec)

                # 5. X-Ray 추적 검사
                if function.get('TracingConfig') == 'PassThrough':
                    logger.debug(f"{log_prefix} Checking X-Ray tracing for {function_name}")
                    xray_rec = check_xray_tracing(function, collection_id)
                    if xray_rec:
                        recommendations.append(xray_rec)

                # 6. VPC 구성 검사
                vpc_config = function.get('VpcConfig', {})
                if not vpc_config or not vpc_config.get('VpcId'):
                    logger.debug(f"{log_prefix} Checking VPC configuration for {function_name}")
                    vpc_rec = check_vpc_configuration(function, collection_id)
                    if vpc_rec:
                        recommendations.append(vpc_rec)

                # 7. 환경 변수 암호화 검사
                if function.get('Environment'):
                    logger.debug(f"{log_prefix} Checking environment encryption for {function_name}")
                    env_rec = check_environment_encryption(function, collection_id)
                    if env_rec:
                        recommendations.append(env_rec)

                # 8. ARM64 아키텍처 마이그레이션 검사
                if 'arm64' not in function.get('Architectures', []):
                    logger.debug(f"{log_prefix} Checking ARM64 architecture for {function_name}")
                    arm64_rec = check_arm64_architecture(function, collection_id)
                    if arm64_rec:
                        recommendations.append(arm64_rec)

                # 9. 태그 관리 검사
                if not function.get('Tags'):
                    logger.debug(f"{log_prefix} Checking tag management for {function_name}")
                    tag_rec = check_tag_management(function, collection_id)
                    if tag_rec:
                        recommendations.append(tag_rec)

                # 10. 공개된 Lambda URL 엔드포인트 검사
                if function.get('UrlConfig') and function.get('UrlConfig', {}).get('AuthType') == 'NONE':
                    logger.debug(f"{log_prefix} Checking public URL endpoint for {function_name}")
                    url_rec = check_public_url_endpoint(function, collection_id)
                    if url_rec:
                        recommendations.append(url_rec)

                # 11. 퍼블릭 Layer 사용 검사
                if function.get('Layers'):
                    logger.debug(f"{log_prefix} Checking public layers for {function_name}")
                    layer_rec = check_public_layers(function, collection_id)
                    if layer_rec:
                        recommendations.append(layer_rec)

                # 12. 디버깅 로그 출력 검사
                if function.get('DebugLogsDetected'):
                    logger.debug(f"{log_prefix} Checking debug logs output for {function_name}")
                    debug_rec = check_debug_logs_output(function, collection_id)
                    if debug_rec:
                        recommendations.append(debug_rec)

                # 13. Reserved Concurrency 미설정 검사
                if function.get('ReservedConcurrency') is None:
                    logger.debug(f"{log_prefix} Checking reserved concurrency for {function_name}")
                    concurrency_rec = check_reserved_concurrency(function, collection_id)
                    if concurrency_rec:
                        recommendations.append(concurrency_rec)

                # 14. Dead Letter Queue (DLQ) 미설정 검사
                if not function.get('DeadLetterConfig'):
                    logger.debug(f"{log_prefix} Checking dead letter queue for {function_name}")
                    dlq_rec = check_dead_letter_queue(function, collection_id)
                    if dlq_rec:
                        recommendations.append(dlq_rec)

                # 15. 최신 버전 alias 미사용 검사
                if function.get('VersionsInfo'):
                    logger.debug(f"{log_prefix} Checking version alias usage for {function_name}")
                    version_rec = check_version_alias_usage(function, collection_id)
                    if version_rec:
                        recommendations.append(version_rec)

            except Exception as e:
                logger.error(f"{log_prefix} Error processing function {function_name}: {str(e)}")
                continue

        logger.info(f"{log_prefix} Found {len(recommendations)} recommendations for Lambda functions")
        return recommendations
    except Exception as e:
        logger.error(f"{log_prefix} Error in get_lambda_recommendations: {str(e)}")
        return []