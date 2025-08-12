import boto3
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client

RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_FAIL = 'fail'

from app.services.service_advisor.ebs.checks.base_ebs_check import BaseEBSCheck

class EBSEncryptionCheck(BaseEBSCheck):
    """EBS 볼륨 암호화 검사"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.check_id = 'ebs_encryption_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            volumes_response = ec2_client.describe_volumes()
            volumes = volumes_response['Volumes']
            
            for volume in volumes:
                volume['Region'] = region
            
            return {'volumes': volumes}
        except Exception as e:
            print(f"리전 {region}에서 EBS 데이터 수집 중 오류: {str(e)}")
            return {'volumes': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """EBS 볼륨 데이터 수집"""
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_volumes = []
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_volumes.extend(result['volumes'])
        
        return {'volumes': all_volumes}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        volumes = collected_data.get('volumes', [])
        
        if not volumes:
            return {
                'resources': [],
                'problem_count': 0,
                'total_resources': 0
            }
        
        for volume in volumes:
            volume_id = volume.get('VolumeId', '')
            encrypted = volume.get('Encrypted', False)
            region = volume.get('Region', 'N/A')
            
            # Name 태그 추출
            volume_name = None
            for tag in volume.get('Tags', []):
                if tag['Key'] == 'Name':
                    volume_name = tag['Value']
                    break
            
            resource_status = RESOURCE_STATUS_PASS
            status_text = '암호화됨'
            advice = 'EBS 볼륨이 암호화되어 있습니다.'
            
            if not encrypted:
                resource_status = RESOURCE_STATUS_FAIL
                status_text = '암호화 안됨'
                advice = 'EBS 볼륨이 암호화되지 않았습니다. 데이터 보호를 위해 암호화를 활성화하세요.'
                problem_count += 1
            
            resources.append({
                'id': volume_id,
                'status': resource_status,
                'advice': advice,
                'status_text': status_text,
                'volume_id': volume_id,
                'volume_name': volume_name or '-',
                'region': region
            })
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        return [
            '모든 EBS 볼륨에 암호화를 활성화하세요.',
            '계정 수준에서 기본 암호화를 설정하세요.',
            'KMS로 암호화 키를 관리하세요.',
            '기존 볼륨은 스냅샷을 통해 암호화된 볼륨으로 마이그레이션하세요.'
        ]
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        
        if total == 0:
            return 'EBS 볼륨이 없습니다.'
        elif problems > 0:
            return f'{total}개 EBS 볼륨 중 {problems}개가 암호화되지 않았습니다.'
        else:
            return f'모든 EBS 볼륨({total}개)이 암호화되어 있습니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """EBS 암호화 검사를 실행합니다."""
    import boto3
    session = boto3.Session()
    check = EBSEncryptionCheck(session=session)
    return check.run(role_arn=role_arn)