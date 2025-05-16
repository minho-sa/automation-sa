import logging
from typing import Dict, List, Any
from app.services.recommendation.check.iam import (
    check_root_account_access_key,
    check_mfa_enabled,
    check_unused_credentials,
    check_excessive_permissions,
    check_external_trust_roles,
    check_direct_attached_policies,
    check_access_key_rotation,
    check_password_policy,
    check_service_linked_roles
)

# 로깅 설정
logger = logging.getLogger(__name__)

def get_iam_recommendations(iam_data: Dict, collection_id: str = None) -> List[Dict]:
    """IAM 데이터에 대한 권장사항 수집"""
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.info(f"{log_prefix}Starting IAM recommendations collection")
    
    try:
        # 데이터 유효성 검사
        if not iam_data or isinstance(iam_data, dict) and iam_data.get('error'):
            logger.warning(f"{log_prefix}Invalid IAM data provided")
            return []
            
        logger.info(f"{log_prefix}Analyzing IAM data for recommendations")
        
        # 권장사항 수집
        recommendations = []
        
        # 각 체크 함수 실행
        checks = [
            check_root_account_access_key(iam_data, collection_id),
            check_mfa_enabled(iam_data, collection_id),
            check_unused_credentials(iam_data, collection_id),
            check_excessive_permissions(iam_data, collection_id),
            check_external_trust_roles(iam_data, collection_id),
            check_direct_attached_policies(iam_data, collection_id),
            check_access_key_rotation(iam_data, collection_id),
            check_password_policy(iam_data, collection_id),
            check_service_linked_roles(iam_data, collection_id)
        ]
        
        # 결과 필터링 (None 제외)
        recommendations = [check for check in checks if check]
        
        logger.info(f"{log_prefix}Successfully collected {len(recommendations)} IAM recommendations")
        return recommendations
        
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_iam_recommendations: {str(e)}")
        return []