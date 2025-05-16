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
        
        # 사용자 목록 추출
        users = []
        if isinstance(iam_data, list):
            users = iam_data
            iam_data = {'users': users, 'root_account': {}, 'password_policy': {}, 'roles': [], 'policies': []}
        elif isinstance(iam_data, dict) and 'users' in iam_data:
            users = iam_data.get('users', [])
        
        logger.info(f"{log_prefix}Analyzing {len(users)} users for recommendations")
        
        # 권장사항 수집
        recommendations = []
        
        # 1. 루트 계정 액세스 키 검사
        root_rec = check_root_account_access_key(iam_data, collection_id)
        if root_rec:
            recommendations.append(root_rec)
        
        # 2. 사용자별 검사
        for user in users:
            user_name = user.get('name', 'unknown')
            logger.debug(f"{log_prefix}Checking recommendations for user {user_name}")
            
            # MFA 검사
            if user.get('password_enabled') and not user.get('mfa_enabled'):
                mfa_rec = check_mfa_enabled({'user': user}, collection_id)
                if mfa_rec:
                    recommendations.append(mfa_rec)
            
            # 미사용 자격 증명 검사
            unused_rec = check_unused_credentials({'user': user}, collection_id)
            if unused_rec:
                recommendations.append(unused_rec)
            
            # 직접 연결된 정책 검사
            if user.get('policies'):
                policy_rec = check_direct_attached_policies({'user': user}, collection_id)
                if policy_rec:
                    recommendations.append(policy_rec)
            
            # 액세스 키 교체 검사
            key_rec = check_access_key_rotation({'user': user}, collection_id)
            if key_rec:
                recommendations.append(key_rec)
        
        # 3. 정책 검사
        policies = iam_data.get('policies', [])
        for policy in policies:
            policy_name = policy.get('name', 'unknown')
            logger.debug(f"{log_prefix}Checking recommendations for policy {policy_name}")
            
            # 과도한 권한 검사
            perm_rec = check_excessive_permissions({'policy': policy}, collection_id)
            if perm_rec:
                recommendations.append(perm_rec)
        
        # 4. 역할 검사
        roles = iam_data.get('roles', [])
        for role in roles:
            role_name = role.get('name', 'unknown')
            logger.debug(f"{log_prefix}Checking recommendations for role {role_name}")
            
            # 외부 신뢰 관계 검사
            trust_rec = check_external_trust_roles({'role': role}, collection_id)
            if trust_rec:
                recommendations.append(trust_rec)
            
            # 서비스 연결 역할 검사
            if role.get('name', '').startswith('AWS') and not role.get('service_linked'):
                service_rec = check_service_linked_roles({'role': role}, collection_id)
                if service_rec:
                    recommendations.append(service_rec)
        
        # 5. 비밀번호 정책 검사
        password_policy = iam_data.get('password_policy', {})
        if password_policy:
            policy_rec = check_password_policy({'password_policy': password_policy}, collection_id)
            if policy_rec:
                recommendations.append(policy_rec)
        
        logger.info(f"{log_prefix}Successfully collected {len(recommendations)} IAM recommendations")
        return recommendations
        
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_iam_recommendations: {str(e)}")
        return []