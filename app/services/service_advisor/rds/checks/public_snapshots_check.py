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
    RDS 스냅샷의 퍼블릭 액세스 설정을 검사하고 보안 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # 모든 리전에서 RDS 스냅샷 검사
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
            "퍼블릭 RDS 스냅샷을 즉시 프라이빗으로 변경하세요.",
            "스냅샷 생성 시 기본적으로 프라이빗 설정을 확인하세요.",
            "정기적으로 RDS 스냅샷 권한을 검토하세요.",
            "민감한 데이터베이스 스냅샷은 암호화를 활성화하세요.",
            "불필요한 스냅샷은 삭제하여 보안 위험을 줄이세요.",
            "스냅샷 공유가 필요한 경우 특정 AWS 계정과만 공유하세요."
        ]
        
        # 결과 생성
        if public_snapshots:
            message = f"{len(all_snapshots)}개 RDS 스냅샷 중 {len(public_snapshots)}개가 퍼블릭으로 설정되어 있습니다."
            return create_unified_check_result(
                status=STATUS_ERROR,
                message=message,
                resources=all_snapshots,
                recommendations=recommendations
            )
        else:
            message = f"모든 RDS 스냅샷({len(all_snapshots)}개)이 프라이빗으로 안전하게 설정되어 있습니다."
            return create_unified_check_result(
                status=STATUS_OK,
                message=message,
                resources=all_snapshots,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'RDS 퍼블릭 스냅샷 검사 중 오류가 발생했습니다: {str(e)}')

def _check_region_snapshots(region: str, role_arn: str) -> List[Dict[str, Any]]:
    """특정 리전의 RDS 스냅샷 검사"""
    try:
        rds_client = create_boto3_client('rds', region_name=region, role_arn=role_arn)
        
        snapshot_results = []
        
        # DB 스냅샷 검사
        db_snapshots = _check_db_snapshots(rds_client, region)
        snapshot_results.extend(db_snapshots)
        
        # 클러스터 스냅샷 검사
        cluster_snapshots = _check_cluster_snapshots(rds_client, region)
        snapshot_results.extend(cluster_snapshots)
        
        return snapshot_results
        
    except Exception as e:
        print(f"리전 {region}에서 RDS 스냅샷 검사 중 오류: {str(e)}")
        return []

def _check_db_snapshots(rds_client, region: str) -> List[Dict[str, Any]]:
    """DB 스냅샷 검사"""
    snapshot_results = []
    
    try:
        # 자신이 소유한 DB 스냅샷만 조회
        response = rds_client.describe_db_snapshots(SnapshotType='manual')
        snapshots = response['DBSnapshots']
        
        for snapshot in snapshots:
            snapshot_id = snapshot['DBSnapshotIdentifier']
            
            try:
                # 스냅샷 속성 확인
                attrs = rds_client.describe_db_snapshot_attributes(
                    DBSnapshotIdentifier=snapshot_id
                )
                
                # 퍼블릭 권한 확인
                attributes = attrs['DBSnapshotAttributesResult']['DBSnapshotAttributes']
                is_public = False
                
                for attr in attributes:
                    if attr['AttributeName'] == 'restore' and 'all' in attr.get('AttributeValues', []):
                        is_public = True
                        break
                
                # 스냅샷 정보
                db_instance_id = snapshot.get('DBInstanceIdentifier', 'N/A')
                engine = snapshot.get('Engine', 'N/A')
                engine_version = snapshot.get('EngineVersion', 'N/A')
                allocated_storage = snapshot.get('AllocatedStorage', 0)
                encrypted = snapshot.get('Encrypted', False)
                creation_time = snapshot.get('SnapshotCreateTime')
                creation_date = creation_time.strftime('%Y-%m-%d %H:%M:%S') if creation_time else 'N/A'
                
                # 상태 결정
                if is_public:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '퍼블릭 DB 스냅샷'
                    if encrypted:
                        advice = f"DB 스냅샷이 퍼블릭으로 설정되어 있습니다. 암호화되어 있지만 즉시 프라이빗으로 변경하세요."
                    else:
                        advice = f"DB 스냅샷이 퍼블릭이며 암호화되지 않았습니다. 매우 위험하므로 즉시 프라이빗으로 변경하세요."
                else:
                    status = RESOURCE_STATUS_PASS
                    status_text = '프라이빗 DB 스냅샷'
                    advice = "DB 스냅샷이 안전하게 프라이빗으로 설정되어 있습니다."
                
                # 결과 생성
                snapshot_result = create_resource_result(
                    resource_id=snapshot_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    snapshot_id=snapshot_id,
                    snapshot_type='DB 스냅샷',
                    db_instance_id=db_instance_id,
                    engine=engine,
                    engine_version=engine_version,
                    region=region,
                    allocated_storage_gb=allocated_storage,
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
                    advice=f"DB 스냅샷 권한 확인 중 오류가 발생했습니다: {str(e)}",
                    status_text='확인 불가',
                    snapshot_id=snapshot_id,
                    snapshot_type='DB 스냅샷',
                    region=region
                )
                snapshot_results.append(snapshot_result)
        
    except Exception as e:
        print(f"DB 스냅샷 조회 중 오류: {str(e)}")
    
    return snapshot_results

