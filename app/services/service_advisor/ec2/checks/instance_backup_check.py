import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class InstanceBackupCheck(BaseEC2Check):
    """EC2 인스턴스 백업(스냅샷) 상태 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_instance_backup_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        """특정 리전의 인스턴스와 스냅샷 데이터를 수집합니다."""
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            
            instances = ec2_client.describe_instances()
            snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])
            
            return {
                'reservations': instances['Reservations'],
                'snapshots': snapshots['Snapshots'],
                'region': region
            }
        except Exception as e:
            print(f"리전 {region}에서 데이터 수집 중 오류: {str(e)}")
            return {'reservations': [], 'snapshots': [], 'region': region}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        # 모든 리전 목록 가져오기
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_reservations = []
        all_snapshots = []
        
        # 병렬 처리로 리전별 데이터 수집
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                
                # 각 인스턴스에 리전 정보 추가
                for reservation in result['reservations']:
                    for instance in reservation['Instances']:
                        instance['Region'] = result['region']
                
                all_reservations.extend(result['reservations'])
                all_snapshots.extend(result['snapshots'])
        
        return {
            'reservations': all_reservations,
            'snapshots': all_snapshots
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        now = datetime.utcnow()
        recent_threshold = now - timedelta(days=7)  # 7일
        
        # 최근 스냅샷 매핑
        recent_snapshots = {}
        for snapshot in collected_data['snapshots']:
            volume_id = snapshot.get('VolumeId')
            start_time = snapshot['StartTime'].replace(tzinfo=None)
            if start_time > recent_threshold:
                if volume_id not in recent_snapshots or start_time > recent_snapshots[volume_id]:
                    recent_snapshots[volume_id] = start_time
        
        for reservation in collected_data['reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                
                if instance_state == 'terminated':
                    continue
                
                instance_name = '-'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                # 인스턴스의 볼륨 확인
                has_recent_backup = False
                for bdm in instance.get('BlockDeviceMappings', []):
                    volume_id = bdm.get('Ebs', {}).get('VolumeId')
                    if volume_id and volume_id in recent_snapshots:
                        has_recent_backup = True
                        break
                
                if not has_recent_backup:
                    status = RESOURCE_STATUS_WARNING
                    advice = '최근 7일 내 백업(스냅샷)이 없습니다. 정기적인 백업을 설정하세요.'
                    status_text = '백업 없음'
                    problem_count += 1
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = '최근 백업이 존재합니다.'
                    status_text = '백업 있음'
                
                resources.append(create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    instance_name=instance_name,
                    region=instance.get('Region', 'N/A'),
                    has_recent_backup=has_recent_backup
                ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = []
        recommendations = [
            'AWS Backup으로 자동 백업을 설정하세요.',
            '중요한 인스턴스는 일일 스냅샷을 생성하세요.',
            '정기적으로 백업 복원 테스트를 수행하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{total}개 인스턴스 중 {problems}개에 최근 백업이 없습니다.'
        else:
            return f'모든 인스턴스({total}개)에 최근 백업이 존재합니다.'