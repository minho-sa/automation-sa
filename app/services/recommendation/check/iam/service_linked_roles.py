import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_service_linked_roles(data, collection_id=None):
    """서비스 연결 역할 사용 검사
    
    Args:
        data: 역할 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking service linked roles")
        
        role = data.get('role')
        if not role:
            return None
            
        role_name = role.get('name', 'unknown')
        
        if role_name.startswith('AWS') and not role.get('service_linked'):
            logger.info(f"{log_prefix}Role {role_name} is not using service-linked role")
            return {
                'service': 'IAM',
                'resource': role_name,
                'severity': '낮음',
                'message': f"역할 {role_name}의 서비스 연결 역할 사용 검토가 필요합니다.",
                'problem': "AWS 서비스 역할이 서비스 연결 역할을 사용하지 않고 있습니다.",
                'impact': "수동 권한 관리로 인한 관리 부담 및 오류 가능성이 증가하고 있습니다.",
                'benefit': "서비스 연결 역할 사용으로 권한 관리 간소화 및 오류 감소가 가능합니다.",
                'steps': [
                    "지원되는 서비스에 서비스 연결 역할을 활성화합니다.",
                    "기존 수동 관리 역할을 서비스 연결 역할로 마이그레이션합니다.",
                    "서비스 연결 역할 사용 현황을 모니터링합니다.",
                    "AWS 서비스 권한 관리 방식을 정기적으로 검토합니다."
                ]
            }
        return None
    except Exception as e:
        logger.error(f"{log_prefix}Error in check_service_linked_roles: {str(e)}")
        return None