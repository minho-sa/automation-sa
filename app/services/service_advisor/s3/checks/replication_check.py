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
    S3 버킷의 복제(Replication) 설정을 검사하고 재해 복구 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        s3_client = create_boto3_client('s3')
        
        # S3 버킷 목록 가져오기
        buckets = s3_client.list_buckets()
        
        # 버킷 분석 결과
        bucket_analysis = []
        
        for bucket in buckets.get('Buckets', []):
            bucket_name = bucket['Name']
            
            # 태그 가져오기
            try:
                tags_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
            except Exception:
                tags = {}
            
            # 프로덕션 환경인지 확인
            is_production = False
            for key, value in tags.items():
                if (key.lower() in ['environment', 'env'] and 
                    value.lower() in ['prod', 'production']):
                    is_production = True
                    break
            
            # 버킷 이름으로도 프로덕션 환경 확인
            if not is_production and (bucket_name.lower().startswith(('prod-', 'production-')) or 
                                     'prod' in bucket_name.lower()):
                is_production = True
            
            # 버전 관리 설정 확인 (복제를 위해 필요)
            try:
                versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
                versioning_enabled = versioning.get('Status') == 'Enabled'
            except Exception:
                versioning_enabled = False
            
            # 복제 설정 확인
            try:
                replication = s3_client.get_bucket_replication(Bucket=bucket_name)
                replication_rules = replication.get('ReplicationConfiguration', {}).get('Rules', [])
                
                # 활성화된 규칙만 필터링
                active_rules = [rule for rule in replication_rules if rule.get('Status') == 'Enabled']
                
                # 복제 설정 분석
                has_replication = len(active_rules) > 0
                destination_buckets = []
                
                for rule in active_rules:
                    if 'Destination' in rule and 'Bucket' in rule['Destination']:
                        dest_bucket = rule['Destination']['Bucket']
                        if dest_bucket.startswith('arn:aws:s3:::'):
                            dest_bucket = dest_bucket[13:]  # "arn:aws:s3:::" 제거
                        destination_buckets.append(dest_bucket)
                
                # 상태 및 권장 사항 결정
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if has_replication:
                    status_text = '복제 활성화됨'
                    advice = f'버킷에 복제가 적절하게 구성되어 있습니다. 대상 버킷: {", ".join(destination_buckets)}'
                elif is_production and versioning_enabled:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '복제 권장'
                    advice = '프로덕션 환경의 버킷에 복제가 구성되어 있지 않습니다. 재해 복구 및 데이터 보호를 위해 복제 구성을 고려하세요.'
                elif is_production and not versioning_enabled:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '버전 관리 필요'
                    advice = '프로덕션 환경의 버킷에 버전 관리가 활성화되어 있지 않습니다. 복제를 구성하려면 먼저 버전 관리를 활성화하세요.'
                else:
                    status_text = '복제 없음'
                    advice = '버킷에 복제가 구성되어 있지 않습니다. 중요한 데이터를 저장하는 경우 복제 구성을 고려하세요.'
                
            except s3_client.exceptions.ClientError as e:
                if 'ReplicationConfigurationNotFoundError' in str(e):
                    # 복제 설정이 없는 경우
                    if is_production and versioning_enabled:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '복제 권장'
                        advice = '프로덕션 환경의 버킷에 복제가 구성되어 있지 않습니다. 재해 복구 및 데이터 보호를 위해 복제 구성을 고려하세요.'
                    elif is_production and not versioning_enabled:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '버전 관리 필요'
                        advice = '프로덕션 환경의 버킷에 버전 관리가 활성화되어 있지 않습니다. 복제를 구성하려면 먼저 버전 관리를 활성화하세요.'
                    else:
                        status = RESOURCE_STATUS_PASS
                        status_text = '복제 없음'
                        advice = '버킷에 복제가 구성되어 있지 않습니다. 중요한 데이터를 저장하는 경우 복제 구성을 고려하세요.'
                else:
                    # 기타 오류
                    status = RESOURCE_STATUS_UNKNOWN
                    status_text = '확인 불가'
                    advice = f'버킷의 복제 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            except Exception as e:
                # 기타 오류
                status = RESOURCE_STATUS_UNKNOWN
                status_text = '확인 불가'
                advice = f'버킷의 복제 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            
            # 표준화된 리소스 결과 생성
            bucket_result = create_resource_result(
                resource_id=bucket_name,
                status=status,
                advice=advice,
                status_text=status_text,
                bucket_name=bucket_name,
                creation_date=bucket['CreationDate'].strftime('%Y-%m-%d'),
                has_replication=has_replication if 'has_replication' in locals() else False,
                versioning_enabled=versioning_enabled,
                is_production=is_production,
                destination_buckets=destination_buckets if 'destination_buckets' in locals() else []
            )
            
            bucket_analysis.append(bucket_result)
        
        # 결과 분류
        passed_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_PASS]
        warning_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_WARNING]
        failed_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_FAIL]
        unknown_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_UNKNOWN]
        
        # 개선 필요 버킷 카운트
        improvement_needed_count = len(warning_buckets) + len(failed_buckets)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 복제가 권장되는 프로덕션 버킷 찾기
        prod_buckets_no_replication = [b for b in warning_buckets if b['status_text'] == '복제 권장']
        if prod_buckets_no_replication:
            recommendations.append(f'{len(prod_buckets_no_replication)}개 프로덕션 버킷에 복제 구성이 권장됩니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in prod_buckets_no_replication])})')
        
        # 버전 관리가 필요한 프로덕션 버킷 찾기
        prod_buckets_no_versioning = [b for b in warning_buckets if b['status_text'] == '버전 관리 필요']
        if prod_buckets_no_versioning:
            recommendations.append(f'{len(prod_buckets_no_versioning)}개 프로덕션 버킷에 버전 관리 활성화가 필요합니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in prod_buckets_no_versioning])})')
        
        # 일반적인 권장사항
        recommendations.append('중요한 데이터를 저장하는 버킷에는 다른 리전으로의 복제를 구성하여 재해 복구 기능을 강화하세요.')
        recommendations.append('복제를 구성하기 전에 버전 관리를 활성화해야 합니다.')
        recommendations.append('복제 규칙을 구성할 때 필요한 객체 메타데이터, 태그 및 ACL도 복제되도록 설정하세요.')
        
        # 데이터 준비
        data = {
            'buckets': bucket_analysis,
            'passed_buckets': passed_buckets,
            'warning_buckets': warning_buckets,
            'failed_buckets': failed_buckets,
            'unknown_buckets': unknown_buckets,
            'improvement_needed_count': improvement_needed_count,
            'total_buckets_count': len(bucket_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if improvement_needed_count > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {improvement_needed_count}개 프로덕션 버킷에 복제 구성이 권장됩니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 적절한 복제 설정을 가지고 있거나 복제가 필요하지 않습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'복제 설정 검사 중 오류가 발생했습니다: {str(e)}')