import boto3
from typing import Dict, List, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_unified_check_result, create_resource_result, create_error_result,
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    Windows Server 지원 종료로 인한 EC2 인스턴스 검사
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        # 모든 리전에서 EC2 인스턴스 검사
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_instances = []
        
        # 병렬로 모든 리전 검사
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_region = {
                executor.submit(_check_region_instances, region, role_arn): region 
                for region in regions
            }
            
            for future in as_completed(future_to_region):
                region_instances = future.result()
                all_instances.extend(region_instances)
        
        # 결과 분류
        eol_instances = [i for i in all_instances if i['status'] == RESOURCE_STATUS_FAIL]
        warning_instances = [i for i in all_instances if i['status'] == RESOURCE_STATUS_WARNING]
        safe_instances = [i for i in all_instances if i['status'] == RESOURCE_STATUS_PASS]
        
        # 권장사항
        recommendations = [
            "지원 종료된 Windows Server 인스턴스를 최신 버전으로 업그레이드하세요.",
            "Windows Server 2008/2008 R2는 즉시 업그레이드가 필요합니다.",
            "Windows Server 2012/2012 R2는 2023년 10월 지원 종료되었으므로 업그레이드하세요.",
            "업그레이드 전 애플리케이션 호환성을 테스트하세요.",
            "정기적으로 Windows Server 지원 일정을 확인하세요.",
            "가능한 경우 최신 Windows Server 2022 사용을 권장합니다."
        ]
        
        # 결과 생성
        if eol_instances:
            message = f"{len(all_instances)}개 Windows 인스턴스 중 {len(eol_instances)}개가 지원 종료된 버전을 사용하고 있습니다."
            return create_unified_check_result(
                status=STATUS_ERROR,
                message=message,
                resources=all_instances,
                recommendations=recommendations
            )
        elif warning_instances:
            message = f"{len(all_instances)}개 Windows 인스턴스 중 {len(warning_instances)}개가 곧 지원 종료될 예정입니다."
            return create_unified_check_result(
                status=STATUS_WARNING,
                message=message,
                resources=all_instances,
                recommendations=recommendations
            )
        else:
            message = f"모든 Windows 인스턴스({len(all_instances)}개)가 지원되는 버전을 사용하고 있습니다."
            return create_unified_check_result(
                status=STATUS_OK,
                message=message,
                resources=all_instances,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Windows Server 지원 종료 검사 중 오류가 발생했습니다: {str(e)}')

def _check_region_instances(region: str, role_arn: str) -> List[Dict[str, Any]]:
    """특정 리전의 Windows EC2 인스턴스 검사"""
    try:
        ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
        
        # Windows 인스턴스만 필터링
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'platform', 'Values': ['windows']},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
            ]
        )
        
        instance_results = []
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                
                # 인스턴스 정보 추출
                instance_type = instance.get('InstanceType', 'N/A')
                state = instance.get('State', {}).get('Name', 'N/A')
                launch_time = instance.get('LaunchTime')
                launch_date = launch_time.strftime('%Y-%m-%d %H:%M:%S') if launch_time else 'N/A'
                
                # Name 태그 추출
                instance_name = None
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                # Windows 버전 확인 (AMI 정보에서 추출)
                image_id = instance.get('ImageId', '')
                windows_version = _get_windows_version_from_ami(ec2_client, image_id)
                
                # 지원 상태 확인
                support_status = _check_windows_support_status(windows_version)
                
                # 상태 결정
                if support_status['status'] == 'eol':
                    status = RESOURCE_STATUS_FAIL
                    status_text = f'지원 종료 ({support_status["eol_date"]})'
                    advice = f"Windows {windows_version}은 {support_status['eol_date']}에 지원이 종료되었습니다. 즉시 최신 버전으로 업그레이드하세요."
                elif support_status['status'] == 'warning':
                    status = RESOURCE_STATUS_WARNING
                    status_text = f'지원 종료 예정 ({support_status["eol_date"]})'
                    advice = f"Windows {windows_version}은 {support_status['eol_date']}에 지원이 종료될 예정입니다. 업그레이드를 계획하세요."
                elif support_status['status'] == 'unknown':
                    status = RESOURCE_STATUS_WARNING
                    status_text = 'Windows 버전 확인 불가'
                    advice = f"Windows 버전을 확인할 수 없습니다. AMI 정보를 확인하고 지원되는 Windows Server 버전인지 검토하세요."
                else:
                    status = RESOURCE_STATUS_PASS
                    status_text = '지원 중'
                    advice = f"Windows {windows_version}은 현재 지원되는 버전입니다."
                
                # 결과 생성
                instance_result = create_resource_result(
                    resource_id=instance_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    instance_id=instance_id,
                    instance_name=instance_name or '-',
                    instance_type=instance_type,
                    region=region,
                    state=state,
                    windows_version=windows_version,
                    launch_date=launch_date,
                    eol_date=support_status.get('eol_date', 'N/A'),
                    support_status=support_status['status']
                )
                
                instance_results.append(instance_result)
        
        return instance_results
        
    except Exception as e:
        print(f"리전 {region}에서 Windows 인스턴스 검사 중 오류: {str(e)}")
        return []

