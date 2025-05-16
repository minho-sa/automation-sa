import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_mfa_enabled(data, collection_id=None):
    """MFA 미설정 사용자 검사
    
    Args:
        data: 사용자 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking MFA enabled status")
        
        user = data.get('user')
        if not user:
            return None
            
        user_name = user.get('name', 'unknown')
        
        if user.get('password_enabled') and not user.get('mfa_enabled'):
            logger.info(f"{log_prefix}User {user_name} has no MFA enabled")
            return {
                'service': 'IAM',
                'resource': user_name,
                'severity': '높음',
                'message': f"사용자 {user_name}에 대해 MFA 활성화가 필요합니다.",
                'problem': "콘솔 액세스가 가능한 IAM 사용자 계정에 MFA가 설정되어 있지 않습니다.",
                'impact': "MFA가 없는 계정은 비인가 접근에 취약할 수 있습니다.",
                'benefit': "MFA를 사용하면 계정 보안이 크게 강화됩니다.",
                'steps': [
                    "AWS 콘솔에서 IAM 서비스로 이동합니다.",
                    f"사용자 {user_name}를 선택합니다.",
                    "보안 자격 증명 탭으로 이동합니다.",
                    "MFA 디바이스를 할당합니다.",
                    "가상 MFA 또는 하드웨어 MFA를 설정합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_mfa_enabled: {str(e)}")
        return None