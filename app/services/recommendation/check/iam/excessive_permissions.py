import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_excessive_permissions(iam_data, collection_id=None):
    """IAM 정책 권한 검사
    
    Args:
        iam_data: IAM 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking excessive permissions")
        
        policies = iam_data.get('policies', [])
        excessive_policies = []
        
        for policy in policies:
            document = policy.get('document', {})
            statements = document.get('Statement', [])
            
            for statement in statements:
                if statement.get('Effect') == 'Allow':
                    action = statement.get('Action', [])
                    resource = statement.get('Resource', [])
                    
                    # 와일드카드 권한 확인
                    if (isinstance(action, str) and action == '*') or (isinstance(action, list) and '*' in action):
                        if (isinstance(resource, str) and resource == '*') or (isinstance(resource, list) and '*' in resource):
                            excessive_policies.append(policy.get('name', 'unknown'))
                            break
        
        if excessive_policies:
            logger.info(f"{log_prefix}Found {len(excessive_policies)} policies with excessive permissions")
            return {
                'service': 'IAM',
                'resource': 'Policies',
                'severity': '높음',
                'message': "과도한 IAM 권한 검토가 필요합니다.",
                'problem': f"{len(excessive_policies)}개의 정책에 과도한 권한이 부여되어 있습니다.",
                'impact': "최소 권한 원칙 위반으로 보안 위험이 증가하고 있습니다.",
                'benefit': "최소 권한 원칙 적용으로 보안 강화 및 잠재적 위험 감소가 가능합니다.",
                'steps': [
                    "관리형 정책 대신 사용자 지정 정책을 사용합니다.",
                    "와일드카드(*) 사용을 최소화합니다.",
                    "IAM Access Analyzer를 활용하여 정책을 검토합니다.",
                    "정기적인 권한 감사를 수행합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_excessive_permissions: {str(e)}")
        return None