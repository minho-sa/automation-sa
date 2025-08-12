import boto3
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    EBS 스냅샷의 퍼블릭 액세스 설정을 검사하고 보안 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # 모든 리전에서 스냅샷 검사
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_snapshots = []
        
        # 병렬로 모든 리전 검사
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_region = {
                executor.submit(_check_region_snapshots, region, role_arn): region 
                for region in regions
            }
            
            for future in as_completed(future_to_region):
                region_snapshots = future.result()
                all_snapshots.extend(region_snapshots)
        
        # 결과 분류
        public_snapshots = [s for s in all_snapshots if s['status'] == RESOURCE_STATUS_FAIL]
        private_snapshots = [s for s in all_snapshots if s['status'] == RESOURCE_STATUS_PASS]
        
        # 권장사항
        recommendations = [
            "퍼블릭 스냅샷을 즉시 프라이빗으로 변경하세요.",
            "스냅샷 생성 시 기본적으로 프라이빗 설정을 확인하세요.",
            "정기적으로 스냅샷 권한을 검토하세요.",
            "민감한 데이터가 포함된 스냅샷은 암호화를 활성화하세요.",
            "불필요한 스냅샷은 삭제하여 보안 위험을 줄이세요."
        ]
        
        # 결과 생성
        if public_snapshots:
            message = f"{len(all_snapshots)}개 스냅샷 중 {len(public_snapshots)}개가 퍼블릭으로 설정되어 있습니다."
            return create_unified_check_result(
                status=STATUS_ERROR,
                message=message,
                resources=all_snapshots,
                recommendations=recommendations
            )
        else:
            message = f"모든 스냅샷({len(all_snapshots)}개)이 프라이빗으로 안전하게 설정되어 있습니다."
            return create_unified_check_result(
                status=STATUS_OK,
                message=message,
                resources=all_snapshots,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'EBS 퍼블릭 스냅샷 검사 중 오류가 발생했습니다: {str(e)}')

def _check_region_snapshots(region: str, role_arn: str) -> List[Dict[str, Any]]:
    """특정 리전의 스냅샷 검사"""
    try:
        ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
        
        # 자신이 소유한 스냅샷만 조회
        response = ec2_client.describe_snapshots(OwnerIds=['self'])
        snapshots = response['Snapshots']
        
        snapshot_results = []
        
        for snapshot in snapshots:
            snapshot_id = snapshot['SnapshotId']
            
            # 스냅샷 권한 확인
            try:
                attrs = ec2_client.describe_snapshot_attribute(
                    SnapshotId=snapshot_id,
                    Attribute='createVolumePermission'
                )
                
                # 퍼블릭 권한 확인
                create_permissions = attrs.get('CreateVolumePermissions', [])
                is_public = any(perm.get('Group') == 'all' for perm in create_permissions)
                
                # Name 태그 추출
                snapshot_name = None
                for tag in snapshot.get('Tags', []):
                    if tag['Key'] == 'Name':
                        snapshot_name = tag['Value']
                        break
                
                # 스냅샷 크기 (GB)
                volume_size = snapshot.get('VolumeSize', 0)
                
                # 암호화 여부
                encrypted = snapshot.get('Encrypted', False)
                
                # 생성 날짜
                start_time = snapshot.get('StartTime')
                creation_date = start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A'
                
                # 상태 결정
                if is_public:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '퍼블릭 스냅샷'
                    if encrypted:
                        advice = f"스냅샷이 퍼블릭으로 설정되어 있습니다. 암호화되어 있지만 즉시 프라이빗으로 변경하세요."
                    else:
                        advice = f"스냅샷이 퍼블릭이며 암호화되지 않았습니다. 매우 위험하므로 즉시 프라이빗으로 변경하세요."
                else:
                    status = RESOURCE_STATUS_PASS
                    status_text = '프라이빗 스냅샷'
                    advice = "스냅샷이 안전하게 프라이빗으로 설정되어 있습니다."
                
                # 결과 생성
                snapshot_result = create_resource_result(
                    resource_id=snapshot_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot_name or '-',
                    region=region,
                    volume_size_gb=volume_size,
                    encrypted=encrypted,
                    creation_date=creation_date,
                    is_public=is_public
                )
                
                snapshot_results.append(snapshot_result)
                
            except Exception as e:
                # 권한 확인 실패 시
                snapshot_result = create_resource_result(
                    resource_id=snapshot_id,
                    status=RESOURCE_STATUS_UNKNOWN,
                    advice=f"스냅샷 권한 확인 중 오류가 발생했습니다: {str(e)}",
                    status_text='확인 불가',
                    snapshot_id=snapshot_id,
                    region=region
                )
                snapshot_results.append(snapshot_result)
        
        return snapshot_results
        
    except Exception as e:
        print(f"리전 {region}에서 스냅샷 검사 중 오류: {str(e)}")
        return []