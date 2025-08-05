import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run(role_arn=None) -> Dict[str, Any]:
    """
    RDS 인스턴스의 공개 액세스 설정을 검사하고 개선 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        rds_client = create_boto3_client('rds', role_arn=role_arn)
        
        # RDS 인스턴스 목록 가져오기
        instances = rds_client.describe_db_instances()
        
        # 인스턴스 분석 결과
        instance_analysis = []
        
        for instance in instances.get('DBInstances', []):
            instance_id = instance['DBInstanceIdentifier']
            engine = instance['Engine']
            publicly_accessible = instance.get('PubliclyAccessible', False)
            
            # 태그 가져오기
            try:
                tags_response = rds_client.list_tags_for_resource(
                    ResourceName=instance['DBInstanceArn']
                )
                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
            except Exception:
                tags = {}
            
            # 공개 액세스 설정 분석
            status = RESOURCE_STATUS_PASS
            advice = None
            status_text = None
            
            if publicly_accessible:
                status = RESOURCE_STATUS_FAIL
                status_text = '인터넷 노출 위험'
                advice = f'⚠️ 위험: {instance_id}가 인터넷에서 직접 접근 가능합니다. 즉시 조치 필요:\n1. AWS 콘솔에서 인스턴스 수정 → "퍼블릭 액세스 가능" 비활성화\n2. 프라이빗 서브넷으로 이동 (다운타임 발생)\n3. 보안그룹에서 0.0.0.0/0 규칙 제거\n4. 외부 접근 시 VPN/Direct Connect 사용'
            else:
                status_text = '보안 설정 양호'
                advice = f'{instance_id}는 VPC 내부에서만 접근 가능하도록 안전하게 구성되어 있습니다.'
            
            # 표준화된 리소스 결과 생성
            instance_result = create_resource_result(
                resource_id=instance_id,
                status=status,
                advice=advice,
                status_text=status_text,
                instance_id=instance_id,
                engine=engine,
                publicly_accessible=publicly_accessible
            )
            
            instance_analysis.append(instance_result)
        
        # 결과 분류
        passed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_PASS]
        failed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_FAIL]
        
        # 개선 필요 인스턴스 카운트
        improvement_needed_count = len(failed_instances)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 위험한 공개 액세스 인스턴스 경고
        if failed_instances:
            recommendations.append(f'🚨 긴급: {len(failed_instances)}개 DB가 인터넷에 노출되어 해킹 위험 존재 (대상: {", ".join([i["instance_id"] for i in failed_instances])})')
            recommendations.append('즉시 조치: AWS 콘솔 → RDS → 인스턴스 선택 → 수정 → "퍼블릭 액세스 가능" 체크 해제')
        
        # 실용적인 보안 강화 방안  
        recommendations.append('외부 접근이 필요한 경우: VPN 연결 또는 AWS Direct Connect 사용 (인터넷 직접 노출 금지)')
        recommendations.append('보안그룹 점검: 0.0.0.0/0 (모든 IP) 허용 규칙 제거하고 특정 IP/CIDR만 허용')
        recommendations.append('DB 서브넷 그룹을 프라이빗 서브넷으로만 구성하여 물리적 격리')
        
        # 데이터 준비
        data = {
            'instances': instance_analysis,
            'passed_instances': passed_instances,
            'failed_instances': failed_instances,
            'improvement_needed_count': improvement_needed_count,
            'total_instances_count': len(instance_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if improvement_needed_count > 0:
            message = f'🚨 보안 위험: {len(instance_analysis)}개 DB 중 {improvement_needed_count}개가 인터넷에서 직접 접근 가능 (해킹 위험 높음)'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 DB({len(passed_instances)}개)가 VPC 내부에서만 접근 가능하도록 안전하게 구성됨'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'공개 액세스 설정 검사 중 오류가 발생했습니다: {str(e)}')