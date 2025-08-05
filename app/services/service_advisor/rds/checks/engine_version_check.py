import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_FAIL
)
from app.services.service_advisor.rds.checks.base_rds_check import BaseRDSCheck

class EngineVersionCheck(BaseRDSCheck):
    """RDS 엔진 버전 및 업그레이드 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'rds_engine_version_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        rds_client = create_boto3_client('rds', role_arn=role_arn)
        
        # RDS 인스턴스 조회
        db_instances = rds_client.describe_db_instances()
        
        # 각 엔진별 사용 가능한 버전 조회
        engine_versions = {}
        for instance in db_instances['DBInstances']:
            engine = instance['Engine']
            if engine not in engine_versions:
                try:
                    versions = rds_client.describe_db_engine_versions(Engine=engine)
                    engine_versions[engine] = versions['DBEngineVersions']
                except Exception:
                    engine_versions[engine] = []
        
        return {
            'db_instances': db_instances['DBInstances'],
            'engine_versions': engine_versions
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        # 구버전으로 간주할 기준 (월 단위)
        old_version_threshold = 12  # 12개월 이상 된 버전
        
        for instance in collected_data['db_instances']:
            db_identifier = instance['DBInstanceIdentifier']
            engine = instance['Engine']
            current_version = instance['EngineVersion']
            auto_minor_upgrade = instance.get('AutoMinorVersionUpgrade', False)
            
            # 사용 가능한 엔진 버전들
            available_versions = collected_data['engine_versions'].get(engine, [])
            
            # 현재 버전 정보 찾기
            current_version_info = None
            latest_version_info = None
            
            for version in available_versions:
                if version['Version'] == current_version:
                    current_version_info = version
                
                # 최신 버전 찾기 (가장 높은 버전)
                if latest_version_info is None or self._compare_versions(version['Version'], latest_version_info['Version']) > 0:
                    latest_version_info = version
            
            # 상태 결정
            status = RESOURCE_STATUS_PASS
            status_text = '최신 버전'
            advice = f'현재 엔진 버전({current_version})이 최신 상태입니다.'
            
            # 버전 비교 및 분석
            if latest_version_info and current_version != latest_version_info['Version']:
                version_gap = self._calculate_version_gap(current_version, latest_version_info['Version'])
                
                if version_gap >= 2:  # 메이저 버전이 2개 이상 차이
                    status = RESOURCE_STATUS_FAIL
                    status_text = '업그레이드 필요'
                    advice = f'현재 버전({current_version})이 최신 버전({latest_version_info["Version"]})보다 {version_gap}개 버전 뒤처져 있습니다. 보안 및 성능 향상을 위해 업그레이드를 권장합니다.'
                    problem_count += 1
                elif version_gap >= 1:  # 메이저 버전이 1개 차이
                    status = RESOURCE_STATUS_WARNING
                    status_text = '업그레이드 권장'
                    advice = f'현재 버전({current_version})보다 새로운 버전({latest_version_info["Version"]})이 사용 가능합니다. 업그레이드를 고려하세요.'
                    problem_count += 1
            
            # 자동 마이너 버전 업그레이드 확인
            if not auto_minor_upgrade and status == RESOURCE_STATUS_PASS:
                status = RESOURCE_STATUS_WARNING
                status_text = '자동 업그레이드 비활성화'
                advice = f'자동 마이너 버전 업그레이드가 비활성화되어 있습니다. 보안 패치를 자동으로 받기 위해 활성화를 고려하세요.'
                problem_count += 1
            
            # 지원 종료 예정 버전 확인
            if current_version_info and 'SupportedFeatureNames' in current_version_info:
                if 'deprecated' in str(current_version_info).lower():
                    status = RESOURCE_STATUS_FAIL
                    status_text = '지원 종료 예정'
                    advice = f'현재 버전({current_version})이 지원 종료 예정입니다. 즉시 업그레이드하세요.'
                    problem_count += 1
            
            resources.append(create_resource_result(
                resource_id=db_identifier,
                status=status,
                advice=advice,
                status_text=status_text,
                db_identifier=db_identifier,
                engine=engine,
                current_version=current_version,
                latest_version=latest_version_info['Version'] if latest_version_info else 'N/A',
                auto_minor_upgrade=auto_minor_upgrade
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """버전 비교 (1: version1이 더 높음, -1: version2가 더 높음, 0: 같음)"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # 길이를 맞춤
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            return 0
        except:
            return 0
    
    def _calculate_version_gap(self, current: str, latest: str) -> int:
        """버전 간격 계산 (메이저 버전 기준)"""
        try:
            current_major = int(current.split('.')[0])
            latest_major = int(latest.split('.')[0])
            return latest_major - current_major
        except:
            return 0
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '정기적으로 RDS 엔진 버전을 최신 상태로 유지하세요.',
            '자동 마이너 버전 업그레이드를 활성화하여 보안 패치를 자동으로 받으세요.',
            '메이저 버전 업그레이드 전에는 테스트 환경에서 충분히 검증하세요.',
            '지원 종료 예정 버전은 즉시 업그레이드하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 RDS 인스턴스 중 {problems}개가 엔진 버전 업그레이드가 필요합니다.'
        else:
            return f'모든 RDS 인스턴스({total}개)가 적절한 엔진 버전을 사용하고 있습니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """
    RDS 엔진 버전 검사를 실행합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    check = EngineVersionCheck()
    return check.run(role_arn=role_arn)