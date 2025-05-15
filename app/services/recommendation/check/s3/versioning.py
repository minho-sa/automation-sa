import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_versioning(bucket, collection_id=None):
    """버저닝 검사
    
    Args:
        bucket: S3 버킷 정보
        collection_id: 수집 ID (로깅용)
    """
    try:
        bucket_name = bucket.get('name', 'unknown')
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking versioning for bucket {bucket_name}")
        
        if not bucket.get('versioning'):
            logger.info(f"{log_prefix}Bucket {bucket_name} has versioning disabled")
            return {
                'service': 'S3',
                'resource': bucket_name,
                'message': "S3 버킷의 버저닝 활성화를 검토하세요.",
                'severity': '중간',
                'problem': "S3 버킷에 버저닝이 활성화되어 있지 않습니다.",
                'impact': "실수로 인한 데이터 손실 위험이 있습니다.",
                'benefit': "버저닝을 활성화하여 데이터 보호 및 복구 기능을 강화할 수 있습니다.",
                'steps': [
                    "AWS 콘솔에서 S3 서비스로 이동합니다.",
                    f"버킷 {bucket_name}을 선택합니다.",
                    "'속성' 탭으로 이동합니다.",
                    "'버전 관리' 설정을 활성화합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_versioning for bucket {bucket.get('name', 'unknown')}: {str(e)}")
        return None