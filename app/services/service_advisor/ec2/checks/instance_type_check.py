"""
EC2 인스턴스 타입 최적화 검사
"""
import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_UNKNOWN,
    create_unified_check_result, create_resource_result
)
from app.services.service_advisor.ec2.checks.base_ec2_check import BaseEC2Check

class InstanceTypeCheck(BaseEC2Check):
    """EC2 인스턴스 타입 최적화 검사 클래스"""
    
    def __init__(self):
        self.check_id = 'ec2-instance-type'
    
    def collect_data(self) -> Dict[str, Any]:
        """
        EC2 인스턴스 및 CloudWatch 메트릭 데이터를 수집합니다.
        
        Returns:
            Dict[str, Any]: 수집된 데이터
        """
        ec2 = create_boto3_client('ec2')
        cloudwatch = create_boto3_client('cloudwatch')
        
        # 실행 중인 인스턴스 정보 수집
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        # 현재 시간 설정
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=14)  # 2주 데이터 분석
        
        return {
            'instances': instances,
            'cloudwatch': cloudwatch,
            'start_time': start_time,
            'end_time': end_time
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        수집된 데이터를 분석하여 인스턴스 최적화 결과를 생성합니다.
        
        Args:
            collected_data: 수집된 데이터
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        instances = collected_data['instances']
        cloudwatch = collected_data['cloudwatch']
        start_time = collected_data['start_time']
        end_time = collected_data['end_time']
        
        # 인스턴스 분석 결과
        instance_analysis = []
        
        for reservation in instances.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                
                # 인스턴스 이름 태그 가져오기
                instance_name = "N/A"
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                
                # CPU 사용률 데이터 가져오기
                try:
                    cpu_response = cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1시간 간격
                        Statistics=['Average', 'Maximum']
                    )
                    
                    datapoints = cpu_response.get('Datapoints', [])
                    
                    if datapoints:
                        avg_cpu = sum(point['Average'] for point in datapoints) / len(datapoints)
                        max_cpu = max(point['Maximum'] for point in datapoints) if datapoints else 0
                        
                        # 인스턴스 타입 최적화 분석
                        status = RESOURCE_STATUS_PASS  # 기본값은 통과
                        advice = None
                        status_text = None
                        
                        if avg_cpu < 10 and max_cpu < 40:
                            status = RESOURCE_STATUS_FAIL
                            status_text = '최적화 필요'
                            advice = f'CPU 사용률이 낮습니다(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%). 이 인스턴스는 과다 프로비저닝되어 있습니다.'
                        elif avg_cpu > 80 or max_cpu > 90:
                            status = RESOURCE_STATUS_FAIL
                            status_text = '최적화 필요'
                            advice = f'CPU 사용률이 높습니다(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%). 이 인스턴스는 리소스 제약을 받고 있습니다.'
                        else:
                            status_text = '최적화됨'
                            advice = f'CPU 사용률(평균: {round(avg_cpu, 2)}%, 최대: {round(max_cpu, 2)}%)이 적절한 범위(10-80%) 내에 있습니다.'
                        
                        # 인스턴스 결과 생성
                        instance_result = create_resource_result(
                            resource_id=instance_id,
                            resource_name=instance_name,
                            status=status,
                            status_text=status_text,
                            advice=advice
                        )
                        
                        instance_analysis.append(instance_result)
                    else:
                        # 데이터 없음 결과 생성
                        status_text = '데이터 부족'
                        advice = '이 인스턴스에 대한 충분한 CloudWatch 메트릭 데이터가 없습니다. 최근에 시작되었거나 메트릭 수집이 활성화되지 않았을 수 있습니다.'
                        
                        instance_result = create_resource_result(
                            resource_id=instance_id,
                            resource_name=instance_name,
                            status=RESOURCE_STATUS_UNKNOWN,
                            status_text=status_text,
                            advice=advice
                        )
                        
                        instance_analysis.append(instance_result)
                        
                except Exception as e:
                    # 오류 결과 생성
                    status_text = '오류'
                    advice = f'이 인스턴스의 메트릭 데이터를 가져오는 중 오류가 발생했습니다. 권한 문제 또는 API 호출 실패가 원인일 수 있습니다.'
                    
                    instance_result = create_resource_result(
                        resource_id=instance_id,
                        resource_name=instance_name,
                        status='error',
                        status_text=status_text,
                        advice=advice
                    )
                    
                    instance_analysis.append(instance_result)
        
        # 결과 분류
        passed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_PASS]
        failed_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_FAIL]
        unknown_instances = [i for i in instance_analysis if i['status'] == RESOURCE_STATUS_UNKNOWN or i['status'] == 'error']
        
        # 최적화 필요 인스턴스 카운트
        optimization_needed_count = len(failed_instances)
        
        return {
            'resources': instance_analysis,
            'passed_instances': passed_instances,
            'failed_instances': failed_instances,
            'unknown_instances': unknown_instances,
            'problem_count': optimization_needed_count,
            'total_count': len(instance_analysis)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        분석 결과를 바탕으로 권장사항을 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            List[str]: 권장사항 목록
        """
        # 리소스 검사 결과와 상관없이 일관된 권장사항 제공
        recommendations = [
            'CPU 사용률이 10% 미만인 인스턴스는 더 작은 인스턴스 타입으로 변경하여 비용을 절감하세요.',
            'CPU 사용률이 80% 이상인 인스턴스는 더 큰 인스턴스 타입으로 변경하여 성능을 개선하세요.',
            '예약 인스턴스 또는 Savings Plans를 고려하여 비용을 절감하세요.',
            '인스턴스 크기 조정 시 CPU 외에도 메모리, 네트워크, 디스크 I/O 등 다른 성능 지표도 함께 고려하세요.'
        ]
        
        return recommendations
        
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        """
        분석 결과를 바탕으로 메시지를 생성합니다.
        
        Args:
            analysis_result: 분석 결과
            
        Returns:
            str: 결과 메시지
        """
        optimization_needed_count = analysis_result['problem_count']
        total_instances_count = analysis_result['total_count']
        
        if optimization_needed_count > 0:
            return f'{total_instances_count}개 인스턴스 중 {optimization_needed_count}개가 최적화가 필요합니다.'
        else:
            return f'모든 인스턴스({total_instances_count}개)가 적절한 크기로 구성되어 있습니다.'

def run() -> Dict[str, Any]:
    """
    인스턴스 타입 최적화 검사를 실행합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    check = InstanceTypeCheck()
    return check.run()