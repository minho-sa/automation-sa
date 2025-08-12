import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    CloudTrail 활성화 상태를 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        cloudtrail_client = create_boto3_client('cloudtrail', role_arn=role_arn)
        
        # CloudTrail 목록 가져오기
        trails = []
        paginator = cloudtrail_client.get_paginator('list_trails')
        for page in paginator.paginate():
            trails.extend(page['Trails'])
        
        trail_analysis = []
        
        for trail in trails:
            trail_name = trail['Name']
            trail_arn = trail['TrailARN']
            
            # Trail 상세 정보 가져오기
            trail_status = cloudtrail_client.get_trail_status(Name=trail_name)
            trail_details = cloudtrail_client.describe_trails(trailNameList=[trail_name])['trailList'][0]
            
            # 상태 분석
            is_logging = trail_status['IsLogging']
            is_multi_region = trail_details.get('IsMultiRegionTrail', False)
            include_global_events = trail_details.get('IncludeGlobalServiceEvents', False)
            
            status = RESOURCE_STATUS_PASS
            status_text = '정상'
            advice = 'CloudTrail이 올바르게 구성되어 있습니다.'
            
            if not is_logging:
                status = RESOURCE_STATUS_FAIL
                status_text = '로깅 비활성화'
                advice = 'CloudTrail 로깅이 비활성화되어 있습니다. 보안 감사를 위해 로깅을 활성화하세요.'
            elif not is_multi_region:
                status = RESOURCE_STATUS_FAIL
                status_text = '단일 리전'
                advice = '다중 리전 CloudTrail을 활성화하여 모든 리전의 이벤트를 기록하세요.'
            elif not include_global_events:
                status = RESOURCE_STATUS_FAIL
                status_text = '글로벌 이벤트 미포함'
                advice = '글로벌 서비스 이벤트를 포함하도록 설정하세요.'
            
            trail_result = create_resource_result(
                resource_id=trail_arn,
                status=status,
                advice=advice,
                status_text=status_text,
                trail_name=trail_name,
                trail_arn=trail_arn,
                region=trail_details.get('HomeRegion', 'N/A'),
                is_logging=is_logging,
                is_multi_region=is_multi_region,
                include_global_events=include_global_events,
                s3_bucket=trail_details.get('S3BucketName', 'N/A')
            )
            
            trail_analysis.append(trail_result)
        
        # 결과 분류
        active_trails = [t for t in trail_analysis if t['is_logging']]
        inactive_trails = [t for t in trail_analysis if not t['is_logging']]
        failed_trails = [t for t in trail_analysis if t['status'] == RESOURCE_STATUS_FAIL]
        
        # 권장사항 생성
        recommendations = [
            'CloudTrail을 활성화하여 모든 API 호출을 기록하세요.',
            '다중 리전 CloudTrail을 설정하여 모든 리전의 이벤트를 기록하세요.',
            '글로벌 서비스 이벤트를 포함하도록 설정하세요.',
            'CloudTrail 로그를 정기적으로 모니터링하고 분석하세요.'
        ]
        
        data = {
            'trails': trail_analysis,
            'active_trails': active_trails,
            'inactive_trails': inactive_trails,
            'failed_trails': failed_trails,
            'total_trails_count': len(trail_analysis),
            'resources': trail_analysis
        }
        
        # 전체 상태 결정
        if not trails:
            return create_check_result(
                status=STATUS_ERROR,
                message='CloudTrail이 설정되지 않았습니다.',
                data=data,
                recommendations=recommendations
            )
        elif failed_trails:
            return create_check_result(
                status=STATUS_WARNING,
                message=f'{len(trails)}개 CloudTrail 중 {len(failed_trails)}개에 문제가 있습니다.',
                data=data,
                recommendations=recommendations
            )
        else:
            return create_check_result(
                status=STATUS_OK,
                message=f'모든 CloudTrail({len(trails)}개)이 올바르게 구성되어 있습니다.',
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'CloudTrail 활성화 상태 확인 중 오류가 발생했습니다: {str(e)}')