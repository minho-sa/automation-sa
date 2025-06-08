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
    S3 버킷의 버전 관리 설정을 검사하고 데이터 보호 개선 방안을 제안합니다.
    
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
            
            # 버전 관리 설정 확인
            try:
                versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
                versioning_status = versioning.get('Status', 'Suspended')
                
                # 버전 관리 설정 분석
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if versioning_status == 'Enabled':
                    status_text = '활성화됨'
                    advice = '버킷에 버전 관리가 적절하게 활성화되어 있습니다.'
                elif is_production:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '비활성화됨'
                    advice = '프로덕션 환경의 버킷에 버전 관리가 활성화되어 있지 않습니다. 데이터 보호를 위해 버전 관리를 활성화하세요.'
                else:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '비활성화됨'
                    advice = '버킷에 버전 관리가 활성화되어 있지 않습니다. 중요한 데이터를 저장하는 경우 버전 관리를 활성화하는 것이 좋습니다.'
                
            except Exception as e:
                # 버전 관리 설정을 확인할 수 없는 경우
                status = RESOURCE_STATUS_UNKNOWN
                status_text = '확인 불가'
                advice = f'버킷의 버전 관리 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            
            # 표준화된 리소스 결과 생성
            bucket_result = create_resource_result(
                resource_id=bucket_name,
                status=status,
                advice=advice,
                status_text=status_text,
                bucket_name=bucket_name,
                creation_date=bucket['CreationDate'].strftime('%Y-%m-%d'),
                versioning_status=versioning_status if 'versioning_status' in locals() else 'Unknown',
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
        
        # 버전 관리가 필요한 프로덕션 버킷 찾기
        if failed_buckets:
            recommendations.append(f'{len(failed_buckets)}개 프로덕션 버킷에 버전 관리 활성화가 필요합니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in failed_buckets])})')
        
        # 버전 관리가 권장되는 버킷 찾기
        if warning_buckets:
            recommendations.append(f'{len(warning_buckets)}개 버킷에 버전 관리 활성화가 권장됩니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in warning_buckets])})')
        
        # 일반적인 권장사항
        recommendations.append('중요한 데이터를 저장하는 모든 버킷에 버전 관리를 활성화하세요.')
        recommendations.append('버전 관리를 활성화한 버킷에는 수명 주기 정책을 설정하여 이전 버전의 객체 관리 비용을 최적화하세요.')
        
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
            message = f'{len(bucket_analysis)}개 버킷 중 {len(failed_buckets)}개 프로덕션 버킷에 버전 관리 활성화가 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_buckets) > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {len(warning_buckets)}개 버킷에 버전 관리 활성화가 권장됩니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 적절한 버전 관리 설정을 가지고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'버전 관리 설정 검사 중 오류가 발생했습니다: {str(e)}')