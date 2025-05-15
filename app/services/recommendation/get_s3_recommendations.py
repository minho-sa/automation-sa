import logging
from typing import Dict, List, Any
from app.services.resource.s3 import get_s3_data
from app.services.recommendation.check.s3 import (
    check_public_access,
    check_versioning,
    check_encryption,
    check_lifecycle_rules,
    check_tag_management
)

# 로깅 설정
logger = logging.getLogger(__name__)

def get_s3_recommendations(buckets: List[Dict], collection_id: str = None) -> List[Dict]:
    """S3 버킷에 대한 권장사항 수집"""
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.info(f"{log_prefix}Starting S3 recommendations collection")
    
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.info(f"{log_prefix}Analyzing {len(buckets)} buckets for recommendations")
        
        # 권장사항 수집
        recommendations = []
        
        for bucket in buckets:
            bucket_name = bucket.get('name', 'unknown')
            logger.debug(f"{log_prefix}Checking recommendations for bucket {bucket_name}")
            
            # 각 체크 함수 실행
            checks = [
                check_public_access(bucket, collection_id),
                check_versioning(bucket, collection_id),
                check_encryption(bucket, collection_id),
                check_lifecycle_rules(bucket, collection_id),
                check_tag_management(bucket, collection_id)
            ]
            
            # 결과 필터링 (None 제외)
            bucket_recommendations = [check for check in checks if check]
            
            if bucket_recommendations:
                logger.info(f"{log_prefix}Found {len(bucket_recommendations)} recommendations for bucket {bucket_name}")
                recommendations.extend(bucket_recommendations)
        
        logger.info(f"{log_prefix}Successfully collected {len(recommendations)} recommendations")
        return recommendations
        
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_s3_recommendations: {str(e)}")
        return []