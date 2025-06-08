import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    S3 버킷의 암호화 설정을 검사하고 보안 개선 방안을 제안합니다.
    
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
            
            # 기본 암호화 설정 확인
            try:
                encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                encryption_rules = encryption.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
                
                # 암호화 설정 분석
                has_encryption = len(encryption_rules) > 0
                encryption_type = None
                kms_key_id = None
                
                if has_encryption:
                    for rule in encryption_rules:
                        if 'ApplyServerSideEncryptionByDefault' in rule:
                            default_encryption = rule['ApplyServerSideEncryptionByDefault']
                            encryption_type = default_encryption.get('SSEAlgorithm')
                            kms_key_id = default_encryption.get('KMSMasterKeyID')
                
                # 상태 및 권장 사항 결정
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if not has_encryption:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '암호화 없음'
                    advice = '버킷에 기본 암호화가 설정되어 있지 않습니다. SSE-S3 또는 SSE-KMS 암호화를 활성화하세요.'
                elif encryption_type == 'AES256':
                    status_text = 'SSE-S3 암호화'
                    advice = '버킷에 SSE-S3 암호화가 설정되어 있습니다. 더 강력한 보안을 위해 SSE-KMS 암호화를 고려하세요.'
                elif encryption_type == 'aws:kms':
                    status_text = 'SSE-KMS 암호화'
                    advice = '버킷에 SSE-KMS 암호화가 적절하게 설정되어 있습니다.'
                else:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '알 수 없는 암호화'
                    advice = f'버킷에 알 수 없는 암호화 유형({encryption_type})이 설정되어 있습니다. SSE-S3 또는 SSE-KMS 암호화를 사용하세요.'
                
            except s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                # 암호화 설정이 없는 경우
                status = RESOURCE_STATUS_FAIL
                status_text = '암호화 없음'
                advice = '버킷에 기본 암호화가 설정되어 있지 않습니다. SSE-S3 또는 SSE-KMS 암호화를 활성화하세요.'
            except Exception as e:
                # 기타 오류
                status = RESOURCE_STATUS_UNKNOWN
                status_text = '확인 불가'
                advice = f'버킷의 암호화 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            
            # 표준화된 리소스 결과 생성
            bucket_result = create_resource_result(
                resource_id=bucket_name,
                status=status,
                advice=advice,
                status_text=status_text,
                bucket_name=bucket_name,
                creation_date=bucket['CreationDate'].strftime('%Y-%m-%d'),
                encryption_type=encryption_type if 'encryption_type' in locals() and encryption_type else 'None'
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
        
        # 암호화가 필요한 버킷 찾기
        if failed_buckets:
            recommendations.append(f'{len(failed_buckets)}개 버킷에 기본 암호화 설정이 필요합니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in failed_buckets])})')
        
        # 일반적인 권장사항
        recommendations.append('모든 S3 버킷에 기본 암호화를 설정하세요.')
        recommendations.append('중요한 데이터를 저장하는 버킷에는 SSE-KMS 암호화를 사용하세요.')
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_buckets) > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {len(failed_buckets)}개에 기본 암호화 설정이 필요합니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=bucket_analysis,
                recommendations=recommendations
            )
        elif len(warning_buckets) > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {len(warning_buckets)}개에 암호화 설정 개선이 필요합니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=bucket_analysis,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 적절하게 암호화되어 있습니다.'
            return create_unified_check_result(
                status=STATUS_OK,
                message=message,
                resources=bucket_analysis,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'암호화 설정 검사 중 오류가 발생했습니다: {str(e)}')