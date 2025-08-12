import boto3
from typing import Dict, List, Any
from app.services.service_advisor.common.aws_client import AWSClient
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    EFS 파일 시스템의 전송 중 데이터 암호화 설정을 검사합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        aws_client = AWSClient()
        
        # 모든 리전에서 EFS 파일 시스템 수집
        ec2_client = aws_client.get_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
        
        # 파일 시스템 분석 결과
        filesystem_analysis = []
        
        for region in regions:
            try:
                efs_client = aws_client.get_client('efs', region_name=region, role_arn=role_arn)
                filesystems = efs_client.describe_file_systems()
            except Exception:
                continue
                
            for fs in filesystems.get('FileSystems', []):
                fs_id = fs.get('FileSystemId', 'Unknown')
                fs_name = fs.get('Name', '')
                creation_time = fs.get('CreationTime', '')
                lifecycle_state = fs.get('LifeCycleState', 'Unknown')
                encrypted = fs.get('Encrypted', False)
                
                # EFS 태그에서 Name 태그 찾기
                if not fs_name:
                    try:
                        tags_response = efs_client.describe_tags(FileSystemId=fs_id)
                        tags = tags_response.get('Tags', [])
                        for tag in tags:
                            if tag.get('Key') == 'Name':
                                fs_name = tag.get('Value', '')
                                break
                    except Exception:
                        pass
                
                # 이름이 없으면 "-" 사용
                if not fs_name:
                    fs_name = '-'
                
                # 마운트 타겟 정보 확인
                try:
                    mount_targets = efs_client.describe_mount_targets(FileSystemId=fs_id)
                    mount_target_count = len(mount_targets.get('MountTargets', []))
                except Exception:
                    mount_target_count = 0
                
                # 상태 결정
                status = RESOURCE_STATUS_FAIL
                status_text = '전송 중 데이터 암호화 미사용'
                advice = f'EFS 파일 시스템 {fs_id}에 전송 중 데이터 암호화가 설정되지 않았습니다. EFS 마운트 헬퍼를 사용하여 "-o tls" 옵션으로 TLS v1.2 암호화를 활성화하세요.'
                
                # 암호화된 파일 시스템의 경우 권장사항 제공
                if encrypted:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '전송 중 암호화 미설정'
                    advice = f'EFS 파일 시스템 {fs_id}에 저장 데이터 암호화는 활성화되어 있지만, 전송 중 데이터 암호화도 함께 사용하는 것을 권장합니다. 마운트 시 "-o tls" 옵션을 사용하세요.'
                
                # 표준화된 리소스 결과 생성
                fs_result = create_resource_result(
                    resource_id=fs_id,
                    resource_name=fs_name,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    filesystem_id=fs_id,
                    filesystem_name=fs_name,
                    region=region,
                    creation_time=creation_time.strftime('%Y-%m-%d') if creation_time else 'N/A',
                    lifecycle_state=lifecycle_state,
                    encrypted_at_rest=encrypted,
                    mount_target_count=mount_target_count
                )
                
                filesystem_analysis.append(fs_result)
        
        # 결과 분류
        passed_filesystems = [f for f in filesystem_analysis if f['status'] == RESOURCE_STATUS_PASS]
        warning_filesystems = [f for f in filesystem_analysis if f['status'] == RESOURCE_STATUS_WARNING]
        failed_filesystems = [f for f in filesystem_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        
        # 권장사항 생성
        recommendations = [
            'EFS 마운트 시 "-o tls" 옵션을 사용하여 data-in-transit 암호화를 활성화하세요.',
            'EFS 마운트 헬퍼(amazon-efs-utils)를 사용하여 TLS v1.2 암호화를 적용하세요.',
            'At-rest 암호화와 함께 data-in-transit 암호화를 모두 사용하여 완전한 데이터 보호를 구현하세요.',
            '중요한 데이터를 저장하는 EFS 파일 시스템에는 반드시 암호화를 적용하세요.'
        ]
        
        # 전체 상태 결정 및 결과 생성
        if len(failed_filesystems) > 0:
            message = f'{len(filesystem_analysis)}개 EFS 파일 시스템 중 {len(failed_filesystems)}개에 전송 중 데이터 암호화 설정이 필요합니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=filesystem_analysis,
                recommendations=recommendations
            )
        elif len(warning_filesystems) > 0:
            message = f'{len(filesystem_analysis)}개 EFS 파일 시스템 중 {len(warning_filesystems)}개에 전송 중 데이터 암호화 개선이 권장됩니다.'
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=filesystem_analysis,
                recommendations=recommendations
            )
        else:
            message = f'모든 EFS 파일 시스템({len(passed_filesystems)}개)이 적절하게 암호화되어 있습니다.'
            return create_unified_check_result(
                status=STATUS_OK,
                message=message,
                resources=filesystem_analysis,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'EFS 전송 중 데이터 암호화 검사 중 오류가 발생했습니다: {str(e)}')