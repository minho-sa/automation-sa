import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_public_access(bucket, collection_id=None):
    """퍼블릭 액세스 검사
    
    Args:
        bucket: S3 버킷 정보
        collection_id: 수집 ID (로깅용)
    """
    try:
        bucket_name = bucket.get('name', 'unknown')
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking public access for bucket {bucket_name}")
        
        if bucket.get('public_access'):
            logger.info(f"{log_prefix}Bucket {bucket_name} has public access enabled")
            return {
                'service': 'S3',
                'resource': bucket_name,
                'message': "S3 버킷의 퍼블릭 액세스 설정을 검토하세요.",
                'severity': '높음',
                'problem': "S3 버킷이 퍼블릭 액세스 가능 상태입니다.",
                'impact': "데이터 유출 및 보안 위험이 있습니다.",
                'benefit': "퍼블릭 액세스를 차단하여 데이터 보안을 강화할 수 있습니다.",
                'steps': [
                    "AWS 콘솔에서 S3 서비스로 이동합니다.",
                    f"버킷 {bucket_name}을 선택합니다.",
                    "'권한' 탭으로 이동합니다.",
                    "'퍼블릭 액세스 차단' 설정을 활성화합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_public_access for bucket {bucket.get('name', 'unknown')}: {str(e)}")
        return None