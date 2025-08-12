import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
# 상수 정의
RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_FAIL = 'fail'
from app.services.service_advisor.acm.checks.base_acm_check import BaseACMCheck

class CertificateExpiryCheck(BaseACMCheck):
    """ACM 인증서 만료 검사"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.check_id = 'acm_certificate_expiry_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """모든 리전에서 ACM 인증서 데이터 수집"""
        try:
            certificates = []
            
            # 모든 리전 목록 가져오기
            if role_arn:
                sts_client = self.session.client('sts')
                assumed_role = sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName='ACMCertificateExpiryCheck'
                )
                credentials = assumed_role['Credentials']
                ec2_client = boto3.client(
                    'ec2',
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
            else:
                ec2_client = self.session.client('ec2')
            
            # 모든 리전 목록 가져오기
            regions_response = ec2_client.describe_regions()
            regions = [region['RegionName'] for region in regions_response['Regions']]
            
            # 각 리전에서 인증서 조회
            for region in regions:
                try:
                    # 리전별 ACM 클라이언트 생성
                    if role_arn:
                        acm_client = boto3.client(
                            'acm',
                            region_name=region,
                            aws_access_key_id=credentials['AccessKeyId'],
                            aws_secret_access_key=credentials['SecretAccessKey'],
                            aws_session_token=credentials['SessionToken']
                        )
                    else:
                        acm_client = self.session.client('acm', region_name=region)
                    
                    # 인증서 목록 조회
                    paginator = acm_client.get_paginator('list_certificates')
                    for page in paginator.paginate():
                        for cert_summary in page['CertificateSummaryList']:
                            cert_arn = cert_summary['CertificateArn']
                            
                            # 인증서 상세 정보 조회
                            try:
                                cert_detail = acm_client.describe_certificate(CertificateArn=cert_arn)
                                cert_info = cert_detail['Certificate']
                                
                                certificates.append({
                                    'CertificateArn': cert_arn,
                                    'DomainName': cert_info.get('DomainName', 'N/A'),
                                    'Status': cert_info.get('Status', 'UNKNOWN'),
                                    'NotAfter': cert_info.get('NotAfter'),
                                    'Type': cert_info.get('Type', 'UNKNOWN'),
                                    'Region': region,
                                    'SubjectAlternativeNames': cert_info.get('SubjectAlternativeNames', [])
                                })
                            except Exception as e:
                                print(f"인증서 상세 정보 조회 실패 {cert_arn}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"리전 {region} ACM 조회 실패: {str(e)}")
                    continue
            
            return {'certificates': certificates}
            
        except Exception as e:
            print(f"ACM 데이터 수집 중 오류 발생: {str(e)}")
            return {'certificates': []}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        certificates = collected_data.get('certificates', [])
        
        # 인증서가 없는 경우에도 결과 반환
        if not certificates:
            return {
                'resources': [],
                'problem_count': 0,
                'total_resources': 0
            }
        
        for cert in certificates:
            cert_arn = cert.get('CertificateArn', '')
            domain_name = cert.get('DomainName', 'N/A')
            status = cert.get('Status', 'UNKNOWN')
            not_after = cert.get('NotAfter')
            
            resource_status = RESOURCE_STATUS_PASS
            status_text = '정상'
            advice = '인증서가 정상 상태입니다.'
            issues = []
            
            if status != 'ISSUED':
                resource_status = RESOURCE_STATUS_FAIL
                status_text = '상태 이상'
                issues.append(f'인증서 상태가 {status}입니다.')
                problem_count += 1
            
            days_until_expiry = None
            if not_after:
                days_until_expiry = (not_after.replace(tzinfo=None) - datetime.now()).days
                
                if days_until_expiry <= 7:
                    resource_status = RESOURCE_STATUS_FAIL
                    status_text = '만료 임박'
                    issues.append(f'인증서가 {days_until_expiry}일 후 만료됩니다.')
                    problem_count += 1
                elif days_until_expiry <= 30:
                    if resource_status == RESOURCE_STATUS_PASS:
                        resource_status = RESOURCE_STATUS_WARNING
                        status_text = '만료 주의'
                    issues.append(f'인증서가 {days_until_expiry}일 후 만료됩니다.')
                    problem_count += 1
            
            if issues:
                advice = f'다음 문제가 발견되었습니다: {" ".join(issues)}'
            
            resources.append({
                'id': cert_arn.split('/')[-1] if cert_arn else domain_name,
                'status': resource_status,
                'advice': advice,
                'status_text': status_text,
                'certificate_arn': cert_arn,
                'certificate_id': cert_arn.split('/')[-1] if cert_arn else 'N/A',
                'domain_name': domain_name,
                'certificate_status': status,
                'certificate_type': cert.get('Type', 'N/A'),
                'region': cert.get('Region', 'N/A'),
                'expiry_date': not_after.strftime('%Y-%m-%d') if not_after else 'N/A',
                'days_until_expiry': days_until_expiry if not_after else None,
                'subject_alternative_names': cert.get('SubjectAlternativeNames', [])
            })
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        return [
            'ACM 인증서의 만료일을 정기적으로 모니터링하세요.',
            '만료 30일 전에 인증서 갱신을 준비하세요.',
            'ACM 자동 갱신 기능을 활용하세요.'
        ]
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        
        if total == 0:
            return 'ACM에 등록된 인증서가 없습니다.'
        elif problems > 0:
            return f'{total}개 인증서 중 {problems}개가 주의가 필요합니다.'
        else:
            return f'모든 인증서({total}개)가 정상 상태입니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """
    ACM 인증서 만료 검사를 실행합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    import boto3
    session = boto3.Session()
    check = CertificateExpiryCheck(session=session)
    return check.run(role_arn=role_arn)