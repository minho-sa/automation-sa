import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_excessive_permissions(data, collection_id=None):
    """IAM 정책 권한 검사
    
    Args:
        data: 정책 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking excessive permissions")
        
        policy = data.get('policy')
        if not policy:
            return None
            
        policy_name = policy.get('name', 'unknown')
        document = policy.get('document', {})
        statements = document.get('Statement', [])
        
        for statement in statements:
            if statement.get('Effect') == 'Allow':
                action = statement.get('Action', [])
                resource = statement.get('Resource', [])
                
                # 와일드카드 권한 확인
                if (isinstance(action, str) and action == '*') or (isinstance(action, list) and '*' in action):
                    if (isinstance(resource, str) and resource == '*') or (isinstance(resource, list) and '*' in resource):
                        logger.info(f"{log_prefix}Policy {policy_name} has excessive permissions")
                        return {
                            'service': 'IAM',
                            'resource': policy_name,
                            'severity': '높음',
                            'message': f"정책 {policy_name}의 과도한 권한 검토가 필요합니다.",
                            'problem': "정책에 과도한 권한(Action: *, Resource: *)이 부여되어 있습니다.",
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