def _get_windows_version_from_ami(ec2_client, image_id: str) -> str:
    """AMI 정보에서 Windows 버전 추출"""
    try:
        response = ec2_client.describe_images(ImageIds=[image_id])
        images = response.get('Images', [])
        
        if not images:
            return 'Unknown'
        
        image = images[0]
        image_name = image.get('Name', '').lower()
        description = image.get('Description', '').lower()
        
        # Windows 버전 매핑
        version_patterns = {
            'windows_server-2025': 'Server 2025',
            'windows_server-2022': 'Server 2022',
            'windows_server-2019': 'Server 2019',
            'windows_server-2016': 'Server 2016',
            'windows_server-2012-r2': 'Server 2012 R2',
            'windows_server-2012': 'Server 2012',
            'windows_server-2008-r2': 'Server 2008 R2',
            'windows_server-2008': 'Server 2008',
            '2025': 'Server 2025',
            '2022': 'Server 2022',
            '2019': 'Server 2019',
            '2016': 'Server 2016',
            '2012 r2': 'Server 2012 R2',
            '2012': 'Server 2012',
            '2008 r2': 'Server 2008 R2',
            '2008': 'Server 2008'
        }
        
        # 이미지 이름과 설명에서 버전 찾기
        for pattern, version in version_patterns.items():
            if pattern in image_name or pattern in description:
                return version
        
        # 디버깅을 위해 실제 AMI 정보 출력
        print(f"[DEBUG] AMI {image_id} 정보:")
        print(f"  Name: {image.get('Name', 'N/A')}")
        print(f"  Description: {image.get('Description', 'N/A')}")
        print(f"  Platform: {image.get('Platform', 'N/A')}")
        print(f"  Architecture: {image.get('Architecture', 'N/A')}")
        
        return 'Unknown'
        
    except Exception as e:
        print(f"AMI {image_id} 정보 조회 중 오류: {str(e)}")
        return 'Unknown'

def _check_windows_support_status(windows_version: str) -> Dict[str, str]:
    """Windows Server 버전별 지원 상태 확인"""
    current_date = datetime.now()
    
    # Windows Server 지원 종료 일정
    eol_dates = {
        'Server 2008': {'eol': datetime(2020, 1, 14), 'status': 'eol'},
        'Server 2008 R2': {'eol': datetime(2020, 1, 14), 'status': 'eol'},
        'Server 2012': {'eol': datetime(2023, 10, 10), 'status': 'eol'},
        'Server 2012 R2': {'eol': datetime(2023, 10, 10), 'status': 'eol'},
        'Server 2016': {'eol': datetime(2027, 1, 12), 'status': 'supported'},
        'Server 2019': {'eol': datetime(2029, 1, 9), 'status': 'supported'},
        'Server 2022': {'eol': datetime(2031, 10, 14), 'status': 'supported'},
        'Server 2025': {'eol': datetime(2034, 10, 14), 'status': 'supported'}
    }
    
    if windows_version in eol_dates:
        eol_info = eol_dates[windows_version]
        eol_date = eol_info['eol']
        
        if current_date > eol_date:
            return {
                'status': 'eol',
                'eol_date': eol_date.strftime('%Y-%m-%d')
            }
        elif (eol_date - current_date).days <= 365:  # 1년 이내 지원 종료
            return {
                'status': 'warning',
                'eol_date': eol_date.strftime('%Y-%m-%d')
            }
        else:
            return {
                'status': 'supported',
                'eol_date': eol_date.strftime('%Y-%m-%d')
            }
    
    # 알 수 없는 버전
    return {
        'status': 'unknown',
        'eol_date': 'Unknown'
    }