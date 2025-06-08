import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    RDS 인스턴스의 공개 액세스 설정을 검사하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        rds_client = create_boto3_client('rds')
        
        # RDS 인스턴스 목록 가져오기
        instances = rds_client.describe_db_instances()
        
        # 인스턴스 분석 결과
        instance_analysis = []
        
        for instance in instances.get('DBInstances', []):
            instance_id = instance['DBInstanceIdentifier']
            engine = instance['Engine']
            publicly_accessible = instance.get('PubliclyAccessible', False)
            
            # 태그 가져오기
            try:
                tags_response = rds_client.list_tags_for_resource(
                    ResourceName=instance['DBInstanceArn']
                )
                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
            except Exception:
                tags = {}
            
            # 공개 액세스 설정 분석
            status = RESOURCE_STATUS_PASS
            advice = None
            status_text = None
            
            if publicly_accessible:
                status = RESOURCE_STATUS_FAIL
                status_text = '공개 액세스 활성화됨'
                advice = '데이터베이스가 공개적으로 액세스 가능하도록 설정되어 있습니다. 보안을 강화하기 위해 공개 액세스를 비활성화하고 VPC 내에서만 액세스할 수 있도록 구성하세요.'
            else:
                status_text = '최적화됨'
                advice = '데이터베이스가 공개적으로 액세스할 수 없도록 적절하게 구성되어 있습니다.'
            
            # 표준화된 리소스 결과 생성
            instance_result = create_resource_result(
                resource_id=instance_id,
                status=status,
                advice=advice,
                status_text=status_text,
                instance_id=instance_id,
                engine=engine,
                publicly_accessible=publicly_accessible
            )
            
            instance_analysis.append(instance_result)
        
        # 결과 분류
        passed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_PASS]
        failed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 인스턴스 카운트
        improvement_needed_count = len(failed_instances)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 공개 액세스 인스턴스 찾기
        if failed_instances:
            recommendations.append(f'{len(failed_instances)}개 인스턴스가 공개적으로 액세스 가능하도록 설정되어 있습니다. 보안을 강화하기 위해 공개 액세스를 비활성화하세요. (영향받는 인스턴스: {", ".join([i["instance_id"] for i in failed_instances])})')
        
        # 일반적인 권장사항
        recommendations.append('데이터베이스는 VPC 내에서만 액세스할 수 있도록 구성하세요.')
        recommendations.append('필요한 경우 VPN, Direct Connect 또는 AWS PrivateLink를 사용하여 안전하게 액세스하세요.')
        recommendations.append('보안 그룹을 사용하여 데이터베이스에 대한 액세스를 제한하세요.')
        
        # 데이터 준비
        data = {
            'instances': instance_analysis,
            'passed_instances': passed_instances,
            'failed_instances': failed_instances,
            'improvement_needed_count': improvement_needed_count,
            'total_instances_count': len(instance_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if improvement_needed_count > 0:
            message = f'{len(instance_analysis)}개 인스턴스 중 {improvement_needed_count}개가 공개적으로 액세스 가능하도록 설정되어 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 인스턴스({len(passed_instances)}개)가 공개적으로 액세스할 수 없도록 적절하게 구성되어 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'공개 액세스 설정 검사 중 오류가 발생했습니다: {str(e)}')