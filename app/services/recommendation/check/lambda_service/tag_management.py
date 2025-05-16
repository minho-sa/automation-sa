from typing import Dict
from app.services.recommendation.check.lambda_service.utils import logger, get_log_prefix

def check_tag_management(function: Dict, collection_id: str = None) -> Dict:
    """태그 관리 검사"""
    log_prefix = get_log_prefix(collection_id)
    function_name = function.get('FunctionName', 'unknown')
    tags = function.get('Tags', {})
    logger.debug(f"{log_prefix}Checking tag management for function: {function_name}")
    
    try:
        if not tags:
            logger.info(f"{log_prefix}Function {function_name} has no tags")
            return {
                'service': 'Lambda',
                'resource': function_name,
                'message': "Lambda 함수에 태그를 추가하세요.",
                'severity': '낮음',
                'problem': "Lambda 함수에 태그가 설정되어 있지 않습니다.",
                'impact': "리소스 관리, 비용 할당 및 자동화가 어려울 수 있습니다.",
                'benefit': "태그를 통해 리소스 관리, 비용 추적 및 자동화를 개선할 수 있습니다.",
                'steps': [
                    "조직의 태그 지정 전략을 검토합니다.",
                    "필수 태그(예: Owner, Environment, Project)를 식별합니다.",
                    "Lambda 함수에 태그를 적용합니다.",
                    "태그 기반 정책 및 자동화를 구현합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_tag_management for function {function_name}: {str(e)}")
        return None