def _check_cluster_snapshots(rds_client, region: str) -> List[Dict[str, Any]]:
    """클러스터 스냅샷 검사"""
    snapshot_results = []
    
    try:
        # 자신이 소유한 클러스터 스냅샷만 조회
        response = rds_client.describe_db_cluster_snapshots(SnapshotType='manual')
        snapshots = response['DBClusterSnapshots']
        
        for snapshot in snapshots:
            snapshot_id = snapshot['DBClusterSnapshotIdentifier']
            
            try:
                # 스냅샷 속성 확인
                attrs = rds_client.describe_db_cluster_snapshot_attributes(
                    DBClusterSnapshotIdentifier=snapshot_id
                )
                
                # 퍼블릭 권한 확인
                attributes = attrs['DBClusterSnapshotAttributesResult']['DBClusterSnapshotAttributes']
                is_public = False
                
                for attr in attributes:
                    if attr['AttributeName'] == 'restore' and 'all' in attr.get('AttributeValues', []):
                        is_public = True
                        break
                
                # 스냅샷 정보
                db_cluster_id = snapshot.get('DBClusterIdentifier', 'N/A')
                engine = snapshot.get('Engine', 'N/A')
                engine_version = snapshot.get('EngineVersion', 'N/A')
                allocated_storage = snapshot.get('AllocatedStorage', 0)
                encrypted = snapshot.get('StorageEncrypted', False)
                creation_time = snapshot.get('SnapshotCreateTime')
                creation_date = creation_time.strftime('%Y-%m-%d %H:%M:%S') if creation_time else 'N/A'
                
                # 상태 결정
                if is_public:
                    status = RESOURCE_STATUS_FAIL
                    status_text = '퍼블릭 클러스터 스냅샷'
                    if encrypted:
                        advice = f"클러스터 스냅샷이 퍼블릭으로 설정되어 있습니다. 암호화되어 있지만 즉시 프라이빗으로 변경하세요."
                    else:
                        advice = f"클러스터 스냅샷이 퍼블릭이며 암호화되지 않았습니다. 매우 위험하므로 즉시 프라이빗으로 변경하세요."
                else:
                    status = RESOURCE_STATUS_PASS
                    status_text = '프라이빗 클러스터 스냅샷'
                    advice = "클러스터 스냅샷이 안전하게 프라이빗으로 설정되어 있습니다."
                
                # 결과 생성
                snapshot_result = create_resource_result(
                    resource_id=snapshot_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    snapshot_id=snapshot_id,
                    snapshot_type='클러스터 스냅샷',
                    db_cluster_id=db_cluster_id,
                    engine=engine,
                    engine_version=engine_version,
                    region=region,
                    allocated_storage_gb=allocated_storage,
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
                    advice=f"클러스터 스냅샷 권한 확인 중 오류가 발생했습니다: {str(e)}",
                    status_text='확인 불가',
                    snapshot_id=snapshot_id,
                    snapshot_type='클러스터 스냅샷',
                    region=region
                )
                snapshot_results.append(snapshot_result)
        
    except Exception as e:
        print(f"클러스터 스냅샷 조회 중 오류: {str(e)}")
    
    return snapshot_results