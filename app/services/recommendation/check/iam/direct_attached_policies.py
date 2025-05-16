import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_direct_attached_policies(data, collection_id=None):
    """IAM 사용자 직접 정책 연결 검사
    
    Args:
        data: 사용자 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking direct attached policies")
        
        user = data.get('user')
        if not user:
            return None
            
        user_name = user.get('name', 'unknown')
        
        if user.get('policies'):
            logger.info(f"{log_prefix}User {user_name} has directly attached policies")
            return {
                'service': 'IAM',
                'resource': user_name,
                'severity': '중간',
                'message': f"사용자 {user_name}의 권한 관리 개선이 필요합니다.",
                'problem': "사용자에게 직접 정책이 연결되어 있습니다.",
                'impact': "권한 관리의 복잡성이 증가하고 일관성이 저하되고 있습니다.",
                'benefit': "그룹 기반 권한 관리로 효율성 향상 및 관리 부담 감소가 가능합니다.",
                'steps': [
                    "IAM 그룹을 생성하고 사용자를 그룹에 할당합니다.",
                    "정책을 그룹에 연결합니다.",
                    "사용자에게 직접 연결된 정책을 제거합니다.",
                    "정기적인 권한 구조를 검토합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_direct_attached_policies: {str(e)}")
        return None