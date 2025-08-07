import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    RDS 엔진 버전 및 업그레이드 검사를 실행합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # 모든 리전에서 RDS 인스턴스 수집
        ec2_client = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
        
        # 인스턴스 분석 결과
        instance_analysis = []
        
        for region in regions:
            try:
                rds_client = create_boto3_client('rds', region_name=region, role_arn=role_arn)
                instances = rds_client.describe_db_instances()
            except Exception:
                continue
                
            for instance in instances.get('DBInstances', []):
                db_identifier = instance.get('DBInstanceIdentifier', 'Unknown')
                engine = instance.get('Engine', 'Unknown')
                current_version = instance.get('EngineVersion', 'Unknown')
                auto_minor_upgrade = instance.get('AutoMinorVersionUpgrade', False)
                
                # 필수 정보가 없으면 건너뛰기
                if not all([db_identifier != 'Unknown', engine != 'Unknown', current_version != 'Unknown']):
                    continue
                
                # 사용 가능한 엔진 버전들 조회 (최신 버전만)
                try:
                    versions_response = rds_client.describe_db_engine_versions(
                        Engine=engine,
                        DefaultOnly=True  # 기본(최신) 버전만 가져오기
                    )
                    default_versions = versions_response.get('DBEngineVersions', [])
                    
                    # 모든 버전도 가져오기 (현재 버전 정보 확인용)
                    all_versions_response = rds_client.describe_db_engine_versions(Engine=engine)
                    all_versions = all_versions_response.get('DBEngineVersions', [])
                except Exception:
                    default_versions = []
                    all_versions = []
                
                # 현재 버전 정보 찾기
                current_version_info = None
                latest_version_info = None
                
                # 기본(최신) 버전 찾기
                if default_versions:
                    latest_version_info = default_versions[0]  # 첫 번째가 기본 버전
                
                # 현재 버전 정보 찾기
                for version in all_versions:
                    version_str = version.get('Version', '')
                    if version_str == current_version:
                        current_version_info = version
                        break
                
                # 상태 결정
                status = RESOURCE_STATUS_PASS
                status_text = '최신 버전'
                advice = f'현재 엔진 버전({current_version})이 최신 상태입니다.'
                
                # 버전 비교 및 분석
                latest_version = latest_version_info.get('Version', '') if latest_version_info else ''
                if latest_version_info and current_version != latest_version:
                    version_gap = _calculate_version_gap(current_version, latest_version)
                    
                    if version_gap >= 2:  # 메이저 버전이 2개 이상 차이
                        status = RESOURCE_STATUS_FAIL
                        status_text = '업그레이드 필요'
                        advice = f'현재 버전({current_version})이 최신 버전({latest_version})보다 {version_gap}개 버전 뒤처져 있습니다. 보안 및 성능 향상을 위해 업그레이드를 권장합니다.'
                    elif version_gap >= 1:  # 메이저 버전이 1개 차이
                        status = RESOURCE_STATUS_WARNING
                        status_text = '업그레이드 권장'
                        advice = f'현재 버전({current_version})보다 새로운 버전({latest_version})이 사용 가능합니다. 업그레이드를 고려하세요.'
                
                # 자동 마이너 버전 업그레이드 확인
                if not auto_minor_upgrade and status == RESOURCE_STATUS_PASS:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '자동 업그레이드 비활성화'
                    advice = f'자동 마이너 버전 업그레이드가 비활성화되어 있습니다. 보안 패치를 자동으로 받기 위해 활성화를 고려하세요.'
                
                # 지원 종료 예정 버전 확인
                if current_version_info and 'SupportedFeatureNames' in current_version_info:
                    if 'deprecated' in str(current_version_info).lower():
                        status = RESOURCE_STATUS_FAIL
                        status_text = '지원 종료 예정'
                        advice = f'현재 버전({current_version})이 지원 종료 예정입니다. 즉시 업그레이드하세요.'
                
                # 표준화된 리소스 결과 생성
                instance_result = create_resource_result(
                    resource_id=db_identifier,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    db_identifier=db_identifier,
                    region=region,
                    engine=engine,
                    current_version=current_version,
                    latest_version=latest_version_info.get('Version', 'N/A') if latest_version_info else 'N/A',
                    auto_minor_upgrade=auto_minor_upgrade
                )
                
                instance_analysis.append(instance_result)
        
        # 결과 분류
        passed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_PASS]
        warning_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_WARNING]
        failed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 인스턴스 카운트
        improvement_needed_count = len(failed_instances) + len(warning_instances)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 업그레이드 필요 인스턴스 찾기
        if failed_instances:
            recommendations.append(f'{len(failed_instances)}개 인스턴스에 엔진 버전 업그레이드가 필요합니다. (영향받는 인스턴스: {", ".join([i["db_identifier"] for i in failed_instances])})')
        
        # 업그레이드 권장 인스턴스 찾기
        if warning_instances:
            recommendations.append(f'{len(warning_instances)}개 인스턴스에 엔진 버전 업그레이드를 고려하세요. (영향받는 인스턴스: {", ".join([i["db_identifier"] for i in warning_instances])})')
        
        # 일반적인 권장사항
        recommendations.append('정기적으로 RDS 엔진 버전을 최신 상태로 유지하세요.')
        recommendations.append('자동 마이너 버전 업그레이드를 활성화하여 보안 패치를 자동으로 받으세요.')
        recommendations.append('메이저 버전 업그레이드 전에는 테스트 환경에서 충분히 검증하세요.')
        recommendations.append('지원 종료 예정 버전은 즉시 업그레이드하세요.')
        
        # 데이터 준비
        data = {
            'instances': instance_analysis,
            'passed_instances': passed_instances,
            'warning_instances': warning_instances,
            'failed_instances': failed_instances,
            'improvement_needed_count': improvement_needed_count,
            'total_instances_count': len(instance_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_instances) > 0:
            message = f'{len(instance_analysis)}개 인스턴스 중 {len(failed_instances)}개가 엔진 버전 업그레이드가 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_instances) > 0:
            message = f'{len(instance_analysis)}개 인스턴스 중 {len(warning_instances)}개에 엔진 버전 업그레이드를 고려하세요.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 인스턴스({len(passed_instances)}개)가 적절한 엔진 버전을 사용하고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'엔진 버전 및 업그레이드 검사 중 오류가 발생했습니다: {str(e)}')

def _compare_versions(version1: str, version2: str) -> int:
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

def _calculate_version_gap(current: str, latest: str) -> int:
    """버전 간격 계산 (메이저 버전 기준)"""
    try:
        current_major = int(current.split('.')[0])
        latest_major = int(latest.split('.')[0])
        return latest_major - current_major
    except:
        return 0