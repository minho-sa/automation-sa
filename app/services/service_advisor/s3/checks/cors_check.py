import boto3
import botocore
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    S3 버킷의 CORS(Cross-Origin Resource Sharing) 설정을 검사하고 보안 개선 방안을 제안합니다.
    
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
            
            # CORS 설정 확인
            try:
                cors = s3_client.get_bucket_cors(Bucket=bucket_name)
                cors_rules = cors.get('CORSRules', [])
                
                # CORS 설정 분석
                has_cors = len(cors_rules) > 0
                has_wildcard_origin = False
                has_wildcard_method = False
                
                for rule in cors_rules:
                    if '*' in rule.get('AllowedOrigins', []):
                        has_wildcard_origin = True
                    if '*' in rule.get('AllowedMethods', []):
                        has_wildcard_method = True
                
                # 상태 및 권장 사항 결정
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if has_cors:
                    if has_wildcard_origin and has_wildcard_method:
                        status = RESOURCE_STATUS_FAIL
                        status_text = '과도한 CORS 설정'
                        advice = '버킷에 모든 오리진(*) 및 모든 메서드(*)에 대한 CORS 설정이 있습니다. 필요한 오리진과 메서드만 허용하도록 CORS 설정을 제한하세요.'
                    elif has_wildcard_origin:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '광범위한 CORS 설정'
                        advice = '버킷에 모든 오리진(*)에 대한 CORS 설정이 있습니다. 필요한 오리진만 허용하도록 CORS 설정을 제한하세요.'
                    else:
                        status_text = '최적화됨'
                        advice = '버킷에 적절한 CORS 설정이 구성되어 있습니다.'
                else:
                    status_text = 'CORS 없음'
                    advice = '버킷에 CORS 설정이 없습니다. 웹 애플리케이션에서 버킷의 리소스에 액세스해야 하는 경우 CORS를 구성하세요.'
                
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchCORSConfiguration':
                    # CORS 설정이 없는 경우
                    status = RESOURCE_STATUS_PASS
                    status_text = 'CORS 없음'
                    advice = '버킷에 CORS 설정이 없습니다. 웹 애플리케이션에서 버킷의 리소스에 액세스해야 하는 경우 CORS를 구성하세요.'
                else:
                    # 다른 ClientError 예외 처리
                    status = RESOURCE_STATUS_UNKNOWN
                    status_text = '확인 불가'
                    advice = f'버킷의 CORS 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            except Exception as e:
                # 기타 오류
                status = RESOURCE_STATUS_UNKNOWN
                status_text = '확인 불가'
                advice = f'버킷의 CORS 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            
            # 표준화된 리소스 결과 생성
            bucket_result = create_resource_result(
                resource_id=bucket_name,
                status=status,
                advice=advice,
                status_text=status_text,
                bucket_name=bucket_name,
                creation_date=bucket['CreationDate'].strftime('%Y-%m-%d'),
                has_cors=has_cors if 'has_cors' in locals() else False,
                has_wildcard_origin=has_wildcard_origin if 'has_wildcard_origin' in locals() else False,
                has_wildcard_method=has_wildcard_method if 'has_wildcard_method' in locals() else False
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
        
        # 과도한 CORS 설정이 있는 버킷 찾기
        if failed_buckets:
            recommendations.append(f'{len(failed_buckets)}개 버킷에 과도한 CORS 설정이 있습니다. 필요한 오리진과 메서드만 허용하도록 제한하세요. (영향받는 버킷: {", ".join([b["bucket_name"] for b in failed_buckets])})')
        
        # 광범위한 CORS 설정이 있는 버킷 찾기
        if warning_buckets:
            recommendations.append(f'{len(warning_buckets)}개 버킷에 광범위한 CORS 설정이 있습니다. 필요한 오리진만 허용하도록 제한하세요. (영향받는 버킷: {", ".join([b["bucket_name"] for b in warning_buckets])})')
        
        # 일반적인 권장사항
        recommendations.append('CORS 설정에서 와일드카드(*) 대신 특정 오리진을 지정하세요.')
        recommendations.append('필요한 HTTP 메서드(GET, PUT 등)만 허용하세요.')
        recommendations.append('필요한 경우에만 CORS 설정을 구성하고, 정기적으로 검토하세요.')
        
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
            message = f'{len(bucket_analysis)}개 버킷 중 {len(failed_buckets)}개에 과도한 CORS 설정이 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_buckets) > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {len(warning_buckets)}개에 광범위한 CORS 설정이 있습니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 적절한 CORS 설정을 가지고 있거나 CORS가 필요하지 않습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'CORS 설정 검사 중 오류가 발생했습니다: {str(e)}')