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
    CloudTrail 로그 파일 검증 설정을 확인합니다.
    
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
            trail_details = cloudtrail_client.describe_trails(trailNameList=[trail_name])['trailList'][0]
            
            # 로그 파일 검증 설정 확인
            log_file_validation_enabled = trail_details.get('LogFileValidationEnabled', False)
            
            status = RESOURCE_STATUS_PASS
            status_text = '검증 활성화'
            advice = '로그 파일 무결성 검증이 활성화되어 있습니다.'
            
            if not log_file_validation_enabled:
                status = RESOURCE_STATUS_FAIL
                status_text = '검증 비활성화'
                advice = '로그 파일 무결성 검증을 활성화하여 로그 변조를 방지하세요.'
            
            trail_result = create_resource_result(
                resource_id=trail_arn,
                status=status,
                advice=advice,
                status_text=status_text,
                trail_name=trail_name,
                trail_arn=trail_arn,
                region=trail_details.get('HomeRegion', 'N/A'),
                log_file_validation_enabled=log_file_validation_enabled,
                s3_bucket=trail_details.get('S3BucketName', 'N/A')
            )
            
            trail_analysis.append(trail_result)
        
        # 결과 분류
        validated_trails = [t for t in trail_analysis if t['log_file_validation_enabled']]
        unvalidated_trails = [t for t in trail_analysis if not t['log_file_validation_enabled']]
        
        # 권장사항 생성
        recommendations = [
            'CloudTrail 로그 파일 무결성 검증을 활성화하세요.',
            '로그 파일 검증을 통해 로그 변조를 탐지할 수 있습니다.',
            '정기적으로 로그 파일 무결성을 확인하세요.',
            '로그 파일 검증 실패 시 즉시 조사하세요.'
        ]
        
        data = {
            'trails': trail_analysis,
            'validated_trails': validated_trails,
            'unvalidated_trails': unvalidated_trails,
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
        elif unvalidated_trails:
            return create_check_result(
                status=STATUS_WARNING,
                message=f'{len(trails)}개 CloudTrail 중 {len(unvalidated_trails)}개에서 로그 파일 검증이 비활성화되어 있습니다.',
                data=data,
                recommendations=recommendations
            )
        else:
            return create_check_result(
                status=STATUS_OK,
                message=f'모든 CloudTrail({len(trails)}개)에서 로그 파일 검증이 활성화되어 있습니다.',
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'CloudTrail 로그 파일 검증 확인 중 오류가 발생했습니다: {str(e)}')