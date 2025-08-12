import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client

RESOURCE_STATUS_PASS = 'pass'
RESOURCE_STATUS_WARNING = 'warning'
RESOURCE_STATUS_FAIL = 'fail'

from app.services.service_advisor.ebs.checks.base_ebs_check import BaseEBSCheck

class SnapshotManagementCheck(BaseEBSCheck):
    """EBS 스냅샷 관리 검사"""
    
    def __init__(self, session=None):
        super().__init__(session)
        self.check_id = 'snapshot_management_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            snapshots_response = ec2_client.describe_snapshots(OwnerIds=['self'])
            snapshots = snapshots_response['Snapshots']
            
            for snapshot in snapshots:
                snapshot['Region'] = region
            
            return {'snapshots': snapshots}
        except Exception as e:
            print(f"리전 {region}에서 스냅샷 데이터 수집 중 오류: {str(e)}")
            return {'snapshots': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        """EBS 스냅샷 데이터 수집"""
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_snapshots = []
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_snapshots.extend(result['snapshots'])
        
        return {'snapshots': all_snapshots}
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        snapshots = collected_data.get('snapshots', [])
        
        if not snapshots:
            return {
                'resources': [],
                'problem_count': 0,
                'total_resources': 0
            }
        
        # 현재 시간
        now = datetime.now()
        old_threshold = now - timedelta(days=90)  # 90일 이상 된 스냅샷
        
        for snapshot in snapshots:
            snapshot_id = snapshot.get('SnapshotId', '')
            start_time = snapshot.get('StartTime')
            state = snapshot.get('State', '')
            region = snapshot.get('Region', 'N/A')
            
            # 스냅샷 나이 계산
            if start_time:
                if start_time.tzinfo is not None:
                    start_time = start_time.replace(tzinfo=None)
                age_days = (now - start_time).days
            else:
                age_days = 0
            
            # Name 태그 추출
            snapshot_name = None
            for tag in snapshot.get('Tags', []):
                if tag['Key'] == 'Name':
                    snapshot_name = tag['Value']
                    break
            
            resource_status = RESOURCE_STATUS_PASS
            status_text = '정상'
            advice = '스냅샷이 정상적으로 관리되고 있습니다.'
            issues = []
            
            # 상태 검사
            if state != 'completed':
                resource_status = RESOURCE_STATUS_FAIL
                status_text = '비정상 상태'
                issues.append(f'스냅샷 상태가 {state}입니다.')
                problem_count += 1
            
            # 오래된 스냅샷 검사
            elif age_days > 90:
                if resource_status == RESOURCE_STATUS_PASS:
                    resource_status = RESOURCE_STATUS_WARNING
                    status_text = '오래된 스냅샷'
                issues.append(f'스냅샷이 {age_days}일 전에 생성되었습니다.')
                problem_count += 1
            
            if issues:
                advice = f'다음 문제가 발견되었습니다: {" ".join(issues)}'
            
            resources.append({
                'id': snapshot_id,
                'status': resource_status,
                'advice': advice,
                'status_text': status_text,
                'snapshot_id': snapshot_id,
                'snapshot_name': snapshot_name or '-',
                'region': region
            })
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        return [
            '정기적으로 오래된 스냅샷을 검토하고 불필요한 것은 삭제하세요.',
            '스냅샷 생성을 자동화하여 일관된 백업 정책을 유지하세요.',
            '스냅샷에 적절한 태그를 추가하여 관리를 용이하게 하세요.',
            'Data Lifecycle Manager를 사용하여 스냅샷 수명주기를 관리하세요.'
        ]
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        
        if total == 0:
            return 'EBS 스냅샷이 없습니다.'
        elif problems > 0:
            return f'{total}개 스냅샷 중 {problems}개에 주의가 필요합니다.'
        else:
            return f'모든 스냅샷({total}개)이 정상적으로 관리되고 있습니다.'

def run(role_arn=None) -> Dict[str, Any]:
    """EBS 스냅샷 관리 검사를 실행합니다."""
    import boto3
    session = boto3.Session()
    check = SnapshotManagementCheck(session=session)
    return check.run(role_arn=role_arn)