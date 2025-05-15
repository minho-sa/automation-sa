# app/services/recommendation/check/ec2/stopped_instance.py
# Check for long-stopped EC2 instances

import logging
from app.services.recommendation.check.ec2.utils import calculate_stop_duration

# 로깅 설정
logger = logging.getLogger(__name__)

def check_stopped_instance(instance, collection_id=None):
    """장기 중지된 인스턴스 검사
    
    Args:
        instance: EC2 인스턴스 정보
        collection_id: 수집 ID (로깅용)
    """
    instance_id = instance.get('id', 'unknown')
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.debug(f"{log_prefix}Checking stopped instance: {instance_id}")
    
    try:
        if instance.get('state') == 'stopped':
            stop_duration = calculate_stop_duration(instance.get('state_transition_time'))
            if stop_duration and stop_duration.days >= 7:
                logger.info(f"{log_prefix}Found long-stopped instance: {instance_id}")
                return {
                    'service': 'EC2',
                    'resource': instance_id,
                    'message': f"장기 중지된 인스턴스의 검토가 필요합니다.",
                    'severity': '중간',
                    'problem': f"EC2 인스턴스가 {stop_duration.days}일 동안 중지된 상태입니다.",
                    'impact': "스토리지 비용이 지속적으로 발생하고 있습니다.",
                    'benefit': "불필요한 인스턴스 정리를 통한 비용 절감이 가능합니다.",
                    'steps': [
                        "AWS 콘솔에서 EC2 서비스로 이동합니다.",
                        f"인스턴스 {instance_id}를 선택합니다.",
                        "필요하지 않은 경우 '인스턴스 종료' 작업을 수행합니다.",
                        "필요한 경우 AMI를 생성하여 나중에 복원할 수 있도록 합니다."
                    ]
                }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_stopped_instance for {instance_id}: {str(e)}")
        return None