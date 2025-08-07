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
    RDS 인스턴스의 암호화 설정을 검사하고 개선 방안을 제안합니다.
    
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
                instance_id = instance['DBInstanceIdentifier']
                engine = instance['Engine']
                storage_encrypted = instance.get('StorageEncrypted', False)
                
                # 태그 가져오기
                try:
                    tags_response = rds_client.list_tags_for_resource(
                        ResourceName=instance['DBInstanceArn']
                    )
                    tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
                except Exception:
                    tags = {}
                
                # 프로덕션 환경인지 확인
                is_production = False
                for key, value in tags.items():
                    if (key.lower() in ['environment', 'env'] and 
                        value.lower() in ['prod', 'production']):
                        is_production = True
                        break
                
                # 인스턴스 이름으로도 프로덕션 환경 확인
                if not is_production and (instance_id.lower().startswith(('prod-', 'production-')) or 
                                         'prod' in instance_id.lower()):
                    is_production = True
                
                # 암호화 설정 분석
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if not storage_encrypted:
                    if is_production:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '암호화 필요'
                        advice = '프로덕션 환경의 데이터베이스가 암호화되어 있지 않습니다. 스냅샷을 생성하고 암호화된 새 인스턴스로 복원하세요.'
                    else:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '암호화 권장'
                        advice = '데이터베이스가 암호화되어 있지 않습니다. 데이터 보호를 위해 암호화를 활성화하는 것이 좋습니다.'
                else:
                    status_text = '최적화됨'
                    advice = '데이터베이스가 적절하게 암호화되어 있습니다.'
                
                # 표준화된 리소스 결과 생성
                instance_result = create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    region=region,
                    engine=engine,
                    storage_encrypted=storage_encrypted,
                    is_production=is_production
                )
                
                instance_analysis.append(instance_result)

        
        # 결과 분류
        passed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_PASS]
        warning_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_WARNING]
        failed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 인스턴스 카운트
        improvement_needed_count = len(warning_instances) + len(failed_instances)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = [
            '모든 RDS 인스턴스에 암호화를 활성화하세요.',
            '스냅샷을 통해 기존 인스턴스를 암호화하세요.',
            'KMS 키로 암호화 키를 관리하세요.'
        ]
        
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
            message = f'{len(instance_analysis)}개 인스턴스 중 {len(failed_instances)}개 프로덕션 인스턴스가 암호화되어 있지 않습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_instances) > 0:
            message = f'{len(instance_analysis)}개 인스턴스 중 {len(warning_instances)}개 인스턴스가 암호화되어 있지 않습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 인스턴스({len(passed_instances)}개)가 적절하게 암호화되어 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'암호화 설정 검사 중 오류가 발생했습니다: {str(e)}')