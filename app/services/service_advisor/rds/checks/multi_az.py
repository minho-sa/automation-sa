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
    RDS 인스턴스의 다중 AZ 구성을 검사하고 고가용성 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        rds_client = create_boto3_client('rds', role_arn=role_arn)
        
        # RDS 인스턴스 목록 가져오기
        instances = rds_client.describe_db_instances()
        
        # 인스턴스 분석 결과
        instance_analysis = []
        
        # 프로덕션 환경으로 간주할 인스턴스 태그 또는 이름 패턴
        production_indicators = ['prod', 'production', 'prd']
        
        for instance in instances.get('DBInstances', []):
            instance_id = instance['DBInstanceIdentifier']
            engine = instance['Engine']
            multi_az = instance['MultiAZ']
            instance_class = instance['DBInstanceClass']
            
            # 인스턴스가 프로덕션 환경인지 추정
            is_production = False
            
            # 인스턴스 이름에서 프로덕션 환경 여부 추정
            for indicator in production_indicators:
                if indicator in instance_id.lower():
                    is_production = True
                    break
            
            # 태그에서 프로덕션 환경 여부 추정
            try:
                tags_response = rds_client.list_tags_for_resource(
                    ResourceName=instance['DBInstanceArn']
                )
                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
                
                for key, value in tags.items():
                    if (key.lower() in ['environment', 'env'] and 
                        any(ind in value.lower() for ind in production_indicators)):
                        is_production = True
                        break
            except Exception:
                pass
            
            # 다중 AZ 구성 분석
            status = RESOURCE_STATUS_PASS
            advice = None
            status_text = None
            
            if is_production and not multi_az:
                status = RESOURCE_STATUS_FAIL
                status_text = '다중 AZ 필요'
                advice = '프로덕션 환경으로 추정되는 인스턴스에 다중 AZ가 구성되어 있지 않습니다. 고가용성을 위해 다중 AZ를 활성화하세요.'
            elif not is_production and not multi_az:
                status = RESOURCE_STATUS_WARNING
                status_text = '다중 AZ 권장'
                advice = '중요한 워크로드의 경우 고가용성을 위해 다중 AZ를 활성화하는 것이 좋습니다.'
            elif multi_az:
                status_text = '다중 AZ 활성화됨'
                advice = '다중 AZ가 적절하게 구성되어 있습니다.'
            
            # 표준화된 리소스 결과 생성
            instance_result = create_resource_result(
                resource_id=instance_id,
                status=status,
                advice=advice,
                status_text=status_text,
                instance_id=instance_id,
                engine=engine,
                instance_class=instance_class,
                multi_az=multi_az,
                is_production=is_production
            )
            
            instance_analysis.append(instance_result)
        
        # 결과 분류
        passed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_PASS]
        warning_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_WARNING]
        failed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 인스턴스 카운트
        improvement_needed_count = len(failed_instances)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 다중 AZ 필요 인스턴스 찾기
        if failed_instances:
            recommendations.append(f'{len(failed_instances)}개의 프로덕션 인스턴스에 다중 AZ가 구성되어 있지 않습니다. 고가용성을 위해 다중 AZ를 활성화하세요. (영향받는 인스턴스: {", ".join([i["instance_id"] for i in failed_instances])})')
        
        # 다중 AZ 권장 인스턴스 찾기
        if warning_instances:
            recommendations.append(f'{len(warning_instances)}개 인스턴스에 다중 AZ 구성을 고려하세요. (영향받는 인스턴스: {", ".join([i["instance_id"] for i in warning_instances])})')
        
        # 일반적인 권장사항
        recommendations.append('프로덕션 환경의 모든 데이터베이스는 고가용성을 위해 다중 AZ로 구성하는 것이 좋습니다.')
        recommendations.append('다중 AZ 구성은 계획된 유지 관리 및 예기치 않은 장애 시 가용성을 높입니다.')
        
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
            message = f'{len(instance_analysis)}개 인스턴스 중 {len(failed_instances)}개의 프로덕션 인스턴스에 다중 AZ가 구성되어 있지 않습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_instances) > 0:
            message = f'{len(instance_analysis)}개 인스턴스 중 {len(warning_instances)}개 인스턴스에 다중 AZ 구성을 고려하세요.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 인스턴스({len(passed_instances)}개)가 적절하게 구성되어 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'다중 AZ 구성 검사 중 오류가 발생했습니다: {str(e)}')