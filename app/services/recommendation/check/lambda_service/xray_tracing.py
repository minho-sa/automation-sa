from typing import Dict
from app.services.recommendation.check.lambda_service.utils import logger, get_log_prefix

def check_xray_tracing(function: Dict, collection_id: str = None) -> Dict:
    """X-Ray 추적 검사"""
    log_prefix = get_log_prefix(collection_id)
    function_name = function.get('FunctionName', 'unknown')
    tracing_config = function.get('TracingConfig', 'PassThrough')
    logger.debug(f"{log_prefix}Checking X-Ray tracing for function: {function_name}")
    
    try:
        if tracing_config == 'PassThrough':
            logger.info(f"{log_prefix}Function {function_name} has X-Ray tracing disabled")
            return {
                'service': 'Lambda',
                'resource': function_name,
                'message': "X-Ray 추적 설정을 점검하세요.",
                'severity': '낮음',
                'problem': "X-Ray 추적이 비활성화되어 있습니다.",
                'impact': "함수 성능이나 오류 원인을 분석하기 어렵습니다.",
                'benefit': "X-Ray 추적을 통해 성능 병목 및 문제점을 빠르게 식별할 수 있습니다.",
                'steps': [
                    "Lambda 콘솔에서 함수 구성을 편집합니다.",
                    "모니터링 설정에서 X-Ray를 활성화합니다.",
                    "필요한 IAM 권한을 부여합니다.",
                    "X-Ray 콘솔에서 추적 결과를 확인합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_xray_tracing for function {function_name}: {str(e)}")
        return None