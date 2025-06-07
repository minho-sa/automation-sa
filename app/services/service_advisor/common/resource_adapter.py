"""
리소스 어댑터 모듈
UI 호환성을 위한 리소스 데이터 변환 기능을 제공합니다.
"""
from typing import Dict, List, Any

def adapt_resources_for_ui(resources: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    리소스 목록을 UI에 맞게 변환합니다.
    
    Args:
        resources: 리소스 목록
        
    Returns:
        UI에 맞게 변환된 리소스 데이터
    """
    result = {}
    
    # 리소스 유형별로 분류
    instances = []
    security_groups = []
    
    for resource in resources:
        resource_type = resource.get('resource_type')
        
        if resource_type == 'instance':
            # 인스턴스 데이터 변환
            instance_data = {
                'id': resource['id'],
                'instance_name': resource['name'],
                'status': resource['status'],
                'status_text': resource['status_text'],
                'advice': resource['advice'],
                'instance_type': resource['details'].get('instance_type', 'N/A'),
                'avg_cpu': resource['details'].get('avg_cpu', 'N/A'),
                'max_cpu': resource['details'].get('max_cpu', 'N/A')
            }
            instances.append(instance_data)
            
        elif resource_type == 'security_group':
            # 보안 그룹 데이터 변환
            sg_data = {
                'id': resource['id'],
                'sg_name': resource['name'],
                'status': resource['status'],
                'status_text': resource['status_text'],
                'advice': resource['advice'],
                'vpc_id': resource['details'].get('vpc_id', 'N/A'),
                'description': resource['details'].get('description', ''),
                'risky_rules': resource['details'].get('risky_rules', []),
                'risky_rules_count': resource['details'].get('risky_rules_count', 0)
            }
            security_groups.append(sg_data)
    
    # 결과 구성
    if instances:
        result['instances'] = instances
    
    if security_groups:
        result['security_groups'] = security_groups
    
    return result