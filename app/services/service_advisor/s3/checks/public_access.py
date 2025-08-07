import boto3
import botocore
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    S3 버킷의 퍼블릭 액세스 설정을 검사하고 보안 개선 방안을 제안합니다.
    
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
            except Exception as e:
                region = 'N/A'
            
            # 퍼블릭 액세스 차단 설정 확인
            try:
                public_access_block = s3_client.get_public_access_block(Bucket=bucket_name)
                block_config = public_access_block['PublicAccessBlockConfiguration']
                
                # 모든 퍼블릭 액세스 차단 설정이 활성화되어 있는지 확인
                all_blocked = (
                    block_config.get('BlockPublicAcls', False) and
                    block_config.get('IgnorePublicAcls', False) and
                    block_config.get('BlockPublicPolicy', False) and
                    block_config.get('RestrictPublicBuckets', False)
                )
                
                # 버킷 정책 확인
                try:
                    policy = s3_client.get_bucket_policy(Bucket=bucket_name)
                    has_policy = True
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                        has_policy = False
                    else:
                        raise
                
                # ACL 확인
                acl = s3_client.get_bucket_acl(Bucket=bucket_name)
                public_acl = False
                
                for grant in acl.get('Grants', []):
                    grantee = grant.get('Grantee', {})
                    if grantee.get('URI') == 'http://acs.amazonaws.com/groups/global/AllUsers':
                        public_acl = True
                        break
                
                # 상태 및 권장 사항 결정
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if not all_blocked:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '퍼블릭 액세스 차단 미설정'
                    advice = '버킷에 퍼블릭 액세스 차단 설정이 완전히 활성화되어 있지 않습니다. 모든 퍼블릭 액세스 차단 설정을 활성화하세요.'
                elif public_acl:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '퍼블릭 ACL 감지됨'
                    advice = '버킷에 퍼블릭 ACL이 설정되어 있습니다. 퍼블릭 ACL을 제거하세요.'
                else:
                    status_text = '안전하게 구성됨'
                    advice = '버킷이 퍼블릭 액세스로부터 적절하게 보호되고 있습니다.'
                
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
                    # 퍼블릭 액세스 차단 설정이 없는 경우
                    status = RESOURCE_STATUS_FAIL
                    status_text = '퍼블릭 액세스 차단 없음'
                    advice = '버킷에 퍼블릭 액세스 차단 설정이 구성되어 있지 않습니다. 모든 퍼블릭 액세스 차단 설정을 활성화하세요.'
                else:
                    # 다른 ClientError 예외 처리
                    status = RESOURCE_STATUS_UNKNOWN
                    status_text = '확인 불가'
                    advice = f'버킷의 퍼블릭 액세스 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            except Exception as e:
                # 기타 오류
                status = RESOURCE_STATUS_UNKNOWN
                status_text = '확인 불가'
                advice = f'버킷의 퍼블릭 액세스 설정을 확인하는 중 오류가 발생했습니다: {str(e)}'
            
            # 표준화된 리소스 결과 생성
            bucket_result = create_resource_result(
                resource_id=bucket_name,
                status=status,
                advice=advice,
                status_text=status_text,
                bucket_name=bucket_name,
                region=region,
                creation_date=bucket['CreationDate'].strftime('%Y-%m-%d'),
                public_acl=public_acl if 'public_acl' in locals() else 'N/A',
                all_blocked=all_blocked if 'all_blocked' in locals() else 'N/A'
            )
            
            bucket_analysis.append(bucket_result)
        
        # 결과 분류
        passed_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_PASS]
        failed_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_FAIL]
        unknown_buckets = [b for b in bucket_analysis if b['status'] == RESOURCE_STATUS_UNKNOWN]
        
        # 개선 필요 버킷 카운트
        improvement_needed_count = len(failed_buckets)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = [
            '모든 S3 버킷에 퍼블릭 액세스 차단을 설정하세요.',
            '계정 수준에서 퍼블릭 액세스 차단을 활성화하세요.',
            '정기적으로 버킷 권한을 검토하세요.'
        ]
        
        # 데이터 준비
        data = {
            'buckets': bucket_analysis,
            'passed_buckets': passed_buckets,
            'failed_buckets': failed_buckets,
            'unknown_buckets': unknown_buckets,
            'improvement_needed_count': improvement_needed_count,
            'total_buckets_count': len(bucket_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_buckets) > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {len(failed_buckets)}개에 퍼블릭 액세스 차단 설정이 필요합니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=bucket_analysis,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 퍼블릭 액세스로부터 적절하게 보호되고 있습니다.'
            return create_unified_check_result(
                status=STATUS_OK,
                message=message,
                resources=bucket_analysis,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'퍼블릭 액세스 설정 검사 중 오류가 발생했습니다: {str(e)}')