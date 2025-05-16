import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_root_account_access_key(iam_data, collection_id=None):
    """루트 계정 액세스 키 검사
    
    Args:
        iam_data: IAM 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking root account access key")
        
        root_account = iam_data.get('root_account', {})
        if root_account and root_account.get('access_key_exists'):
            logger.info(f"{log_prefix}Root account has access keys")
            return {
                'service': 'IAM',
                'resource': 'Root Account',
                'severity': '높음',
                'message': "루트 계정 액세스 키 제거가 필요합니다.",
                'problem': "루트 계정에 액세스 키가 활성화되어 있습니다.",
                'impact': "루트 계정 자격 증명 노출 시 계정 전체에 대한 무제한 액세스 위험이 있습니다.",
                'benefit': "루트 계정 보안 강화 및 잠재적 보안 위협 감소가 가능합니다.",
                'steps': [
                    "루트 계정 액세스 키를 즉시 삭제합니다.",
                    "필요한 작업은 IAM 사용자 또는 역할을 통해 수행합니다.",
                    "루트 계정에는 MFA를 활성화합니다.",
                    "루트 계정은 긴급 상황에만 사용합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_root_account_access_key: {str(e)}")
        return None