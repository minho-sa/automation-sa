import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_lifecycle_rules(bucket, collection_id=None):
    """라이프사이클 규칙 검사
    
    Args:
        bucket: S3 버킷 정보
        collection_id: 수집 ID (로깅용)
    """
    try:
        bucket_name = bucket.get('name', 'unknown')
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking lifecycle rules for bucket {bucket_name}")
        
        if not bucket.get('lifecycle_rules'):
            logger.info(f"{log_prefix}Bucket {bucket_name} has no lifecycle rules")
            return {
                'service': 'S3',
                'resource': bucket_name,
                'message': "S3 버킷의 라이프사이클 규칙 설정을 검토하세요.",
                'severity': '낮음',
                'problem': "S3 버킷에 라이프사이클 규칙이 설정되어 있지 않습니다.",
                'impact': "불필요한 스토리지 비용이 발생할 수 있습니다.",
                'benefit': "라이프사이클 규칙을 설정하여 비용을 최적화할 수 있습니다.",
                'steps': [
                    "AWS 콘솔에서 S3 서비스로 이동합니다.",
                    f"버킷 {bucket_name}을 선택합니다.",
                    "'관리' 탭으로 이동합니다.",
                    "'라이프사이클 규칙'을 생성합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_lifecycle_rules for bucket {bucket.get('name', 'unknown')}: {str(e)}")
        return None