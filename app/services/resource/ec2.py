import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytz
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ec2_recommendations.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_ec2_data(aws_access_key: str, aws_secret_key: str, region: str, collection_id: str = None) -> Dict:
    """EC2 인스턴스 데이터 수집"""
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.info(f"{log_prefix}Starting EC2 data collection")
    try:
        log_prefix = f"[{collection_id}] " if collection_id else ""
        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        
        cloudwatch = boto3.client(
            'cloudwatch',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )

        # 현재 시간 설정 - 시스템 시간 사용
        current_time = datetime.now(pytz.UTC)
        response = ec2_client.describe_instances()
        instances = []
        
        logger.info(f"{log_prefix}Found {len(response['Reservations'])} reservations")
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                logger.debug(f"{log_prefix}Processing instance {instance['InstanceId']}")
                
                # 기본 인스턴스 정보
                instance_data = {
                    'id': instance['InstanceId'],  # 변경: InstanceId -> id
                    'type': instance['InstanceType'],  # 변경: InstanceType -> type
                    'state': instance['State']['Name'],  # 변경: State -> state
                    'az': instance['Placement']['AvailabilityZone'],  # 변경: AvailabilityZone -> az
                    'launch_time': instance.get('LaunchTime'),
                    'state_transition_time': None,
                    'security_groups': [],
                    'tags': instance.get('Tags', []),
                    'cpu_metrics': [],
                    'cpu_analysis': {'low_usage_days': 0, 'high_usage_days': 0},
                    'network_metrics': {},
                    'volumes': []
                }

                # 보안 그룹 정보 수집
                logger.debug(f"{log_prefix}Collecting security group info for {instance['InstanceId']}")
                for sg in instance.get('SecurityGroups', []):
                    try:
                        sg_details = ec2_client.describe_security_groups(GroupIds=[sg['GroupId']])
                        if sg_details['SecurityGroups']:
                            sg_info = {
                                'group_id': sg['GroupId'],
                                'ip_ranges': [],
                                'ports': []
                            }
                            
                            for rule in sg_details['SecurityGroups'][0]['IpPermissions']:
                                for ip_range in rule.get('IpRanges', []):
                                    sg_info['ip_ranges'].append(ip_range.get('CidrIp'))
                                
                                if 'FromPort' in rule:
                                    sg_info['ports'].append(rule['FromPort'])
                            
                            instance_data['security_groups'].append(sg_info)
                    except Exception as e:
                        logger.error(f"{log_prefix}Error collecting security group info: {str(e)}")

                # 상태 변경 시간 수집
                if instance['State']['Name'] == 'stopped':
                    logger.debug(f"{log_prefix}Collecting state transition time for stopped instance {instance['InstanceId']}")
                    try:
                        # 시간 파라미터 설정
                        end_time = current_time
                        start_time = end_time - timedelta(days=30)
                        
                        status_checks = cloudwatch.get_metric_data(
                            MetricDataQueries=[{
                                'Id': 'status',
                                'MetricStat': {
                                    'Metric': {
                                        'Namespace': 'AWS/EC2',
                                        'MetricName': 'StatusCheckFailed',
                                        'Dimensions': [{'Name': 'InstanceId', 'Value': instance['InstanceId']}]
                                    },
                                    'Period': 3600,
                                    'Stat': 'Maximum'
                                },
                                'ReturnData': True
                            }],
                            StartTime=start_time,
                            EndTime=end_time
                        )
                        
                        if status_checks['MetricDataResults'][0]['Values']:
                            instance_data['state_transition_time'] = current_time - timedelta(
                                hours=len(status_checks['MetricDataResults'][0]['Values'])
                            )
                    except Exception as e:
                        logger.error(f"{log_prefix}Error collecting status checks: {str(e)}")

                # CPU 사용률 데이터 수집
                if instance['State']['Name'] == 'running':
                    logger.debug(f"{log_prefix}Collecting CPU metrics for {instance['InstanceId']}")
                    try:
                        # 시간 파라미터 설정
                        end_time = current_time
                        start_time = end_time - timedelta(days=7)
                            
                        cpu_metrics = cloudwatch.get_metric_statistics(
                            Namespace='AWS/EC2',
                            MetricName='CPUUtilization',
                            Dimensions=[{'Name': 'InstanceId', 'Value': instance['InstanceId']}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=3600,
                            Statistics=['Average']
                        )
                        
                        # CPU 메트릭 수집 및 분석
                        cpu_metrics_data = [point['Average'] for point in cpu_metrics['Datapoints']]
                        instance_data['cpu_metrics'] = cpu_metrics_data
                        
                        # CPU 사용률 패턴 분석 (낮음/높음)
                        low_usage_days = 0
                        high_usage_days = 0
                        
                        for metric in cpu_metrics_data:
                            if metric < 20:
                                low_usage_days += 1/24
                            elif metric > 80:
                                high_usage_days += 1/24
                        
                        instance_data['cpu_analysis'] = {
                            'low_usage_days': int(low_usage_days),
                            'high_usage_days': int(high_usage_days)
                        }
                    except Exception as e:
                        logger.error(f"{log_prefix}Error collecting CPU metrics: {str(e)}")

                # 네트워크 메트릭 수집
                if instance['State']['Name'] == 'running':
                    logger.debug(f"{log_prefix}Collecting network metrics for {instance['InstanceId']}")
                    try:
                        # 네트워크 메트릭 직접 수집
                        metrics = {}
                        metric_names = ['NetworkIn', 'NetworkOut', 'NetworkPacketsIn', 'NetworkPacketsOut']
                        
                        for metric_name in metric_names:
                            # 시간 파라미터 설정
                            end_time = current_time
                            start_time = end_time - timedelta(hours=1)
                                
                            response = cloudwatch.get_metric_statistics(
                                Namespace='AWS/EC2',
                                MetricName=metric_name,
                                Dimensions=[{'Name': 'InstanceId', 'Value': instance['InstanceId']}],
                                StartTime=start_time,
                                EndTime=end_time,
                                Period=300,
                                Statistics=['Average']
                            )
                            if response['Datapoints']:
                                metrics[metric_name] = max(point['Average'] for point in response['Datapoints'])
                            else:
                                metrics[metric_name] = 0
                                
                        instance_data['network_metrics'] = metrics
                    except Exception as e:
                        logger.error(f"{log_prefix}Error collecting network metrics: {str(e)}")

                # EBS 볼륨 정보 수집
                logger.debug(f"{log_prefix}Collecting volume information for {instance['InstanceId']}")
                try:
                    volumes = ec2_client.describe_volumes(
                        Filters=[{'Name': 'attachment.instance-id', 'Values': [instance['InstanceId']]}]
                    )
                    instance_data['volumes'] = volumes.get('Volumes', [])
                except Exception as e:
                    logger.error(f"{log_prefix}Error collecting volume information: {str(e)}")

                instances.append(instance_data)

        result = {'instances': instances}
        # result 데이터 로깅
        logger.info(f"{log_prefix}Successfully collected data for {len(instances)} EC2 instances")
        return result
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_ec2_data: {str(e)}")
        return {'error': str(e)}