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
    S3 버킷의 S3 Intelligent-Tiering 설정을 검사하고 비용 최적화 방안을 제안합니다.
    
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
            
            # 수명 주기 정책 확인
            try:
                lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                lifecycle_rules = lifecycle.get('Rules', [])
                
                # 활성화된 규칙만 필터링
                active_rules = [rule for rule in lifecycle_rules if rule.get('Status') == 'Enabled']
                
                # Intelligent-Tiering 설정 확인
                has_intelligent_tiering = False
                has_archive_tiers = False
                
                for rule in active_rules:
                    if 'Transitions' in rule:
                        for transition in rule['Transitions']:
                            if transition.get('StorageClass') == 'INTELLIGENT_TIERING':
                                has_intelligent_tiering = True
                            elif transition.get('StorageClass') in ['GLACIER', 'DEEP_ARCHIVE']:
                                has_archive_tiers = True
                
                # 상태 및 권장 사항 결정
                status = RESOURCE_STATUS_PASS
                advice = None
                status_text = None
                
                if has_intelligent_tiering:
                    status_text = 'Intelligent-Tiering 활성화됨'
                    advice = '버킷에 S3 Intelligent-Tiering이 적절하게 구성되어 있습니다.'
                elif has_archive_tiers:
                    status_text = '아카이브 계층 사용 중'
                    advice = '버킷에 Glacier 또는 Deep Archive 스토리지 클래스로의 전환이 구성되어 있습니다. 액세스 패턴이 예측할 수 없는 데이터의 경우 S3 Intelligent-Tiering을 고려하세요.'
                else:
                    status = RESOURCE_STATUS_WARNING
                    status_text = 'Intelligent-Tiering 권장'
                    advice = '버킷에 S3 Intelligent-Tiering이 구성되어 있지 않습니다. 액세스 패턴이 예측할 수 없는 데이터의 경우 비용 최적화를 위해 S3 Intelligent-Tiering을 고려하세요.'
                
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                    # 수명 주기 정책이 없는 경우
                    status = RESOURCE_STATUS_WARNING
                    status_text = '수명 주기 정책 없음'
                    advice = '버킷에 수명 주기 정책이 설정되어 있지 않습니다. 비용 최적화를 위해 S3 Intelligent-Tiering 또는 다른 스토리지 클래스로의 전환을 고려하세요.'
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
                has_intelligent_tiering=has_intelligent_tiering if 'has_intelligent_tiering' in locals() else False,
                has_archive_tiers=has_archive_tiers if 'has_archive_tiers' in locals() else False,
                has_lifecycle_rules=len(active_rules) > 0 if 'active_rules' in locals() else False
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
        
        # Intelligent-Tiering이 권장되는 버킷 찾기
        if warning_buckets:
            recommendations.append(f'{len(warning_buckets)}개 버킷에 S3 Intelligent-Tiering 구성이 권장됩니다. (영향받는 버킷: {", ".join([b["bucket_name"] for b in warning_buckets])})')
        
        # 일반적인 권장사항
        recommendations.append('액세스 패턴이 예측할 수 없는 데이터에는 S3 Intelligent-Tiering을 사용하여 자동으로 비용을 최적화하세요.')
        recommendations.append('S3 Intelligent-Tiering은 30일 동안 액세스하지 않은 객체를 저비용 계층으로 자동 이동합니다.')
        recommendations.append('아카이브 액세스 계층을 활성화하여 90일, 180일 이상 액세스하지 않은 데이터를 더 저렴한 계층으로 자동 이동할 수 있습니다.')
        
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
            message = f'{len(bucket_analysis)}개 버킷 중 {improvement_needed_count}개 버킷에 S3 Intelligent-Tiering 구성이 권장됩니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 버킷({len(passed_buckets)}개)이 적절한 스토리지 클래스 설정을 가지고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Intelligent-Tiering 설정 검사 중 오류가 발생했습니다: {str(e)}')