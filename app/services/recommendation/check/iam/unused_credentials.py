import logging
from datetime import datetime, timezone

# 로깅 설정
logger = logging.getLogger(__name__)

def check_unused_credentials(data, collection_id=None):
    """미사용 IAM 자격 증명 검사
    
    Args:
        data: 사용자 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking unused credentials")
        
        user = data.get('user')
        if not user:
            return None
            
        user_name = user.get('name', 'unknown')
        current_time = datetime.now(timezone.utc)
        unused_credentials = []
        
        # 액세스 키 확인
        for key in user.get('access_keys', []):
            if key.get('status') == 'Active' and key.get('days_since_used') and key.get('days_since_used') > 90:
                unused_credentials.append(f"액세스 키 {key.get('id')}")
        
        # 로그인 프로필 확인
        if user.get('password_enabled') and user.get('last_activity'):
            last_activity = datetime.strptime(user.get('last_activity'), '%Y-%m-%d') if isinstance(user.get('last_activity'), str) else user.get('last_activity')
            if last_activity and (current_time - last_activity).days > 90:
                unused_credentials.append("로그인 프로필")
        
        if unused_credentials:
            logger.info(f"{log_prefix}User {user_name} has unused credentials: {', '.join(unused_credentials)}")
            return {
                'service': 'IAM',
                'resource': user_name,
                'severity': '중간',
                'message': f"사용자 {user_name}의 미사용 자격 증명 정리가 필요합니다.",
                'problem': f"다음 자격 증명이 90일 동안 사용되지 않았습니다: {', '.join(unused_credentials)}",
                'impact': "불필요한 액세스 포인트로 인한 보안 위험이 증가하고 있습니다.",
                'benefit': "미사용 자격 증명 제거로 보안 태세 강화 및 관리 부담 감소가 가능합니다.",
                'steps': [
                    "90일 이상 사용되지 않은 액세스 키를 비활성화합니다.",
                    "180일 이상 사용되지 않은 액세스 키를 삭제합니다.",
                    "미사용 IAM 사용자 계정을 비활성화합니다.",
                    "정기적인 자격 증명 감사를 수행합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_unused_credentials: {str(e)}")
        return None