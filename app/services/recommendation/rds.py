import boto3
from typing import Dict, List
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

def get_rds_recommendations(instances: List[Dict]) -> List[Dict]:
    """RDS 인스턴스 추천 사항 수집"""
    logger.info("Starting RDS recommendations analysis")
    recommendations = []
    
    try:
        # 인스턴스 데이터 형식 처리
        if isinstance(instances, dict) and 'instances' in instances:
            instance_list = instances['instances']
        elif isinstance(instances, dict):
            instance_list = [instances]
        elif isinstance(instances, list):
            instance_list = instances
        else:
            logger.error(f"Unexpected data type: {type(instances)}")
            return []
            
        logger.info(f"Analyzing {len(instance_list)} RDS instances for recommendations")
        
        for instance in instance_list:
            # 인스턴스 ID 가져오기 (DBInstanceIdentifier 대신 id 필드 사용)
            instance_id = instance.get('id', 'unknown')
            logger.debug(f"Checking recommendations for instance {instance_id}")
            
            # 1. Aurora 마이그레이션 권장
            if not instance_id.startswith('aurora-'):
                recommendations.append(create_aurora_recommendation(instance))
            
            # 2. 암호화 설정 검사
            if not instance.get('encrypted', False):
                recommendations.append(create_encryption_recommendation(instance))
            
            # 3. 다중 AZ 배포 검사
            if not instance.get('multi_az', False):
                recommendations.append(create_multi_az_recommendation(instance))
            
            # 4. 백업 보존 기간 검사
            if instance.get('backup_retention_period', 0) < 7:
                recommendations.append(create_backup_retention_recommendation(instance))
            
            # 5. Performance Insights 활성화 검사
            if not instance.get('performance_insights_enabled', False):
                recommendations.append(create_performance_insights_recommendation(instance))
            
            # 6. 자동 마이너 버전 업그레이드 검사
            if not instance.get('auto_minor_version_upgrade', False):
                recommendations.append(create_auto_upgrade_recommendation(instance))
            
            # 7. 퍼블릭 액세스 검사
            if instance.get('publicly_accessible', False):
                recommendations.append(create_public_access_recommendation(instance))
            
            # 8. 태그 관리 검사
            if not instance.get('tags'):
                recommendations.append(create_tag_recommendation(instance))
        
        logger.info(f"Successfully collected {len(recommendations)} recommendations")
        return recommendations
        
    except Exception as e:
        logger.error(f"Error in get_rds_recommendations: {str(e)}")
        return []

def create_aurora_recommendation(instance: Dict) -> Dict:
    """Aurora 마이그레이션 권장 추천 사항 생성"""
    instance_id = instance.get('id', 'unknown')
    engine = instance.get('engine', 'unknown')
    
    return {
        'service': 'RDS',
        'resource': instance_id,
        'severity': '중간',
        'message': "RDS 인스턴스는 Aurora로 마이그레이션하여 성능과 비용 효율성을 개선할 수 있습니다.",
        'problem': f"{engine} 엔진을 사용하는 RDS 인스턴스는 Aurora로 마이그레이션하여 성능과 확장성을 개선할 수 있습니다.",
        'impact': "Aurora가 아닌 일반 RDS 엔진 사용으로 인한 성능 및 확장성 제한이 있습니다.",
        'steps': [
            "AWS 콘솔에서 RDS 서비스로 이동합니다.",
            f"인스턴스 {instance_id}의 스냅샷을 생성합니다.",
            "스냅샷에서 Aurora 데이터베이스로 복원합니다.",
            "애플리케이션 연결 문자열을 업데이트합니다.",
            "마이그레이션 완료 후 원본 RDS 인스턴스를 삭제합니다."
        ],
        'benefit': "Aurora 사용 시 성능 향상, 자동 확장, 고가용성 및 비용 효율성 개선이 가능합니다."
    }

