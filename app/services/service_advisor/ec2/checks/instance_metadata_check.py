import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    EC2 인스턴스의 메타데이터 서비스 설정을 검사하여 IMDSv2 사용 여부를 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        ec2 = create_boto3_client('ec2')
        
        # 실행 중인 인스턴스 정보 수집
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        # 인스턴스 메타데이터 설정 분석
        instance_analysis = []
        imdsv1_count = 0
        
        for reservation in instances.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                
                # 인스턴스 메타데이터 설정 확인
                metadata_options = instance.get('MetadataOptions', {})
                http_tokens = metadata_options.get('HttpTokens', 'optional')
                http_endpoint = metadata_options.get('HttpEndpoint', 'enabled')
                
                # IMDSv2 사용 여부 확인
                is_imdsv2_required = http_tokens == 'required'
                is_metadata_enabled = http_endpoint == 'enabled'
                
                # 태그 정보 수집
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                name = tags.get('Name', 'N/A')
                
                # IMDSv1 사용 인스턴스 카운트
                if is_metadata_enabled and not is_imdsv2_required:
                    imdsv1_count += 1
                
                # 분석 결과 저장
                instance_analysis.append({
                    'instance_id': instance_id,
                    'name': name,
                    'instance_type': instance_type,
                    'http_tokens': http_tokens,
                    'http_endpoint': http_endpoint,
                    'is_imdsv2_required': is_imdsv2_required,
                    'is_metadata_enabled': is_metadata_enabled
                })
        
        # 결과 생성
        if imdsv1_count > 0:
            return {
                'status': 'warning',
                'data': {
                    'instances': instance_analysis,
                    'imdsv1_count': imdsv1_count,
                    'total_count': len(instance_analysis)
                },
                'recommendations': [
                    'IMDSv2를 필수로 설정하여 SSRF 취약점으로부터 보호하세요.',
                    '모든 인스턴스에 IMDSv2를 적용하기 위한 계획을 수립하세요.',
                    '새로운 인스턴스 시작 시 IMDSv2를 필수로 설정하는 정책을 구현하세요.'
                ],
                'message': f'{len(instance_analysis)}개의 인스턴스 중 {imdsv1_count}개가 IMDSv1을 허용하고 있습니다.'
            }
        elif not instance_analysis:
            return {
                'status': 'info',
                'data': {
                    'instances': []
                },
                'recommendations': [],
                'message': '실행 중인 인스턴스가 없습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {
                    'instances': instance_analysis,
                    'imdsv1_count': 0,
                    'total_count': len(instance_analysis)
                },
                'recommendations': [],
                'message': '모든 인스턴스가 IMDSv2를 필수로 설정하고 있습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'인스턴스 메타데이터 설정 검사 중 오류가 발생했습니다: {str(e)}'
        }