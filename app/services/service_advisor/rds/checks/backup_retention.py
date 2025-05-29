import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run() -> Dict[str, Any]:
    """
    RDS 인스턴스의 백업 보존 기간을 검사하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        rds_client = create_boto3_client('rds')
        
        # RDS 인스턴스 목록 가져오기
        instances = rds_client.describe_db_instances()
        
        # 인스턴스 분석 결과
        instance_analysis = []
        
        # 권장 백업 보존 기간 (일)
        recommended_retention = 7
        
        for instance in instances.get('DBInstances', []):
            instance_id = instance['DBInstanceIdentifier']
            engine = instance['Engine']
            retention_period = instance['BackupRetentionPeriod']
            
            # 백업 보존 기간 분석
            status = RESOURCE_STATUS_PASS
            advice = None
            status_text = None
            
            if retention_period < 1:
                status = RESOURCE_STATUS_FAIL
                status_text = '백업 없음'
                advice = f'자동 백업이 비활성화되어 있습니다. 최소 {recommended_retention}일의 백업 보존 기간을 설정하세요.'
            elif retention_period < recommended_retention:
                status = RESOURCE_STATUS_WARNING
                status_text = '보존 기간 부족'
                advice = f'백업 보존 기간이 {retention_period}일로 설정되어 있습니다. 최소 {recommended_retention}일로 늘리는 것이 좋습니다.'
            else:
                status_text = '최적화됨'
                advice = f'백업 보존 기간이 {retention_period}일로 적절하게 설정되어 있습니다.'
            
            # 표준화된 리소스 결과 생성
            instance_result = create_resource_result(
                resource_id=instance_id,
                status=status,
                advice=advice,
                status_text=status_text,
                instance_id=instance_id,
                engine=engine,
                retention_period=retention_period,
                recommended_retention=recommended_retention
            )
            
            instance_analysis.append(instance_result)
        
        # 결과 분류
        passed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_PASS]
        warning_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_WARNING]
        failed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 인스턴스 카운트
        improvement_needed_count = len(warning_instances) + len(failed_instances)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 백업 없는 인스턴스 찾기
        if failed_instances:
            recommendations.append(f'{len(failed_instances)}개 인스턴스에 자동 백업이 비활성화되어 있습니다. 백업을 활성화하세요. (영향받는 인스턴스: {", ".join([i["instance_id"] for i in failed_instances])})')
        
        # 보존 기간 부족 인스턴스 찾기
        if warning_instances:
            recommendations.append(f'{len(warning_instances)}개 인스턴스의 백업 보존 기간이 권장 기간({recommended_retention}일)보다 짧습니다. 보존 기간을 늘리세요. (영향받는 인스턴스: {", ".join([i["instance_id"] for i in warning_instances])})')
        
        # 일반적인 권장사항
        recommendations.append(f'프로덕션 데이터베이스의 경우 최소 {recommended_retention}일의 백업 보존 기간을 설정하세요.')
        recommendations.append('중요한 데이터베이스의 경우 스냅샷을 정기적으로 생성하여 장기 보존하는 것이 좋습니다.')
        
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
            message = f'{len(instance_analysis)}개 인스턴스 중 {len(failed_instances)}개에 자동 백업이 비활성화되어 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_instances) > 0:
            message = f'{len(instance_analysis)}개 인스턴스 중 {len(warning_instances)}개의 백업 보존 기간이 권장 기간보다 짧습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 인스턴스({len(passed_instances)}개)의 백업 보존 기간이 적절하게 설정되어 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'백업 보존 기간 검사 중 오류가 발생했습니다: {str(e)}')