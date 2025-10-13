import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.rds.checks.base_rds_check import BaseRDSCheck

class IdleDBInstancesCheck(BaseRDSCheck):
    """유휴 RDS DB 인스턴스 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'rds_idle_db_instances_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        """
        특정 리전의 RDS 인스턴스 데이터를 수집합니다.
        """
        try:
            rds_client = create_boto3_client('rds', region_name=region, role_arn=role_arn)
            cloudwatch_client = create_boto3_client('cloudwatch', region_name=region, role_arn=role_arn)
            
            # RDS 인스턴스 조회
            db_instances = rds_client.describe_db_instances()
            region_instances = []
            
            for instance in db_instances['DBInstances']:
                if instance['DBInstanceStatus'] == 'available':
                    instance['Region'] = region
                    
                    # CloudWatch 메트릭 조회 (지난 7일간 연결 수)
                    try:
                        end_time = datetime.utcnow()
                        start_time = end_time - timedelta(days=7)
                        
                        metrics = cloudwatch_client.get_metric_statistics(
                            Namespace='AWS/RDS',
                            MetricName='DatabaseConnections',
                            Dimensions=[
                                {
                                    'Name': 'DBInstanceIdentifier',
                                    'Value': instance['DBInstanceIdentifier']
                                }
                            ],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=86400,  # 1일
                            Statistics=['Average', 'Maximum']
                        )
                        
                        instance['ConnectionMetrics'] = metrics['Datapoints']
                    except Exception as e:
                        print(f"CloudWatch 메트릭 조회 오류: {str(e)}")
                        instance['ConnectionMetrics'] = []
                    
                    region_instances.append(instance)
            
            return {
                'db_instances': region_instances
            }
        except Exception as e:
            print(f"리전 {region}에서 RDS 데이터 수집 중 오류: {str(e)}")
            return {'db_instances': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        # 모든 리전 목록 가져오기
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_db_instances = []
        
        # 병렬 처리로 리전별 데이터 수집 (10개 리전 동시 처리)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_db_instances.extend(result['db_instances'])
        
        return {
            'db_instances': all_db_instances
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        # RDS 인스턴스 검사
        for instance in collected_data['db_instances']:
            db_identifier = instance.get('DBInstanceIdentifier', 'N/A')
            db_class = instance.get('DBInstanceClass', 'N/A')
            engine = instance.get('Engine', 'N/A')
            
            # 연결 메트릭 분석
            connection_metrics = instance.get('ConnectionMetrics', [])
            
            if not connection_metrics:
                # 메트릭이 없는 경우 경고
                status = RESOURCE_STATUS_WARNING
                advice = f'RDS 인스턴스({db_identifier})의 연결 메트릭을 확인할 수 없습니다. 사용 현황을 점검해주세요.'
                status_text = '메트릭 없음'
                problem_count += 1
            else:
                # 평균 연결 수 계산
                avg_connections = sum(dp.get('Average', 0) for dp in connection_metrics) / len(connection_metrics)
                max_connections = max(dp.get('Maximum', 0) for dp in connection_metrics)
                
                if avg_connections < 1 and max_connections < 5:
                    # 유휴 상태로 판단
                    status = RESOURCE_STATUS_WARNING
                    advice = f'RDS 인스턴스({db_identifier})가 유휴 상태입니다. 평균 연결 수: {avg_connections:.1f}, 최대 연결 수: {max_connections:.0f}'
                    status_text = '유휴 상태'
                    problem_count += 1
                else:
                    # 정상 사용 중
                    status = RESOURCE_STATUS_PASS
                    advice = f'RDS 인스턴스({db_identifier})가 정상적으로 사용되고 있습니다. 평균 연결 수: {avg_connections:.1f}'
                    status_text = '사용 중'
            
            resources.append(create_resource_result(
                resource_id=db_identifier,
                status=status,
                advice=advice,
                status_text=status_text,
                db_identifier=db_identifier,
                resource_type='RDS Instance',
                db_class=db_class,
                engine=engine,
                avg_connections=round(avg_connections, 1) if connection_metrics else 'N/A',
                max_connections=int(max_connections) if connection_metrics else 'N/A',
                region=instance.get('Region', 'N/A')
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '유휴 상태의 RDS 인스턴스를 중지하거나 삭제하세요.',
            '스냅샷을 생성한 후 불필요한 인스턴스를 제거하세요.',
            '개발/테스트 환경의 경우 사용하지 않을 때 중지하세요.',
            '정기적으로 RDS 인스턴스 사용률을 모니터링하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{problems}개의 유휴 RDS 인스턴스가 발견되어 불필요한 비용이 발생하고 있습니다.'
        else:
            return '모든 RDS 인스턴스가 적절히 사용되고 있습니다.'