import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client

RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_FAIL = 'fail'

from app.services.service_advisor.ebs.checks.base_ebs_check import BaseEBSCheck

class UnusedVolumesCheck(BaseEBSCheck):
    """사용하지 않는 EBS 볼륨 검사"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.check_id = 'unused_volumes_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """EBS 볼륨 데이터 수집"""
        try:
            ec2_client = create_boto3_client('ec2', role_arn=role_arn)
            volumes_response = ec2_client.describe_volumes()
            volumes = volumes_response['Volumes']
            
            # 리전 정보 추가
            current_region = ec2_client.meta.region_name
            for volume in volumes:
                volume['Region'] = current_region
            
            print(f"사용하지 않는 EBS 볼륨 검사: {len(volumes)}개 볼륨 발견 (리전: {current_region})")
            return {'volumes': volumes}
        except Exception as e:
            print(f"EBS 데이터 수집 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'volumes': []}
    
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
            state = volume.get('State', '')
            attachments = volume.get('Attachments', [])
            region = volume.get('Region', 'N/A')
            
            # Name 태그 추출
            volume_name = None
            for tag in volume.get('Tags', []):
                if tag['Key'] == 'Name':
                    volume_name = tag['Value']
                    break
            
            resource_status = RESOURCE_STATUS_PASS
            status_text = '사용 중'
            advice = 'EBS 볼륨이 인스턴스에 연결되어 사용 중입니다.'
            
            # 사용하지 않는 볼륨 검사
            if state == 'available' and len(attachments) == 0:
                resource_status = RESOURCE_STATUS_WARNING
                status_text = '사용 안함'
                advice = 'EBS 볼륨이 어떤 인스턴스에도 연결되지 않았습니다. 불필요한 비용이 발생할 수 있습니다.'
                problem_count += 1
            elif state == 'error':
                resource_status = RESOURCE_STATUS_FAIL
                status_text = '오류 상태'
                advice = 'EBS 볼륨이 오류 상태입니다. 확인이 필요합니다.'
                problem_count += 1
            
            # 연결된 인스턴스 정보
            attached_instances = []
            for attachment in attachments:
                instance_id = attachment.get('InstanceId', 'N/A')
                device = attachment.get('Device', 'N/A')
                attached_instances.append(f"{instance_id} ({device})")
            
            resources.append({
                'id': volume_id,
                'status': resource_status,
                'advice': advice,
                'status_text': status_text,
                'volume_id': volume_id,
                'volume_name': volume_name or '-',
                'region': region,
                'size': volume.get('Size', 0),
                'volume_type': volume.get('VolumeType', 'N/A'),
                'state': state,
                'availability_zone': volume.get('AvailabilityZone', 'N/A'),
                'attached_instances': ', '.join(attached_instances) if attached_instances else '연결 안됨',
                'create_time': volume.get('CreateTime', '').strftime('%Y-%m-%d %H:%M:%S') if volume.get('CreateTime') else 'N/A'
            })
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        return [
            '사용하지 않는 EBS 볼륨을 정기적으로 확인하고 삭제하세요.',
            '중요한 데이터가 있는 경우 스냅샷을 생성한 후 볼륨을 삭제하세요.',
            'CloudWatch를 통해 볼륨 사용량을 모니터링하세요.',
            '태그를 활용하여 볼륨의 용도를 명확히 관리하세요.'
        ]
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        
        if total == 0:
            return 'EBS 볼륨이 없습니다.'
        elif problems > 0:
            return f'{total}개 EBS 볼륨 중 {problems}개가 사용되지 않고 있습니다.'
        else:
            return f'모든 EBS 볼륨({total}개)이 사용 중입니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """사용하지 않는 EBS 볼륨 검사를 실행합니다."""
    import boto3
    session = boto3.Session()
    check = UnusedVolumesCheck(session=session)
    return check.run(role_arn=role_arn)