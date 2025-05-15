import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_tag_management(bucket, collection_id=None):
    """태그 관리 검사
    
    Args:
        bucket: S3 버킷 정보
        collection_id: 수집 ID (로깅용)
    """
    try:
        bucket_name = bucket.get('name', 'unknown')
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking tag management for bucket {bucket_name}")
        
        if not bucket.get('tags'):
            logger.info(f"{log_prefix}Bucket {bucket_name} has no tags")
            return {
                'service': 'S3',
                'resource': bucket_name,
                'message': "S3 버킷의 태그 관리를 검토하세요.",
                'severity': '낮음',
                'problem': "S3 버킷에 태그가 설정되어 있지 않습니다.",
                'impact': "리소스 관리 및 비용 할당이 어려울 수 있습니다.",
                'benefit': "태그를 설정하여 리소스 관리 및 비용 추적을 개선할 수 있습니다.",
                'steps': [
                    "AWS 콘솔에서 S3 서비스로 이동합니다.",
                    f"버킷 {bucket_name}을 선택합니다.",
                    "'속성' 탭으로 이동합니다.",
                    "'태그' 섹션에서 태그를 추가합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_tag_management for bucket {bucket.get('name', 'unknown')}: {str(e)}")
        return None