import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def check_service_linked_roles(iam_data, collection_id=None):
    """서비스 연결 역할 사용 검사
    
    Args:
        iam_data: IAM 데이터
        collection_id: 수집 ID (로깅용)
    """
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        logger.debug(f"{log_prefix}Checking service linked roles")
        
        roles = iam_data.get('roles', [])
        non_service_linked_roles = []
        
        for role in roles:
            if not role.get('service_linked') and role.get('name', '').startswith('AWS'):
                non_service_linked_roles.append(role.get('name', 'unknown'))
        
        if non_service_linked_roles:
            logger.info(f"{log_prefix}Found {len(non_service_linked_roles)} AWS service roles not using service-linked roles")
            return {
                'service': 'IAM',
                'resource': 'Roles',
                'severity': '낮음',
                'message': "서비스 연결 역할 사용 검토가 필요합니다.",
                'problem': f"{len(non_service_linked_roles)}개의 서비스가 서비스 연결 역할을 사용하지 않고 있습니다.",
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