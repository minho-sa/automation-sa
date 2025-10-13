import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ebs.checks.base_ebs_check import BaseEBSCheck

class LowUtilizationVolumesCheck(BaseEBSCheck):
    """활용도 낮은 EBS 볼륨 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ebs_low_utilization_volumes_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        """
        특정 리전의 EBS 볼륨 데이터를 수집합니다.
        """
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            cloudwatch_client = create_boto3_client('cloudwatch', region_name=region, role_arn=role_arn)
            
            # 연결된 EBS 볼륨 조회
            volumes = ec2_client.describe_volumes(
                Filters=[{'Name': 'state', 'Values': ['in-use']}]
            )
            
            region_volumes = []
            for volume in volumes['Volumes']:
                volume['Region'] = region
                
                # CloudWatch 메트릭 조회 (지난 7일간 IOPS)
                try:
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(days=7)
                    
                    # VolumeReadOps 메트릭
                    read_ops = cloudwatch_client.get_metric_statistics(
                        Namespace='AWS/EBS',
                        MetricName='VolumeReadOps',
                        Dimensions=[
                            {
                                'Name': 'VolumeId',
                                'Value': volume['VolumeId']
                            }
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,  # 1일
                        Statistics=['Sum']
                    )
                    
                    # VolumeWriteOps 메트릭
                    write_ops = cloudwatch_client.get_metric_statistics(
                        Namespace='AWS/EBS',
                        MetricName='VolumeWriteOps',
                        Dimensions=[
                            {
                                'Name': 'VolumeId',
                                'Value': volume['VolumeId']
                            }
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,  # 1일
                        Statistics=['Sum']
                    )
                    
                    volume['ReadOpsMetrics'] = read_ops['Datapoints']
                    volume['WriteOpsMetrics'] = write_ops['Datapoints']
                    
                except Exception as e:
                    print(f"CloudWatch 메트릭 조회 오류: {str(e)}")
                    volume['ReadOpsMetrics'] = []
                    volume['WriteOpsMetrics'] = []
                
                region_volumes.append(volume)
            
            return {
                'volumes': region_volumes
            }
        except Exception as e:
            print(f"리전 {region}에서 EBS 데이터 수집 중 오류: {str(e)}")
            return {'volumes': []}
    
    def collect_data(self, role_arn=None) -> Dict[str, Any]:
        # 모든 리전 목록 가져오기
        ec2_default = create_boto3_client('ec2', role_arn=role_arn)
        regions = [region['RegionName'] for region in ec2_default.describe_regions()['Regions']]
        
        all_volumes = []
        
        # 병렬 처리로 리전별 데이터 수집 (10개 리전 동시 처리)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_region = {executor.submit(self._collect_region_data, region, role_arn): region for region in regions}
            
            for future in as_completed(future_to_region):
                result = future.result()
                all_volumes.extend(result['volumes'])
        
        return {
            'volumes': all_volumes
        }
    
    def analyze_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        resources = []
        problem_count = 0
        
        # EBS 볼륨 검사
        for volume in collected_data['volumes']:
            volume_id = volume.get('VolumeId', 'N/A')
            volume_type = volume.get('VolumeType', 'N/A')
            size = volume.get('Size', 0)
            
            # 볼륨 이름 태그 찾기
            volume_name = '-'
            for tag in volume.get('Tags', []):
                if tag['Key'] == 'Name':
                    volume_name = tag['Value']
                    break
            
            # IOPS 메트릭 분석
            read_ops_metrics = volume.get('ReadOpsMetrics', [])
            write_ops_metrics = volume.get('WriteOpsMetrics', [])
            
            if not read_ops_metrics and not write_ops_metrics:
                # 메트릭이 없는 경우
                status = RESOURCE_STATUS_WARNING
                advice = f'EBS 볼륨({volume_id})의 사용률 메트릭을 확인할 수 없습니다. 사용 현황을 점검해주세요.'
                status_text = '메트릭 없음'
                avg_daily_ops = 'N/A'
                problem_count += 1
            else:
                # 일일 평균 IOPS 계산
                total_read_ops = sum(dp.get('Sum', 0) for dp in read_ops_metrics)
                total_write_ops = sum(dp.get('Sum', 0) for dp in write_ops_metrics)
                total_ops = total_read_ops + total_write_ops
                days_with_data = max(len(read_ops_metrics), len(write_ops_metrics))
                avg_daily_ops = total_ops / days_with_data if days_with_data > 0 else 0
                
                if avg_daily_ops < 100:  # 일일 평균 IOPS가 100 미만
                    status = RESOURCE_STATUS_WARNING
                    advice = f'EBS 볼륨({volume_id})의 활용도가 낮습니다. 일일 평균 IOPS: {avg_daily_ops:.0f}'
                    status_text = '활용도 낮음'
                    problem_count += 1
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = f'EBS 볼륨({volume_id})이 정상적으로 사용되고 있습니다. 일일 평균 IOPS: {avg_daily_ops:.0f}'
                    status_text = '정상 사용'
            
            resources.append(create_resource_result(
                resource_id=volume_id,
                status=status,
                advice=advice,
                status_text=status_text,
                volume_name=volume_name,
                volume_id=volume_id,
                resource_type='EBS Volume',
                volume_type=volume_type,
                size=size,
                avg_daily_ops=int(avg_daily_ops) if isinstance(avg_daily_ops, (int, float)) else avg_daily_ops,
                region=volume.get('Region', 'N/A')
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '활용도가 낮은 EBS 볼륨을 스냅샷으로 백업 후 삭제하세요.',
            '더 작은 크기의 볼륨으로 다운사이징을 고려하세요.',
            'gp3 볼륨 타입으로 변경하여 비용을 절약하세요.',
            '정기적으로 EBS 볼륨 사용률을 모니터링하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{problems}개의 활용도 낮은 EBS 볼륨이 발견되어 불필요한 비용이 발생하고 있습니다.'
        else:
            return '모든 EBS 볼륨이 적절히 사용되고 있습니다.'