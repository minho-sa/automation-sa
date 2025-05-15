# app/services/ec2_checks/ebs_optimization.py
# Check for EBS volume optimization recommendations

import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_ebs_optimization(instance, collection_id=None):
    """EBS 볼륨 최적화 검사
    
    Args:
        instance: EC2 인스턴스 정보
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking EBS optimization for instance {instance.get('id')}")
        issues = []
        for volume in instance.get('volumes', []):
            logger.debug(f"{log_prefix}Analyzing volume {volume.get('VolumeId')} for instance {instance.get('id')}")
            
            # 미사용 볼륨 검사
            if not volume.get('Attachments'):
                msg = f"미사용 EBS 볼륨 발견: {volume['VolumeId']}"
                issues.append(msg)
            
            # IOPS 과다 설정 검사
            if volume.get('Iops') and volume.get('VolumeType') in ['io1', 'io2']:
                if volume['Iops'] > 10000:
                    msg = f"과다 설정된 IOPS 발견: {volume['VolumeId']}"
                    issues.append(msg)
            
            # gp2에서 gp3로 마이그레이션 추천
            if volume.get('VolumeType') == 'gp2':
                msg = f"gp3로 마이그레이션 권장: {volume['VolumeId']}"
                logger.info(f"{log_prefix}{msg}")
                issues.append(msg)

        if issues:
            logger.info(f"{log_prefix}Found {len(issues)} EBS issues for instance {instance['id']}")
            return {
                'service': 'EC2',
                'resource': instance['id'],
                'message': "EBS 볼륨 최적화가 필요합니다.",
                'severity': '중간',
                'steps': [
                    "미사용 볼륨 식별 및 제거",
                    "볼륨 크기 및 IOPS 최적화",
                    "gp2에서 gp3로 마이그레이션 검토",
                    "주기적인 스냅샷 정책 검토"
                ],
                'problem': "\n".join(issues),
                'impact': "불필요한 스토리지 비용 발생",
                'benefit': "스토리지 비용 최적화 및 성능 개선"
            }
        logger.debug(f"{log_prefix}No EBS optimization issues found for instance {instance['id']}")
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_ebs_optimization for instance {instance.get('id')}: {str(e)}", exc_info=True)
        return None