"""
S3 버킷의 암호화 설정을 검사하는 모듈
"""
import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

class EncryptionCheck:
    """S3 버킷의 암호화 설정을 검사하는 클래스"""
    
    check_id = 's3-encryption-check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """
        S3 버킷 및 암호화 설정 데이터를 수집합니다.
        
        Args:
            role_arn: AWS 역할 ARN
            
        Returns:
            Dict[str, Any]: 수집된 데이터
        """
        s3_client = create_boto3_client('s3', role_arn=role_arn)
        
        # S3 버킷 목록 가져오기
        buckets = s3_client.list_buckets()
        
        # 버킷별 암호화 설정 수집
        bucket_details = []
        
        for bucket in buckets.get('Buckets', []):
            bucket_name = bucket['Name']
            bucket_info = {'bucket': bucket}
            
            try:
                # 기본 암호화 설정 확인
                try:
                    encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                    bucket_info['encryption'] = encryption.get('ServerSideEncryptionConfiguration', {})
                except s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                    bucket_info['encryption'] = None
                except Exception as e:
                    bucket_info['encryption_error'] = str(e)
                
                bucket_details.append(bucket_info)
                
            except Exception as e:
                bucket_info['error'] = str(e)
                bucket_details.append(bucket_info)
        
        return {'buckets': bucket_details}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        수집된 데이터를 분석하여 결과를 생성합니다.
        
        Args:
            collected_data: 수집된 데이터
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        bucket_details = collected_data.get('buckets', [])
        resources = []
        
        for bucket_info in bucket_details:
            bucket = bucket_info.get('bucket', {})
            bucket_name = bucket.get('Name', '')
            creation_date = bucket.get('CreationDate', '').strftime('%Y-%m-%d') if bucket.get('CreationDate') else ''
            
            if 'error' in bucket_info:
                # 오류가 있는 경우
                resources.append(create_resource_result(
                    resource_id=bucket_name,
                    resource_name=bucket_name,
                    status=RESOURCE_STATUS_UNKNOWN,
                    status_text='확인 불가',
                    advice=f'버킷 정보를 가져오는 중 오류가 발생했습니다: {bucket_info["error"]}',
                    creation_date=creation_date,
                    encryption_type='확인 불가'
                ))
                continue
            
            # 암호화 설정 분석
            encryption = bucket_info.get('encryption')
            encryption_error = bucket_info.get('encryption_error')
            
            if encryption_error:
                resources.append(create_resource_result(
                    resource_id=bucket_name,
                    resource_name=bucket_name,
                    status=RESOURCE_STATUS_UNKNOWN,
                    status_text='확인 불가',
                    advice=f'버킷의 암호화 설정을 확인하는 중 오류가 발생했습니다: {encryption_error}',
                    creation_date=creation_date,
                    encryption_type='확인 불가'
                ))
                continue
            
            # 암호화 설정 분석
            has_encryption = encryption is not None
            encryption_type = None
            kms_key_id = None
            
            if has_encryption:
                rules = encryption.get('Rules', [])
                for rule in rules:
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
                status = RESOURCE_STATUS_PASS
                status_text = 'SSE-S3 암호화'
                advice = '버킷에 SSE-S3 암호화가 설정되어 있습니다. 더 강력한 보안을 위해 SSE-KMS 암호화를 고려하세요.'
            elif encryption_type == 'aws:kms':
                status = RESOURCE_STATUS_PASS
                status_text = 'SSE-KMS 암호화'
                advice = '버킷에 SSE-KMS 암호화가 적절하게 설정되어 있습니다.'
            else:
                status = RESOURCE_STATUS_WARNING
                status_text = '알 수 없는 암호화'
                advice = f'버킷에 알 수 없는 암호화 유형({encryption_type})이 설정되어 있습니다. SSE-S3 또는 SSE-KMS 암호화를 사용하세요.'
            
            # 표준화된 리소스 결과 생성
            resources.append(create_resource_result(
                resource_id=bucket_name,
                resource_name=bucket_name,
                status=status,
                status_text=status_text,
                advice=advice,
                creation_date=creation_date,
                encryption_type=encryption_type if encryption_type else 'None'
            ))
        
        # 결과 분류
        passed_buckets = [b for b in resources if b['status'] == RESOURCE_STATUS_PASS]
        warning_buckets = [b for b in resources if b['status'] == RESOURCE_STATUS_WARNING]
        failed_buckets = [b for b in resources if b['status'] == RESOURCE_STATUS_FAIL]
        unknown_buckets = [b for b in resources if b['status'] == RESOURCE_STATUS_UNKNOWN]
        
        return {
            'resources': resources,
            'passed_buckets': passed_buckets,
            'warning_buckets': warning_buckets,
            'failed_buckets': failed_buckets,
            'unknown_buckets': unknown_buckets,
            'problem_count': len(warning_buckets) + len(failed_buckets),
            'total_count': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        분석 결과를 바탕으로 권장사항을 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            List[str]: 권장사항 목록
        """
        recommendations = []
        failed_buckets = analysis_result.get('failed_buckets', [])
        
        # 암호화가 필요한 버킷 찾기
        if failed_buckets:
            recommendations.append(f'{len(failed_buckets)}개 버킷에 기본 암호화 설정이 필요합니다. (영향받는 버킷: {", ".join([b["name"] for b in failed_buckets])})')
        
        # 일반적인 권장사항
        recommendations.append('모든 S3 버킷에 기본 암호화를 설정하세요.')
        recommendations.append('중요한 데이터를 저장하는 버킷에는 SSE-KMS 암호화를 사용하세요.')
        
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """
        분석 결과를 바탕으로 메시지를 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            str: 결과 메시지
        """
        total_count = analysis_result.get('total_count', 0)
        failed_buckets = analysis_result.get('failed_buckets', [])
        warning_buckets = analysis_result.get('warning_buckets', [])
        passed_buckets = analysis_result.get('passed_buckets', [])
        
        if len(failed_buckets) > 0:
            return f'{total_count}개 버킷 중 {len(failed_buckets)}개에 기본 암호화 설정이 필요합니다.'
        elif len(warning_buckets) > 0:
            return f'{total_count}개 버킷 중 {len(warning_buckets)}개에 암호화 설정 개선이 필요합니다.'
        else:
            return f'모든 버킷({len(passed_buckets)}개)이 적절하게 암호화되어 있습니다.'
    
    def run(self) -> Dict[str, Any]:
        """
        검사를 실행하고 결과를 반환합니다.
        
        Returns:
            Dict[str, Any]: 검사 결과
        """
        try:
            # 데이터 수집
            collected_data = self.collect_data()
            
            # 데이터 분석
            analysis_result = self.analyze_data(collected_data)
            
            # 권장사항 생성
            recommendations = self.generate_recommendations(analysis_result)
            
            # 메시지 생성
            message = self.create_message(analysis_result)
            
            # 상태 결정
            problem_count = analysis_result.get('problem_count', 0)
            if problem_count > 0:
                status = STATUS_WARNING
            else:
                status = STATUS_OK
            
            # 리소스 목록 가져오기
            resources = analysis_result.get('resources', [])
            
            # 통일된 결과 생성
            result = create_unified_check_result(
                status=status,
                message=message,
                resources=resources,
                recommendations=recommendations,
                check_id=self.check_id
            )
            
            return result
        except Exception as e:
            return create_error_result(f'암호화 설정 검사 중 오류가 발생했습니다: {str(e)}')

def run(role_arn=None) -> Dict[str, Any]:
    """
    S3 버킷의 암호화 설정을 검사하고 보안 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    check = EncryptionCheck()
    return check.run()