import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_external_trust_roles(iam_data, collection_id=None):
    """IAM 역할 신뢰 관계 검사
    
    Args:
        iam_data: IAM 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking external trust relationships")
        
        roles = iam_data.get('roles', [])
        external_trust_roles = []
        
        for role in roles:
            trust_policy = role.get('trust_policy', {})
            statements = trust_policy.get('Statement', [])
            
            for statement in statements:
                if statement.get('Effect') == 'Allow':
                    principal = statement.get('Principal', {})
                    aws_principal = principal.get('AWS', [])
                    
                    if aws_principal:
                        if isinstance(aws_principal, str) and ('*' in aws_principal or ':root' in aws_principal):
                            external_trust_roles.append(role.get('name', 'unknown'))
                        elif isinstance(aws_principal, list):
                            for arn in aws_principal:
                                if '*' in arn or ':root' in arn:
                                    external_trust_roles.append(role.get('name', 'unknown'))
                                    break
        
        if external_trust_roles:
            logger.info(f"{log_prefix}Found {len(external_trust_roles)} roles with external trust relationships")
            return {
                'service': 'IAM',
                'resource': 'Roles',
                'severity': '높음',
                'message': "IAM 역할 신뢰 관계 검토가 필요합니다.",
                'problem': f"{len(external_trust_roles)}개의 역할이 외부 계정에 과도한 권한을 부여하고 있습니다.",
                'impact': "의도하지 않은 계정 간 액세스로 인한 보안 위험이 증가하고 있습니다.",
                'benefit': "적절한 신뢰 관계 설정으로 계정 간 보안 강화가 가능합니다.",
                'steps': [
                    "모든 역할의 신뢰 관계를 검토합니다.",
                    "외부 계정에 대한 액세스를 제한합니다.",
                    "조건부 신뢰 관계를 구성합니다.",
                    "정기적인 신뢰 관계 감사를 수행합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_external_trust_roles: {str(e)}")
        return None