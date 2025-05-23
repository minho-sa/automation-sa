import logging
from typing import Dict, List, Any
from app.services.resource.ec2 import get_ec2_data
from app.services.recommendation.check.ec2 import (
    check_backup_recommendations,
    check_cpu_utilization,
    check_ebs_optimization,
    check_network_performance,
    check_old_generation_instance,
    check_reserved_instance_recommendation,
    check_security_group_recommendations,
    check_stopped_instance,
    check_tag_recommendations
)

# 로깅 설정
logger = logging.getLogger(__name__)

def get_ec2_recommendations(instances: List[Dict], collection_id: str = None) -> List[Dict]:
    """EC2 인스턴스에 대한 권장사항 수집"""
    # 예외 처리 전에 log_prefix 정의 (전역 변수로 선언)
    global log_prefix
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.info(f"{log_prefix}Starting EC2 recommendations collection")
    
    try:
        logger.info(f"{log_prefix}Analyzing {len(instances)} instances for recommendations")
        
        # 권장사항 수집
        recommendations = []
        
        for instance in instances:
            instance_id = instance.get('id', 'unknown')
            logger.debug(f"{log_prefix}Checking recommendations for instance {instance_id}")
            
            # 각 체크 함수 실행
            checks = [
                check_backup_recommendations(instance, collection_id),
                check_cpu_utilization(instance, collection_id),
                check_ebs_optimization(instance, collection_id),
                check_network_performance(instance, collection_id),
                check_old_generation_instance(instance, collection_id),
                check_reserved_instance_recommendation(instance, collection_id),
                check_security_group_recommendations(instance, collection_id),
                check_stopped_instance(instance, collection_id),
                check_tag_recommendations(instance, collection_id)
            ]
            
            # 결과 필터링 (None 제외)
            instance_recommendations = [check for check in checks if check]
            
            if instance_recommendations:
                logger.info(f"{log_prefix}Found {len(instance_recommendations)} recommendations for instance {instance_id}")
                recommendations.extend(instance_recommendations)
        
        logger.info(f"{log_prefix}Successfully collected {len(recommendations)} recommendations")
        return recommendations
        
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_ec2_recommendations: {str(e)}")
        return []