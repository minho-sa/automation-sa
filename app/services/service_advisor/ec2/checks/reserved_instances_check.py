import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_FAIL
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class ReservedInstancesCheck(BaseEC2Check):
    """EC2 예약 인스턴스 현황 및 만료 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ec2_reserved_instances_check'
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        ec2_client = create_boto3_client('ec2', role_arn=role_arn)
        
        # 예약 인스턴스 조회
        reserved_instances = ec2_client.describe_reserved_instances(
            Filters=[{'Name': 'state', 'Values': ['active']}]
        )
        
        # 실행 중인 인스턴스 조회
        running_instances = ec2_client.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        return {
            'reserved_instances': reserved_instances['ReservedInstances'],
            'running_instances': running_instances
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        now = datetime.utcnow()
        
        # 실행 중인 인스턴스 타입별 카운트
        running_instance_types = {}
        for reservation in collected_data['running_instances']['Reservations']:
            for instance in reservation['Instances']:
                instance_type = instance['InstanceType']
                az = instance['Placement']['AvailabilityZone']
                key = f"{instance_type}_{az}"
                running_instance_types[key] = running_instance_types.get(key, 0) + 1
        
        # 예약 인스턴스가 없는 경우
        if not collected_data['reserved_instances']:
            # 실행 중인 인스턴스가 있는지 확인
            total_running = sum(running_instance_types.values())
            if total_running > 0:
                resources.append(create_resource_result(
                    resource_id='no-reserved-instances',
                    status=RESOURCE_STATUS_WARNING,
                    advice=f'현재 {total_running}개의 인스턴스가 실행 중이지만 예약 인스턴스가 없습니다. 비용 절감을 위해 예약 인스턴스 구매를 고려하세요.',
                    status_text='RI 없음',
                    ri_id='N/A',
                    instance_type='N/A',
                    instance_count=0,
                    days_until_expiry=0,
                    utilization=0,
                    availability_zone='N/A'
                ))
                problem_count += 1
            else:
                resources.append(create_resource_result(
                    resource_id='no-instances',
                    status=RESOURCE_STATUS_PASS,
                    advice='실행 중인 인스턴스와 예약 인스턴스가 모두 없습니다.',
                    status_text='인스턴스 없음',
                    ri_id='N/A',
                    instance_type='N/A',
                    instance_count=0,
                    days_until_expiry=0,
                    utilization=0,
                    availability_zone='N/A'
                ))
        else:
            # 예약 인스턴스 분석
            for ri in collected_data['reserved_instances']:
                ri_id = ri['ReservedInstancesId']
                instance_type = ri['InstanceType']
                instance_count = ri['InstanceCount']
                end_date = ri['End']
                az = ri['AvailabilityZone']
                
                # 만료까지 남은 일수 계산
                if end_date.tzinfo is not None:
                    end_date = end_date.replace(tzinfo=None)
                days_until_expiry = (end_date - now).days
                
                # 상태 결정
                status = RESOURCE_STATUS_PASS
                status_text = '정상'
                advice = f'예약 인스턴스가 정상적으로 운영되고 있습니다. (만료: {days_until_expiry}일 후)'
                
                # 만료 임박 검사 (30일 이내)
                if days_until_expiry <= 30:
                    status = RESOURCE_STATUS_WARNING if days_until_expiry > 7 else RESOURCE_STATUS_FAIL
                    status_text = '만료 임박' if days_until_expiry > 7 else '만료 위험'
                    advice = f'예약 인스턴스가 {days_until_expiry}일 후 만료됩니다. 갱신 또는 새로운 예약을 고려하세요.'
                    problem_count += 1
                
                # 사용률 검사
                key = f"{instance_type}_{az}"
                running_count = running_instance_types.get(key, 0)
                utilization = (running_count / instance_count) * 100 if instance_count > 0 else 0
                
                if utilization < 80 and status == RESOURCE_STATUS_PASS:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '저사용률'
                    advice = f'예약 인스턴스 사용률이 {utilization:.1f}%입니다. ({running_count}/{instance_count} 사용 중)'
                    problem_count += 1
                elif utilization >= 100:
                    status = RESOURCE_STATUS_WARNING
                    status_text = '초과 사용'
                    advice = f'실행 중인 인스턴스({running_count}개)가 예약 인스턴스({instance_count}개)보다 많습니다. 추가 예약을 고려하세요.'
                    problem_count += 1
                
                resources.append(create_resource_result(
                    resource_id=ri_id,
                    status=status,
                    advice=advice,
                    status_text=status_text,
                    ri_id=ri_id,
                    instance_type=instance_type,
                    instance_count=instance_count,
                    days_until_expiry=days_until_expiry,
                    utilization=utilization,
                    availability_zone=az
                ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '만료 예정인 예약 인스턴스를 미리 갱신하세요.',
            '사용률이 낮은 예약 인스턴스는 다른 인스턴스 타입으로 변경을 고려하세요.',
            '실행 중인 인스턴스가 예약보다 많은 경우 추가 예약을 검토하세요.',
            '정기적으로 예약 인스턴스 사용률을 모니터링하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        total = analysis_result['total_resources']
        problems = analysis_result['problem_count']
        
        if total == 0:
            return '예약 인스턴스와 실행 중인 인스턴스가 모두 없습니다.'
        elif problems > 0:
            return f'예약 인스턴스 관리에서 {problems}개 항목이 주의가 필요합니다.'
        else:
            return f'모든 예약 인스턴스가 적절히 관리되고 있습니다.'