import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.common.unified_result import (
    create_resource_result, RESOURCE_STATUS_PASS, RESOURCE_STATUS_WARNING
)
from app.services.service_advisor.ebs.checks.base_ebs_check import BaseEBSCheck

class OverprovisionedVolumesCheck(BaseEBSCheck):
    """과다 프로비저닝된 EBS 볼륨 검사"""
    
    def __init__(self, session=None):
        self.session = session or boto3.Session()
        self.check_id = 'ebs_overprovisioned_volumes_check'
    
    def _collect_region_data(self, region: str, role_arn: str) -> Dict[str, Any]:
        """
        특정 리전의 EBS 볼륨 데이터를 수집합니다.
        """
        try:
            ec2_client = create_boto3_client('ec2', region_name=region, role_arn=role_arn)
            cloudwatch_client = create_boto3_client('cloudwatch', region_name=region, role_arn=role_arn)
            
            # 연결된 EBS 볼륨 조회 (gp2, gp3, io1, io2만 대상)
            volumes = ec2_client.describe_volumes(
                Filters=[
                    {'Name': 'state', 'Values': ['in-use']},
                    {'Name': 'volume-type', 'Values': ['gp2', 'gp3', 'io1', 'io2']}
                ]
            )
            
            region_volumes = []
            for volume in volumes['Volumes']:
                volume['Region'] = region
                
                # CloudWatch 메트릭 조회 (지난 14일간 IOPS 사용률)
                try:
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(days=14)
                    
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
                        Period=3600,  # 1시간
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
                        Period=3600,  # 1시간
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
            iops = volume.get('Iops', 0)
            
            # 볼륨 이름 태그 찾기
            volume_name = '-'
            for tag in volume.get('Tags', []):
                if tag['Key'] == 'Name':
                    volume_name = tag['Value']
                    break
            
            # 프로비저닝된 IOPS 계산
            if volume_type == 'gp2':
                provisioned_iops = min(size * 3, 16000)  # gp2: 3 IOPS per GB, max 16,000
            elif volume_type == 'gp3':
                provisioned_iops = iops if iops > 0 else 3000  # gp3: default 3,000 IOPS
            elif volume_type in ['io1', 'io2']:
                provisioned_iops = iops  # io1/io2: 사용자 지정 IOPS
            else:
                provisioned_iops = 0
            
            # IOPS 메트릭 분석
            read_ops_metrics = volume.get('ReadOpsMetrics', [])
            write_ops_metrics = volume.get('WriteOpsMetrics', [])
            
            if not read_ops_metrics and not write_ops_metrics:
                # 메트릭이 없는 경우
                status = RESOURCE_STATUS_WARNING
                advice = f'EBS 볼륨({volume_id})의 IOPS 메트릭을 확인할 수 없습니다.'
                status_text = '메트릭 없음'
                max_iops_used = 'N/A'
                utilization_rate = 'N/A'
                problem_count += 1
            else:
                # 최대 IOPS 사용량 계산 (시간당)
                max_read_ops = max((dp.get('Sum', 0) / 3600 for dp in read_ops_metrics), default=0)
                max_write_ops = max((dp.get('Sum', 0) / 3600 for dp in write_ops_metrics), default=0)
                max_iops_used = max_read_ops + max_write_ops
                
                # IOPS 사용률 계산
                if provisioned_iops > 0:
                    utilization_rate = (max_iops_used / provisioned_iops) * 100
                else:
                    utilization_rate = 0
                
                if utilization_rate < 20 and provisioned_iops > 1000:  # 사용률 20% 미만이고 1000 IOPS 이상
                    status = RESOURCE_STATUS_WARNING
                    advice = f'EBS 볼륨({volume_id})이 과다 프로비저닝되었습니다. 프로비저닝: {provisioned_iops:.0f} IOPS, 최대 사용: {max_iops_used:.0f} IOPS (사용률: {utilization_rate:.1f}%)'
                    status_text = '과다 프로비저닝'
                    problem_count += 1
                else:
                    status = RESOURCE_STATUS_PASS
                    advice = f'EBS 볼륨({volume_id})이 적절히 프로비저닝되었습니다. 사용률: {utilization_rate:.1f}%'
                    status_text = '적절한 프로비저닝'
            
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
                provisioned_iops=int(provisioned_iops),
                max_iops_used=int(max_iops_used) if isinstance(max_iops_used, (int, float)) else max_iops_used,
                utilization_rate=f"{utilization_rate:.1f}%" if isinstance(utilization_rate, (int, float)) else utilization_rate,
                region=volume.get('Region', 'N/A')
            ))
        
        return {
            'resources': resources,
            'problem_count': problem_count,
            'total_resources': len(resources)
        }
    
    def generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        recommendations = [
            '과다 프로비저닝된 볼륨의 IOPS를 실제 사용량에 맞게 조정하세요.',
            'gp3 볼륨으로 변경하여 IOPS를 독립적으로 조정하세요.',
            'io1/io2 볼륨의 경우 프로비저닝된 IOPS를 줄이세요.',
            '정기적으로 IOPS 사용률을 모니터링하여 최적화하세요.'
        ]
        return recommendations
    
    def create_message(self, analysis_result: Dict[str, Any]) -> str:
        problems = analysis_result['problem_count']
        if problems > 0:
            return f'{problems}개의 과다 프로비저닝된 EBS 볼륨이 발견되어 불필요한 IOPS 비용이 발생하고 있습니다.'
        else:
            return '모든 EBS 볼륨이 적절히 프로비저닝되어 있습니다.'