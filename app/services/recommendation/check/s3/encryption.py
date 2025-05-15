import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_encryption(bucket, collection_id=None):
    """암호화 검사
    
    Args:
        bucket: S3 버킷 정보
        collection_id: 수집 ID (로깅용)
    """
    try:
        bucket_name = bucket.get('name', 'unknown')
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking encryption for bucket {bucket_name}")
        
        if not bucket.get('encryption'):
            logger.info(f"{log_prefix}Bucket {bucket_name} has encryption disabled")
            return {
                'service': 'S3',
                'resource': bucket_name,
                'message': "S3 버킷의 기본 암호화 설정을 검토하세요.",
                'severity': '중간',
                'problem': "S3 버킷에 기본 암호화가 설정되어 있지 않습니다.",
                'impact': "저장 데이터의 보안이 취약할 수 있습니다.",
                'benefit': "기본 암호화를 활성화하여 데이터 보안을 강화할 수 있습니다.",
                'steps': [
                    "AWS 콘솔에서 S3 서비스로 이동합니다.",
                    f"버킷 {bucket_name}을 선택합니다.",
                    "'속성' 탭으로 이동합니다.",
                    "'기본 암호화' 설정을 활성화합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_encryption for bucket {bucket.get('name', 'unknown')}: {str(e)}")
        return None