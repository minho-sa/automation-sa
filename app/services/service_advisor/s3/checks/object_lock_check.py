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
    S3 버킷의 객체 잠금(Object Lock) 설정을 검사하고 데이터 보호 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        s3_client = create_boto3_client('s3', role_arn=role_arn)
        
        # S3 버킷 목록 가져오기
        buckets = s3_client.list_buckets()
        
        # 버킷 분석 결과
        bucket_analysis = []
        
        for bucket in buckets.get('Buckets', []):
            bucket_name = bucket['Name']
            
            # 버킷 리전 정보 가져오기
            try:
                bucket_location = s3_client.get_bucket_location(Bucket=bucket_name)
                region = bucket_location.get('LocationConstraint') or 'us-east-1'
            except Exception:
                region = 'N/A'
            
            # 태그 가져오기
            try:
                tags_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
            except Exception:
                tags = {}
            
            # 중요 데이터 버킷인지 확인
            is_important_data = False
            for key, value in tags.items():
                if (key.lower() in ['data_classification', 'data-classification', 'importance'] and 
                    value.lower() in ['critical', 'sensitive', 'important', 'high']):
                    is_important_data = True
                    break
            
            # 버킷 이름으로도 중요 데이터 버킷 확인
            if not is_important_data and any(term in bucket_name.lower() for term in ['critical', 'sensitive', 'important', 'backup', 'archive']):
                is_important_data = True
            
            # 객체 잠금 설정 확인
            try:
                object_lock = s3_client.get_object_lock_configuration(Bucket=bucket_name)
                object_lock_enabled = object_lock.get('ObjectLockConfiguration', {}).get('ObjectLockEnabled') == 'Enabled'
                default_retention = object_lock.get('ObjectLockConfiguration', {}).get('Rule', {}).get('DefaultRetention', {})
                retention_mode = default_retention.get('Mode') if default_retention else None
                retention_period = None
                
                if default_retention:
                    if 'Days' in default_retention:
                        retention_period = f"{default_retention['Days']}일"
                    elif 'Years' in default_retention:
                        retention_period = f"{default_retention['Years']}년"
                
                # 객체 잠금 설정 분석
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if object_lock_enabled:
                    if retention_mode:
                        status_text = '객체 잠금 활성화됨'
                        advice = f'버킷에 객체 잠금이 활성화되어 있으며, 기본 보존 기간이 {retention_mode} 모드로 {retention_period} 설정되어 있습니다.'
                    else:
                        status_text = '객체 잠금 활성화됨'
                        advice = '버킷에 객체 잠금이 활성화되어 있지만, 기본 보존 기간이 설정되어 있지 않습니다. 필요한 경우 기본 보존 기간을 설정하세요.'
                elif is_important_data:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '객체 잠금 권장'
                    advice = '중요한 데이터를 저장하는 버킷에 객체 잠금이 활성화되어 있지 않습니다. 데이터 보호를 위해 객체 잠금 활성화를 고려하세요.'
                else:
                    status_text = '객체 잠금 없음'
                    advice = '버킷에 객체 잠금이 활성화되어 있지 않습니다. 중요한 데이터를 저장하는 경우 객체 잠금 활성화를 고려하세요.'
                
            except s3_client.exceptions.ClientError as e:
                if 'ObjectLockConfigurationNotFoundError' in str(e):
                    # 객체 잠금 설정이 없는 경우
                    if is_important_data:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '객체 잠금 권장'
                        advice = '중요한 데이터를 저장하는 버킷에 객체 잠금이 활성화되어 있지 않습니다. 데이터 보호를 위해 객체 잠금 활성화를 고려하세요.'
                    else:
                        status = RESOURCE_STATUS_PASS
                        status_text = '객체 잠금 없음'
                        advice = '버킷에 객체 잠금이 활성화되어 있지 않습니다. 중요한 데이터를 저장하는 경우 객체 잠금 활성화를 고려하세요.'
                else:
                    # 기타 오류
                    status = RESOURCE_STATUS_UNKNOWN
                    status_text = '확인 불가'
                    advice = f'버킷의 객체 잠금 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            except Exception as e:
                # 기타 오류
                status = RESOURCE_STATUS_UNKNOWN
                status_text = '확인 불가'
                advice = f'버킷의 객체 잠금 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            
            # 표준화된 리소스 결과 생성
            bucket_result = create_resource_result(
                resource_id=bucket_name,
                status=status,
                advice=advice,
                status_text=status_text,
                bucket_name=bucket_name,
                region=region,
                creation_date=bucket['CreationDate'].strftime('%Y-%m-%d'),
                object_lock_enabled=object_lock_enabled if 'object_lock_enabled' in locals() else False,
                retention_mode=retention_mode if 'retention_mode' in locals() and retention_mode else 'N/A',
                retention_period=retention_period if 'retention_period' in locals() and retention_period else 'N/A',
                is_important_data=is_important_data
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
        
        # 객체 잠금이 권장되는 버킷 찾기
        if warning_buckets:
            recommendations.append(f'{len(warning_buckets)}개 중요 데이터 버킷에 객체 잠금 활성화가 권장됩니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in warning_buckets])})')
        
        # 일반적인 권장사항
        recommendations.append('중요한 데이터를 저장하는 버킷에는 객체 잠금을 활성화하여 우발적인 삭제나 변경을 방지하세요.')
        recommendations.append('규정 준수 모드 또는 거버넌스 모드 중 적절한 모드를 선택하여 객체 잠금을 구성하세요.')
        recommendations.append('객체 잠금은 버킷 생성 시에만 활성화할 수 있으므로, 기존 버킷에 적용하려면 새 버킷을 생성하고 데이터를 마이그레이션해야 합니다.')
        
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
            message = f'{len(bucket_analysis)}개 버킷 중 {improvement_needed_count}개 중요 데이터 버킷에 객체 잠금 활성화가 권장됩니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 적절한 객체 잠금 설정을 가지고 있거나 객체 잠금이 필요하지 않습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'객체 잠금 설정 검사 중 오류가 발생했습니다: {str(e)}')