def create_encryption_recommendation(instance: Dict) -> Dict:
    """암호화 설정 추천 사항 생성"""
    instance_id = instance.get('id', 'unknown')
    
    return {
        'service': 'RDS',
        'resource': instance_id,
        'severity': '높음',
        'message': "RDS 인스턴스가 암호화되어 있지 않습니다. 데이터 보안을 위해 암호화를 활성화하세요.",
        'problem': f"인스턴스 {instance_id}가 저장 시 암호화되어 있지 않습니다.",
        'impact': "암호화되지 않은 데이터베이스는 데이터 유출의 위험이 있습니다.",
        'steps': [
            "암호화되지 않은 DB 인스턴스의 스냅샷을 생성합니다.",
            "스냅샷의 암호화된 사본을 생성합니다.",
            "암호화된 스냅샷에서 새 DB 인스턴스를 복원합니다.",
            "애플리케이션 연결을 새 DB 인스턴스로 전환합니다.",
            "기존 DB 인스턴스를 삭제합니다."
        ],
        'benefit': "저장 데이터 암호화를 통해 데이터 보안 및 규정 준수 요구사항을 충족할 수 있습니다."
    }

def create_multi_az_recommendation(instance: Dict) -> Dict:
    """다중 AZ 배포 추천 사항 생성"""
    instance_id = instance.get('id', 'unknown')
    
    return {
        'service': 'RDS',
        'resource': instance_id,
        'severity': '높음',
        'message': "RDS 인스턴스가 단일 AZ에서 실행 중입니다. 고가용성을 위해 다중 AZ 배포를 구성하세요.",
        'problem': f"인스턴스 {instance_id}가 단일 가용 영역에서 실행 중입니다.",
        'impact': "단일 AZ 배포는 AZ 장애 시 서비스 중단의 위험이 있습니다.",
        'steps': [
            "AWS 콘솔에서 RDS 서비스로 이동합니다.",
            f"인스턴스 {instance_id}를 선택합니다.",
            "'수정' 버튼을 클릭합니다.",
            "'다중 AZ 배포' 옵션을 활성화합니다.",
            "변경 사항을 적용합니다."
        ],
        'benefit': "다중 AZ 배포를 통해 고가용성 확보 및 계획된 유지 관리 중에도 서비스 중단을 최소화할 수 있습니다."
    }

def create_backup_retention_recommendation(instance: Dict) -> Dict:
    """백업 보존 기간 추천 사항 생성"""
    instance_id = instance.get('id', 'unknown')
    current_retention = instance.get('backup_retention_period', 0)
    
    return {
        'service': 'RDS',
        'resource': instance_id,
        'severity': '중간',
        'message': "백업 보존 기간이 7일 미만으로 설정되어 있습니다. 데이터 보호를 위해 보존 기간을 늘리세요.",
        'problem': f"인스턴스 {instance_id}의 백업 보존 기간이 {current_retention}일로 설정되어 있습니다.",
        'impact': "짧은 백업 보존 기간은 장기간의 데이터 복구 능력을 제한합니다.",
        'steps': [
            "AWS 콘솔에서 RDS 서비스로 이동합니다.",
            f"인스턴스 {instance_id}를 선택합니다.",
            "'수정' 버튼을 클릭합니다.",
            "'백업' 섹션에서 보존 기간을 7일 이상으로 설정합니다.",
            "변경 사항을 적용합니다."
        ],
        'benefit': "충분한 백업 보존 기간을 통해 데이터 손실 위험을 줄이고 장기간의 복구 지점을 확보할 수 있습니다."
    }

def create_performance_insights_recommendation(instance: Dict) -> Dict:
    """Performance Insights 활성화 추천 사항 생성"""
    instance_id = instance.get('id', 'unknown')
    
    return {
        'service': 'RDS',
        'resource': instance_id,
        'severity': '낮음',
        'message': "Performance Insights가 비활성화되어 있습니다. 데이터베이스 성능 모니터링을 위해 활성화하세요.",
        'problem': f"인스턴스 {instance_id}에 Performance Insights가 활성화되어 있지 않습니다.",
        'impact': "성능 문제 발생 시 원인 파악과 분석이 어려울 수 있습니다.",
        'steps': [
            "AWS 콘솔에서 RDS 서비스로 이동합니다.",
            f"인스턴스 {instance_id}를 선택합니다.",
            "'수정' 버튼을 클릭합니다.",
            "'Performance Insights' 섹션에서 기능을 활성화합니다.",
            "보존 기간 및 암호화 설정을 구성합니다.",
            "변경 사항을 적용합니다."
        ],
        'benefit': "Performance Insights를 통해 데이터베이스 성능 문제를 쉽게 식별하고 해결할 수 있습니다."
    }

