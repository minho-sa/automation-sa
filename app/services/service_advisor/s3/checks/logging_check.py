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
    S3 버킷의 액세스 로깅 설정을 검사하고 보안 개선 방안을 제안합니다.
    
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
            
            # 로깅 설정 확인
            try:
                logging = s3_client.get_bucket_logging(Bucket=bucket_name)
                logging_enabled = 'LoggingEnabled' in logging
                target_bucket = logging.get('LoggingEnabled', {}).get('TargetBucket') if logging_enabled else None
                target_prefix = logging.get('LoggingEnabled', {}).get('TargetPrefix') if logging_enabled else None
                
                # 로깅 설정 분석
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if not logging_enabled:
                    if is_production:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '로깅 비활성화됨'
                        advice = '프로덕션 환경의 버킷에 액세스 로깅이 활성화되어 있지 않습니다. 보안 및 감사를 위해 액세스 로깅을 활성화하세요.'
                    else:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '로깅 권장'
                        advice = '버킷에 액세스 로깅이 활성화되어 있지 않습니다. 보안 및 감사를 위해 액세스 로깅을 활성화하는 것이 좋습니다.'
                else:
                    status_text = '로깅 활성화됨'
                    advice = f'버킷에 액세스 로깅이 적절하게 활성화되어 있습니다. 로그는 {target_bucket} 버킷의 {target_prefix} 접두사에 저장됩니다.'
                
            except Exception as e:
                # 로깅 설정을 확인할 수 없는 경우
                status = RESOURCE_STATUS_UNKNOWN
                status_text = '확인 불가'
                advice = f'버킷의 로깅 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            
            # 표준화된 리소스 결과 생성
            bucket_result = create_resource_result(
                resource_id=bucket_name,
                status=status,
                advice=advice,
                status_text=status_text,
                bucket_name=bucket_name,
                creation_date=bucket['CreationDate'].strftime('%Y-%m-%d'),
                logging_enabled=logging_enabled if 'logging_enabled' in locals() else False,
                target_bucket=target_bucket if 'target_bucket' in locals() and target_bucket else 'N/A',
                target_prefix=target_prefix if 'target_prefix' in locals() and target_prefix else 'N/A',
                is_production=is_production
            )
            
            bucket_analysis.append(bucket_result)
        
        # 결과 분류
        passed_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_PASS]
        warning_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_WARNING]
        failed_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_FAIL]
        unknown_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_UNKNOWN]
        
        # 개선 필요 버킷 카운트
        improvement_needed_count = len(failed_buckets) + len(warning_buckets)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 로깅이 필요한 프로덕션 버킷 찾기
        if failed_buckets:
            recommendations.append(f'{len(failed_buckets)}개 프로덕션 버킷에 액세스 로깅 활성화가 필요합니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in failed_buckets])})')
        
        # 로깅이 권장되는 버킷 찾기
        if warning_buckets:
            recommendations.append(f'{len(warning_buckets)}개 버킷에 액세스 로깅 활성화가 권장됩니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in warning_buckets])})')
        
        # 일반적인 권장사항
        recommendations.append('중요한 데이터를 저장하는 모든 버킷에 액세스 로깅을 활성화하세요.')
        recommendations.append('로그 버킷에는 적절한 수명 주기 정책을 설정하여 로그 보존 비용을 최적화하세요.')
        recommendations.append('로그 버킷에 대한 액세스를 제한하고 로그 파일을 보호하세요.')
        
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
        if len(failed_buckets) > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {len(failed_buckets)}개 프로덕션 버킷에 액세스 로깅 활성화가 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_buckets) > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {len(warning_buckets)}개 버킷에 액세스 로깅 활성화가 권장됩니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 적절한 액세스 로깅 설정을 가지고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'액세스 로깅 설정 검사 중 오류가 발생했습니다: {str(e)}')