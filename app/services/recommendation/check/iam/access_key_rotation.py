import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_access_key_rotation(iam_data, collection_id=None):
    """액세스 키 교체 검사
    
    Args:
        iam_data: IAM 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking access key rotation")
        
        users = iam_data.get('users', [])
        old_access_keys = []
        
        for user in users:
            for key in user.get('access_keys', []):
                if key.get('status') == 'Active' and key.get('days_since_created') and key.get('days_since_created') > 90:
                    old_access_keys.append(f"{user.get('name')}의 액세스 키 {key.get('id')}")
        
        if old_access_keys:
            logger.info(f"{log_prefix}Found {len(old_access_keys)} access keys not rotated in 90 days")
            return {
                'service': 'IAM',
                'resource': 'Access Keys',
                'severity': '중간',
                'message': "액세스 키 교체가 필요합니다.",
                'problem': f"{len(old_access_keys)}개의 액세스 키가 90일 동안 교체되지 않았습니다.",
                'impact': "장기간 사용된 자격 증명으로 인한 보안 위험이 증가하고 있습니다.",
                'benefit': "정기적인 자격 증명 교체로 보안 강화가 가능합니다.",
                'steps': [
                    "90일마다 액세스 키를 교체합니다.",
                    "액세스 키 교체 일정을 수립합니다.",
                    "자동화된 키 교체 메커니즘을 구현합니다.",
                    "키 교체 상태를 모니터링합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_access_key_rotation: {str(e)}")
        return None