import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_mfa_enabled(iam_data, collection_id=None):
    """MFA 미설정 사용자 검사
    
    Args:
        iam_data: IAM 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking MFA enabled status for users")
        
        users = iam_data.get('users', [])
        mfa_users = []
        
        for user in users:
            if user.get('password_enabled') and not user.get('mfa_enabled'):
                mfa_users.append(user.get('name', 'unknown'))
        
        if mfa_users:
            logger.info(f"{log_prefix}Found {len(mfa_users)} users without MFA")
            return {
                'service': 'IAM',
                'resource': 'Users',
                'severity': '높음',
                'message': "MFA 미설정 사용자가 존재합니다.",
                'problem': f"{len(mfa_users)}명의 사용자가 MFA를 설정하지 않았습니다.",
                'impact': "자격 증명 도용 위험이 증가하고 계정 보안이 취약한 상태입니다.",
                'benefit': "MFA 설정으로 무단 액세스 위험을 95% 이상 감소시킬 수 있습니다.",
                'steps': [
                    "모든 IAM 사용자에게 MFA 설정을 의무화합니다.",
                    "MFA 미설정 사용자에 대한 액세스 제한 정책을 적용합니다.",
                    "정기적인 MFA 설정 상태를 모니터링합니다.",
                    "MFA 설정 가이드를 사용자에게 제공합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_mfa_enabled: {str(e)}")
        return None