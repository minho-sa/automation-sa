from typing import Dict
from app.services.recommendation.check.lambda_service.utils import logger, get_log_prefix

def check_arm64_architecture(function: Dict, collection_id: str = None) -> Dict:
    """ARM64 아키텍처 마이그레이션 검사"""
    log_prefix = get_log_prefix(collection_id)
    function_name = function.get('FunctionName', 'unknown')
    architectures = function.get('Architectures', ['x86_64'])
    logger.debug(f"{log_prefix}Checking ARM64 architecture for function: {function_name}")
    
    try:
        if 'arm64' not in architectures:
            logger.info(f"{log_prefix}Function {function_name} is not using ARM64 architecture")
            return {
                'service': 'Lambda',
                'resource': function_name,
                'message': "Lambda 함수의 ARM64 아키텍처 마이그레이션을 검토하세요.",
                'severity': '낮음',
                'problem': "Lambda 함수가 x86_64 아키텍처를 사용하고 있습니다.",
                'impact': "ARM64 아키텍처에 비해 비용 효율성이 떨어질 수 있습니다.",
                'benefit': "ARM64 아키텍처로 마이그레이션하면 최대 34%의 비용 절감이 가능합니다.",
                'steps': [
                    "함수 코드의 ARM64 호환성을 검토합니다.",
                    "의존성 라이브러리의 ARM64 지원 여부를 확인합니다.",
                    "테스트 환경에서 ARM64로 전환 테스트를 진행합니다.",
                    "성공적인 테스트 후 프로덕션 환경에 적용합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_arm64_architecture for function {function_name}: {str(e)}")
        return None