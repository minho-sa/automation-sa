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
    S3 버킷의 수명 주기 정책 설정을 검사하고 비용 최적화 방안을 제안합니다.
    
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
            
            # 버전 관리 설정 확인
            try:
                versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
                versioning_enabled = versioning.get('Status') == 'Enabled'
            except Exception:
                versioning_enabled = False
            
            # 수명 주기 정책 확인
            try:
                lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                lifecycle_rules = lifecycle.get('Rules', [])
                
                # 활성화된 규칙만 필터링
                active_rules = [rule for rule in lifecycle_rules if rule.get('Status') == 'Enabled']
                
                # 수명 주기 정책 분석
                has_transition_rule = False
                has_expiration_rule = False
                has_noncurrent_version_rule = False
                
                for rule in active_rules:
                    if 'Transitions' in rule:
                        has_transition_rule = True
                    if 'Expiration' in rule:
                        has_expiration_rule = True
                    if 'NoncurrentVersionTransitions' in rule or 'NoncurrentVersionExpiration' in rule:
                        has_noncurrent_version_rule = True
                
                # 상태 및 권장 사항 결정
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if len(active_rules) == 0:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '정책 없음'
                    advice = '버킷에 수명 주기 정책이 설정되어 있지 않습니다. 비용 최적화를 위해 수명 주기 정책을 설정하세요.'
                elif versioning_enabled and not has_noncurrent_version_rule:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '이전 버전 정책 없음'
                    advice = '버킷에 버전 관리가 활성화되어 있지만, 이전 버전 객체에 대한 수명 주기 정책이 없습니다. 비용 최적화를 위해 이전 버전 객체에 대한 정책을 설정하세요.'
                elif not has_transition_rule and not has_expiration_rule:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '전환/만료 정책 없음'
                    advice = '버킷에 객체 전환 또는 만료 정책이 설정되어 있지 않습니다. 비용 최적화를 위해 객체 전환 또는 만료 정책을 설정하세요.'
                else:
                    status_text = '최적화됨'
                    advice = '버킷에 적절한 수명 주기 정책이 설정되어 있습니다.'
                
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                    # 수명 주기 정책이 없는 경우
                    status = RESOURCE_STATUS_FAIL
                    status_text = '정책 없음'
                    advice = '버킷에 수명 주기 정책이 설정되어 있지 않습니다. 비용 최적화를 위해 수명 주기 정책을 설정하세요.'
                else:
                    # 다른 ClientError 예외 처리
                    status = RESOURCE_STATUS_UNKNOWN
                    status_text = '확인 불가'
                    advice = f'버킷의 수명 주기 정책을 확인하는 중 오류가 발생했습니다: {str(e)}'
            except Exception as e:
                # 기타 오류
                status = RESOURCE_STATUS_UNKNOWN
                status_text = '확인 불가'
                advice = f'버킷의 수명 주기 정책을 확인하는 중 오류가 발생했습니다: {str(e)}'
            
            # 표준화된 리소스 결과 생성
            bucket_result = create_resource_result(
                resource_id=bucket_name,
                status=status,
                advice=advice,
                status_text=status_text,
                bucket_name=bucket_name,
                creation_date=bucket['CreationDate'].strftime('%Y-%m-%d'),
                versioning_enabled=versioning_enabled,
                has_lifecycle_rules=len(active_rules) > 0 if 'active_rules' in locals() else False,
                rule_count=len(active_rules) if 'active_rules' in locals() else 0
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
        
        # 수명 주기 정책이 없는 버킷 찾기
        if failed_buckets:
            recommendations.append(f'{len(failed_buckets)}개 버킷에 수명 주기 정책 설정이 필요합니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in failed_buckets])})')
        
        # 수명 주기 정책 개선이 필요한 버킷 찾기
        if warning_buckets:
            recommendations.append(f'{len(warning_buckets)}개 버킷의 수명 주기 정책 개선이 필요합니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in warning_buckets])})')
        
        # 일반적인 권장사항
        recommendations.append('모든 버킷에 비용 최적화를 위한 수명 주기 정책을 설정하세요.')
        recommendations.append('자주 액세스하지 않는 객체는 S3 Standard-IA 또는 S3 Glacier로 전환하도록 설정하세요.')
        recommendations.append('버전 관리가 활성화된 버킷에는 이전 버전 객체에 대한 수명 주기 정책을 설정하세요.')
        
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
            message = f'{len(bucket_analysis)}개 버킷 중 {len(failed_buckets)}개에 수명 주기 정책 설정이 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        elif len(warning_buckets) > 0:
            message = f'{len(bucket_analysis)}개 버킷 중 {len(warning_buckets)}개의 수명 주기 정책 개선이 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 적절한 수명 주기 정책을 가지고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'수명 주기 정책 검사 중 오류가 발생했습니다: {str(e)}')