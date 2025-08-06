import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.common.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_FAIL
)
from app.services.service_advisor.alb.checks.base_alb_check import BaseALBCheck

class SSLCertificateCheck(BaseALBCheck):
    """ELB SSL/TLS 설정 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'alb_ssl_certificate_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        elbv2_client = create_boto3_client('elbv2', role_arn=role_arn)
        acm_client = create_boto3_client('acm', role_arn=role_arn)
        cloudfront_client = create_boto3_client('cloudfront', role_arn=role_arn)
        
        try:
            # ALB 목록 조회
            load_balancers = elbv2_client.describe_load_balancers()
            
            # 리스너 정보 조회
            listeners = {}
            for lb in load_balancers.get('LoadBalancers', []):
                lb_arn = lb['LoadBalancerArn']
                try:
                    listener_response = elbv2_client.describe_listeners(LoadBalancerArn=lb_arn)
                    listeners[lb_arn] = listener_response.get('Listeners', [])
                except Exception as e:
                    print(f"로드 밸런서 {lb_arn}의 리스너 조회 중 오류: {str(e)}")
                    listeners[lb_arn] = []
            
            # CloudFront 배포 조회
            cloudfront_distributions = {}
            try:
                cf_response = cloudfront_client.list_distributions()
                for dist in cf_response.get('DistributionList', {}).get('Items', []):
                    # ALB를 오리진으로 사용하는 CloudFront 찾기
                    for origin in dist.get('Origins', {}).get('Items', []):
                        domain_name = origin.get('DomainName', '')
                        # ALB DNS 이름과 매칭
                        for lb in load_balancers.get('LoadBalancers', []):
                            if lb.get('DNSName') in domain_name:
                                lb_arn = lb['LoadBalancerArn']
                                if lb_arn not in cloudfront_distributions:
                                    cloudfront_distributions[lb_arn] = []
                                
                                # CloudFront 배포 상세 정보 조회 (SSL 인증서 포함)
                                try:
                                    dist_config = cloudfront_client.get_distribution_config(Id=dist.get('Id'))
                                    viewer_cert = dist_config.get('DistributionConfig', {}).get('ViewerCertificate', {})
                                    
                                    cloudfront_distributions[lb_arn].append({
                                        'distribution_id': dist.get('Id'),
                                        'domain_name': dist.get('DomainName'),
                                        'status': dist.get('Status'),
                                        'viewer_protocol_policy': dist.get('DefaultCacheBehavior', {}).get('ViewerProtocolPolicy'),
                                        'ssl_support_method': viewer_cert.get('SSLSupportMethod'),
                                        'certificate_source': viewer_cert.get('CertificateSource'),
                                        'acm_certificate_arn': viewer_cert.get('ACMCertificateArn'),
                                        'cloudfront_default_certificate': viewer_cert.get('CloudFrontDefaultCertificate', False)
                                    })
                                except Exception as e:
                                    print(f"CloudFront 배포 {dist.get('Id')} 상세 조회 중 오류: {str(e)}")
                                    # 기본 정보만 저장
                                    cloudfront_distributions[lb_arn].append({
                                        'distribution_id': dist.get('Id'),
                                        'domain_name': dist.get('DomainName'),
                                        'status': dist.get('Status'),
                                        'viewer_protocol_policy': dist.get('DefaultCacheBehavior', {}).get('ViewerProtocolPolicy'),
                                        'ssl_support_method': None,
                                        'certificate_source': None,
                                        'acm_certificate_arn': None,
                                        'cloudfront_default_certificate': None
                                    })
            except Exception as e:
                print(f"CloudFront 배포 조회 중 오류: {str(e)}")
            
            # SSL 인증서 정보 조회
            certificates = {}
            try:
                cert_response = acm_client.list_certificates()
                for cert in cert_response.get('CertificateSummaryList', []):
                    cert_arn = cert['CertificateArn']
                    try:
                        cert_detail = acm_client.describe_certificate(CertificateArn=cert_arn)
                        certificates[cert_arn] = cert_detail['Certificate']
                    except Exception as e:
                        print(f"인증서 {cert_arn} 상세 조회 중 오류: {str(e)}")
                        certificates[cert_arn] = None
            except Exception as e:
                print(f"인증서 목록 조회 중 오류: {str(e)}")
            
            return {
                'load_balancers': load_balancers.get('LoadBalancers', []),
                'listeners': listeners,
                'certificates': certificates,
                'cloudfront_distributions': cloudfront_distributions
            }
        except Exception as e:
            print(f"ELB SSL 인증서 데이터 수집 중 오류 발생: {str(e)}")
            return {
                'load_balancers': [],
                'listeners': {},
                'certificates': {},
                'cloudfront_distributions': {}
            }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        load_balancers = collected_data.get('load_balancers', [])
        listeners = collected_data.get('listeners', {})
        certificates = collected_data.get('certificates', {})
        cloudfront_distributions = collected_data.get('cloudfront_distributions', {})
        
        for lb in load_balancers:
            lb_arn = lb['LoadBalancerArn']
            lb_name = lb['LoadBalancerName']
            lb_scheme = lb.get('Scheme', 'unknown')
            
            # 리스너 확인
            lb_listeners = listeners.get(lb_arn, [])
            https_listeners = [l for l in lb_listeners if l.get('Protocol') == 'HTTPS']
            http_listeners = [l for l in lb_listeners if l.get('Protocol') == 'HTTP']
            
            status = RESOURCE_STATUS_PASS
            status_text = 'SSL 설정 적절'
            advice = 'ELB의 SSL 설정이 적절합니다.'
            issues = []
            
            # CloudFront 사용 여부 확인
            has_cloudfront = lb_arn in cloudfront_distributions
            cf_info = cloudfront_distributions.get(lb_arn, [])
            
            # 인터넷 대면 ELB에서 HTTP만 사용하는 경우
            if lb_scheme == 'internet-facing':
                if http_listeners and not https_listeners:
                    if has_cloudfront:
                        # CloudFront SSL 설정 상세 확인
                        cf_https_enabled = any(
                            cf.get('viewer_protocol_policy') in ['redirect-to-https', 'https-only'] 
                            for cf in cf_info
                        )
                        
                        # CloudFront SSL 인증서 확인
                        cf_has_ssl_cert = False
                        cf_ssl_issues = []
                        
                        for cf in cf_info:
                            # CloudFront 기본 인증서 사용 여부 확인
                            if cf.get('cloudfront_default_certificate'):
                                cf_ssl_issues.append(f"CloudFront {cf.get('distribution_id')}가 기본 인증서를 사용하고 있습니다.")
                            elif cf.get('acm_certificate_arn'):
                                cf_has_ssl_cert = True
                            elif cf.get('certificate_source') == 'acm':
                                cf_has_ssl_cert = True
                        
                        if cf_https_enabled and cf_has_ssl_cert:
                            # CloudFront가 HTTPS를 처리하고 SSL 인증서가 있는 경우
                            status_text = 'CloudFront SSL 사용'
                        elif cf_https_enabled and not cf_has_ssl_cert:
                            status = RESOURCE_STATUS_WARNING
                            status_text = 'CloudFront SSL 인증서 미설정'
                            issues.append('CloudFront와 연결되어 있지만 CloudFront에 적절한 SSL 인증서가 설정되어 있지 않습니다.')
                            issues.extend(cf_ssl_issues)
                            problem_count += 1
                        elif not cf_https_enabled:
                            status = RESOURCE_STATUS_WARNING
                            status_text = 'CloudFront HTTPS 미설정'
                            issues.append('CloudFront와 연결되어 있지만 CloudFront에서 HTTPS 리다이렉트가 설정되지 않았습니다.')
                            problem_count += 1
                    else:
                        status = RESOURCE_STATUS_FAIL
                        status_text = 'HTTPS 미사용'
                        issues.append('인터넷 대면 ELB에서 HTTPS를 사용하지 않습니다.')
                        problem_count += 1
                elif http_listeners and https_listeners:
                    # HTTP에서 HTTPS로 리다이렉트 확인
                    has_redirect = False
                    for listener in http_listeners:
                        for action in listener.get('DefaultActions', []):
                            if action.get('Type') == 'redirect' and action.get('RedirectConfig', {}).get('Protocol') == 'HTTPS':
                                has_redirect = True
                                break
                    
                    if not has_redirect and not has_cloudfront:
                        status = RESOURCE_STATUS_WARNING
                        status_text = 'HTTP 리다이렉트 미설정'
                        issues.append('HTTP에서 HTTPS로 자동 리다이렉트가 설정되지 않았습니다.')
                        problem_count += 1
            
            # SSL 인증서 만료 확인
            for listener in https_listeners:
                for cert in listener.get('Certificates', []):
                    cert_arn = cert.get('CertificateArn')
                    if cert_arn in certificates:
                        cert_info = certificates[cert_arn]
                        if cert_info:
                            not_after = cert_info.get('NotAfter')
                            if not_after:
                                days_until_expiry = (not_after.replace(tzinfo=None) - datetime.now()).days
                                
                                if days_until_expiry <= 7:
                                    status = RESOURCE_STATUS_FAIL
                                    status_text = '인증서 만료 임박'
                                    issues.append(f'SSL 인증서가 {days_until_expiry}일 후 만료됩니다.')
                                    problem_count += 1
                                elif days_until_expiry <= 30:
                                    if status == RESOURCE_STATUS_PASS:
                                        status = RESOURCE_STATUS_WARNING
                                        status_text = '인증서 만료 주의'
                                    issues.append(f'SSL 인증서가 {days_until_expiry}일 후 만료됩니다. 갱신을 준비하세요.')
                                    problem_count += 1
            
            # SSL 정책 확인 (구버전 정책 사용 여부)
            for listener in https_listeners:
                ssl_policy = listener.get('SslPolicy', '')
                if ssl_policy and ('2016' in ssl_policy or '2015' in ssl_policy):
                    if status == RESOURCE_STATUS_PASS:
                        status = RESOURCE_STATUS_WARNING
                        status_text = '구버전 SSL 정책'
                    issues.append(f'구버전 SSL 정책({ssl_policy})을 사용하고 있습니다. 최신 정책으로 업데이트하세요.')
                    problem_count += 1
            
            # 메시지 생성
            if issues:
                advice = f'다음 SSL 관련 문제가 발견되었습니다: {" ".join(issues)}'
            elif has_cloudfront and http_listeners and not https_listeners and status == RESOURCE_STATUS_PASS:
                # CloudFront가 HTTPS를 처리하는 경우 정보성 메시지
                cf_domain = cf_info[0].get('domain_name', 'N/A') if cf_info else 'N/A'
                cf_cert_info = ''
                if cf_info:
                    cf = cf_info[0]
                    if cf.get('acm_certificate_arn'):
                        cf_cert_info = ' (ACM 인증서 사용)'
                    elif cf.get('cloudfront_default_certificate'):
                        cf_cert_info = ' (기본 인증서 사용)'
                advice = f'CloudFront를 통해 SSL이 처리되고 있습니다. (CloudFront: {cf_domain}{cf_cert_info})'
            
            resources.append(create_resource_result(
                resource_id=lb_name,
                status=status,
                advice=advice,
                status_text=status_text,
                alb_name=lb_name,
                scheme=lb_scheme,
                https_listeners=len(https_listeners),
                http_listeners=len(http_listeners),
                has_cloudfront=has_cloudfront,
                cloudfront_count=len(cf_info),
                issues=issues
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '외부에 노출된 ELB는 HTTPS를 사용하거나 CloudFront를 통해 HTTPS를 처리하세요.',
            'CloudFront를 사용하는 경우 CloudFront에서 HTTPS 리다이렉트를 설정하고 적절한 SSL 인증서를 설정하세요.',
            'CloudFront에서 기본 인증서 대신 ACM 인증서를 사용하여 보안을 강화하세요.',
            'CloudFront 없이 직접 노출되는 ELB는 HTTP에서 HTTPS로 리다이렉트를 설정하세요.',
            'SSL 인증서 만료일을 정기적으로 확인하고 자동 갱신을 설정하세요.',
            '최신 SSL 정책을 사용하여 보안을 강화하세요.',
            'ACM(AWS Certificate Manager)을 사용하여 인증서를 관리하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 ELB 중 {problems}개가 SSL 설정 개선이 필요합니다.'
        else:
            return f'모든 ELB({total}개)의 SSL 설정이 적절하거나 CloudFront를 통해 안전하게 관리되고 있습니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """
    ELB SSL 인증서 검사를 실행합니다.
    
    Args:
        role_arn: AWS 역할 ARN (선택 사항)
        
    Returns:
        Dict[str, Any]: 검사 결과
    """
    check = SSLCertificateCheck()
    return check.run(role_arn=role_arn)