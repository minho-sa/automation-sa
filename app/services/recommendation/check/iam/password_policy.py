import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_password_policy(iam_data, collection_id=None):
    """비밀번호 정책 검사
    
    Args:
        iam_data: IAM 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking password policy")
        
        password_policy = iam_data.get('password_policy', {})
        
        if not password_policy.get('exists', True):
            logger.info(f"{log_prefix}No password policy configured")
            return {
                'service': 'IAM',
                'resource': 'Password Policy',
                'severity': '중간',
                'message': "계정 비밀번호 정책 강화가 필요합니다.",
                'problem': "계정에 비밀번호 정책이 설정되어 있지 않습니다.",
                'impact': "약한 비밀번호로 인한 계정 침해 위험이 증가하고 있습니다.",
                'benefit': "강력한 비밀번호 정책으로 무단 액세스 위험 감소가 가능합니다.",
                'steps': [
                    "최소 14자 이상의 비밀번호 길이를 설정합니다.",
                    "대문자, 소문자, 숫자, 특수 문자를 요구합니다.",
                    "90일 이하의 비밀번호 만료 기간을 설정합니다.",
                    "비밀번호 재사용을 제한합니다."
                ]
            }
        elif (
            not password_policy.get('RequireUppercaseCharacters', False) or
            not password_policy.get('RequireLowercaseCharacters', False) or
            not password_policy.get('RequireSymbols', False) or
            not password_policy.get('RequireNumbers', False) or
            password_policy.get('MinimumPasswordLength', 0) < 14 or
            not password_policy.get('PasswordReusePrevention', 0) or
            not password_policy.get('MaxPasswordAge', 0) or
            password_policy.get('MaxPasswordAge', 0) > 90
        ):
            logger.info(f"{log_prefix}Weak password policy configured")
            return {
                'service': 'IAM',
                'resource': 'Password Policy',
                'severity': '중간',
                'message': "계정 비밀번호 정책 강화가 필요합니다.",
                'problem': "현재 비밀번호 정책이 AWS 권장 설정보다 약합니다.",
                'impact': "약한 비밀번호로 인한 계정 침해 위험이 증가하고 있습니다.",
                'benefit': "강력한 비밀번호 정책으로 무단 액세스 위험 감소가 가능합니다.",
                'steps': [
                    "최소 14자 이상의 비밀번호 길이를 설정합니다.",
                    "대문자, 소문자, 숫자, 특수 문자를 요구합니다.",
                    "90일 이하의 비밀번호 만료 기간을 설정합니다.",
                    "비밀번호 재사용을 제한합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_password_policy: {str(e)}")
        return None