def create_auto_upgrade_recommendation(instance: Dict) -> Dict:
    """자동 마이너 버전 업그레이드 추천 사항 생성"""
    instance_id = instance.get('id', 'unknown')
    
    return {
        'service': 'RDS',
        'resource': instance_id,
        'severity': '중간',
        'message': "자동 마이너 버전 업그레이드가 비활성화되어 있습니다. 보안 패치 적용을 위해 활성화하세요.",
        'problem': f"인스턴스 {instance_id}에 자동 마이너 버전 업그레이드가 비활성화되어 있습니다.",
        'impact': "보안 패치와 버그 수정이 자동으로 적용되지 않아 보안 위험이 있을 수 있습니다.",
        'steps': [
            "AWS 콘솔에서 RDS 서비스로 이동합니다.",
            f"인스턴스 {instance_id}를 선택합니다.",
            "'수정' 버튼을 클릭합니다.",
            "'마이너 버전 자동 업그레이드' 옵션을 활성화합니다.",
            "변경 사항을 적용합니다."
        ],
        'benefit': "자동 마이너 버전 업그레이드를 통해 최신 보안 패치와 버그 수정을 적용하여 데이터베이스 보안을 강화할 수 있습니다."
    }

def create_public_access_recommendation(instance: Dict) -> Dict:
    """퍼블릭 액세스 추천 사항 생성"""
    instance_id = instance.get('id', 'unknown')
    
    return {
        'service': 'RDS',
        'resource': instance_id,
        'severity': '높음',
        'message': "RDS 인스턴스가 퍼블릭하게 접근 가능하도록 설정되어 있습니다. 보안을 위해 접근을 제한하세요.",
        'problem': f"인스턴스 {instance_id}가 인터넷을 통해 공개적으로 접근 가능합니다.",
        'impact': "데이터베이스가 인터넷을 통해 접근 가능하여 보안 위험이 있습니다.",
        'steps': [
            "AWS 콘솔에서 RDS 서비스로 이동합니다.",
            f"인스턴스 {instance_id}를 선택합니다.",
            "'수정' 버튼을 클릭합니다.",
            "'퍼블릭 액세스' 옵션을 비활성화합니다.",
            "보안 그룹 설정을 검토하고 필요한 접근만 허용하도록 수정합니다.",
            "변경 사항을 적용합니다."
        ],
        'benefit': "퍼블릭 액세스 제한을 통해 데이터베이스 보안을 강화하고 무단 접근 위험을 줄일 수 있습니다."
    }

def create_tag_recommendation(instance: Dict) -> Dict:
    """태그 관리 추천 사항 생성"""
    instance_id = instance.get('id', 'unknown')
    
    return {
        'service': 'RDS',
        'resource': instance_id,
        'severity': '낮음',
        'message': "RDS 인스턴스에 태그가 설정되어 있지 않습니다. 리소스 관리를 위해 태그를 추가하세요.",
        'problem': f"인스턴스 {instance_id}에 태그가 설정되어 있지 않습니다.",
        'impact': "태그가 없으면 리소스 관리, 비용 할당 및 보안 감사가 어려울 수 있습니다.",
        'steps': [
            "AWS 콘솔에서 RDS 서비스로 이동합니다.",
            f"인스턴스 {instance_id}를 선택합니다.",
            "'태그' 탭을 선택합니다.",
            "'태그 관리' 버튼을 클릭합니다.",
            "필요한 태그를 추가합니다. (예: Environment, Owner, Cost Center 등)",
            "변경 사항을 저장합니다."
        ],
        'benefit': "적절한 태그 지정을 통해 리소스 관리, 비용 할당, 보안 감사 및 자동화를 개선할 수 있습니다."
    }