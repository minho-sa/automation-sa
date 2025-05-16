import boto3
from typing import Dict, List, Any
import logging
from datetime import datetime, timedelta
import pytz

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_rds_data(aws_access_key: str, aws_secret_key: str, region: str, collection_id: str = None) -> Dict:
    """RDS 인스턴스 데이터 수집
    
    Args:
        aws_access_key: AWS 액세스 키
        aws_secret_key: AWS 시크릿 키
        region: AWS 리전
        collection_id: 수집 ID (로깅용)
        
    Returns:
        Dict: RDS 인스턴스 정보가 담긴 딕셔너리
        
    Examples:
        >>> rds_data = get_rds_data(aws_access_key, aws_secret_key, 'ap-northeast-2', '20250516_123456')
        >>> print(f"총 {len(rds_data['instances'])}개의 RDS 인스턴스가 수집되었습니다.")
        
    Instance Classes:
        - db.t3.micro: 1 vCPU, 1 GiB 메모리, 버스트 가능한 성능의 저비용 인스턴스
        - db.t3.small: 2 vCPU, 2 GiB 메모리, 버스트 가능한 성능의 저비용 인스턴스
        - db.m5.large: 2 vCPU, 8 GiB 메모리, 범용 인스턴스
        - db.m5.xlarge: 4 vCPU, 16 GiB 메모리, 범용 인스턴스
        - db.r5.large: 2 vCPU, 16 GiB 메모리, 메모리 최적화 인스턴스
        - db.r5.xlarge: 4 vCPU, 32 GiB 메모리, 메모리 최적화 인스턴스
        
    Storage Types:
        - gp2: 범용 SSD 스토리지 (3 IOPS/GB, 최대 10,000 IOPS)
        - gp3: 범용 SSD 스토리지 (3,000 IOPS 기본, 최대 16,000 IOPS)
        - io1: 프로비저닝된 IOPS SSD (최대 64,000 IOPS)
        - standard: 마그네틱 스토리지 (레거시)
        
    Database Engines:
        - mysql: MySQL 5.7, 8.0 - 오픈 소스 관계형 데이터베이스
        - postgres: PostgreSQL 10, 11, 12, 13, 14, 15 - 고급 기능을 갖춘 오픈 소스 객체 관계형 데이터베이스
        - mariadb: MariaDB 10.3, 10.4, 10.5, 10.6 - MySQL 포크로 개발된 오픈 소스 데이터베이스
        - oracle: Oracle 12c, 19c - 엔터프라이즈급 상용 관계형 데이터베이스
        - sqlserver: SQL Server 2017, 2019 - Microsoft의 관계형 데이터베이스 관리 시스템
        - aurora-mysql: Aurora MySQL 5.7, 8.0 - AWS에서 개발한 MySQL 호환 데이터베이스
        - aurora-postgresql: Aurora PostgreSQL 10, 11, 12, 13, 14 - AWS에서 개발한 PostgreSQL 호환 데이터베이스
    """
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.info(f"{log_prefix}Starting RDS data collection")
    try:
        # RDS 클라이언트 생성
        rds_client = boto3.client(
            'rds',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        
        # CloudWatch 클라이언트 생성 (메트릭 수집용)
        cloudwatch = boto3.client(
            'cloudwatch',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        
        # RDS 인스턴스 목록 가져오기
        response = rds_client.describe_db_instances()
        instances = []
        
        logger.info(f"{log_prefix}Found {len(response.get('DBInstances', []))} RDS instances")
        
        # 각 RDS 인스턴스에 대한 정보 수집
        for instance in response.get('DBInstances', []):
            instance_id = instance['DBInstanceIdentifier']
            logger.debug(f"{log_prefix}Processing RDS instance: {instance_id}")
            
            # 기본 인스턴스 정보
            instance_data = {
                'id': instance_id,
                'engine': instance.get('Engine'),
                'engine_version': instance.get('EngineVersion'),
                'instance_class': instance.get('DBInstanceClass'),
                'status': instance.get('DBInstanceStatus'),
                'creation_time': instance.get('InstanceCreateTime'),
                'is_aurora': instance_id.startswith('aurora-'),
                'storage_encrypted': instance.get('StorageEncrypted', False),
                'storage_type': instance.get('StorageType', 'unknown'),
                'allocated_storage': instance.get('AllocatedStorage', 0),
                'iops': instance.get('Iops', 0),
                'vpc_id': instance.get('DBSubnetGroup', {}).get('VpcId', 'unknown'),
                'availability_zone': instance.get('AvailabilityZone', 'unknown'),
                'multi_az': instance.get('MultiAZ', False),
                'backup_retention_period': instance.get('BackupRetentionPeriod', 0),
                'performance_insights_enabled': instance.get('PerformanceInsightsEnabled', False),
                'auto_minor_version_upgrade': instance.get('AutoMinorVersionUpgrade', False),
                'publicly_accessible': instance.get('PubliclyAccessible', False),
                'tags': {},
                'metrics': {},
                'parameter_groups': []
            }
            
            # 태그 정보 수집
            try:
                tags_response = rds_client.list_tags_for_resource(
                    ResourceName=instance.get('DBInstanceArn')
                )
                instance_data['tags'] = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
            except Exception as e:
                logger.error(f"{log_prefix}Error getting tags for {instance_id}: {str(e)}")
            
            # 파라미터 그룹 정보 수집
            try:
                for pg in instance.get('DBParameterGroups', []):
                    pg_name = pg.get('DBParameterGroupName')
                    pg_details = rds_client.describe_db_parameters(
                        DBParameterGroupName=pg_name
                    )
                    
                    # 중요 파라미터만 필터링
                    important_params = [
                        param for param in pg_details.get('Parameters', [])
                        if param.get('ParameterName') in [
                            'max_connections', 'innodb_buffer_pool_size', 
                            'shared_buffers', 'work_mem', 'maintenance_work_mem'
                        ]
                    ]
                    
                    instance_data['parameter_groups'].append({
                        'name': pg_name,
                        'status': pg.get('ParameterApplyStatus'),
                        'important_parameters': important_params
                    })
            except Exception as e:
                logger.error(f"{log_prefix}Error getting parameter groups for {instance_id}: {str(e)}")
            
            # CloudWatch 메트릭 수집 (CPU, 메모리, 연결 수 등)
            try:
                # 현재 시간과 24시간 전 시간을 사용하여 시간 범위 설정
                current_time = datetime.now(pytz.UTC)
                start_time = current_time - timedelta(days=1)
                
                # CPU 사용률
                cpu_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='CPUUtilization',
                    Dimensions=[
                        {'Name': 'DBInstanceIdentifier', 'Value': instance_id}
                    ],
                    StartTime=start_time,
                    EndTime=current_time,
                    Period=3600,
                    Statistics=['Average', 'Maximum']
                )
                
                if cpu_response['Datapoints']:
                    instance_data['metrics']['cpu'] = {
                        'average': sum(point['Average'] for point in cpu_response['Datapoints']) / len(cpu_response['Datapoints']),
                        'max': max(point['Maximum'] for point in cpu_response['Datapoints'])
                    }
                
                # 여유 스토리지 공간
                storage_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='FreeStorageSpace',
                    Dimensions=[
                        {'Name': 'DBInstanceIdentifier', 'Value': instance_id}
                    ],
                    StartTime=start_time,
                    EndTime=current_time,
                    Period=3600,
                    Statistics=['Average', 'Minimum']
                )
                
                if storage_response['Datapoints']:
                    instance_data['metrics']['free_storage'] = {
                        'average': sum(point['Average'] for point in storage_response['Datapoints']) / len(storage_response['Datapoints']),
                        'min': min(point['Minimum'] for point in storage_response['Datapoints'])
                    }
                
                # 데이터베이스 연결 수
                connections_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='DatabaseConnections',
                    Dimensions=[
                        {'Name': 'DBInstanceIdentifier', 'Value': instance_id}
                    ],
                    StartTime=start_time,
                    EndTime=current_time,
                    Period=3600,
                    Statistics=['Average', 'Maximum']
                )
                
                if connections_response['Datapoints']:
                    instance_data['metrics']['connections'] = {
                        'average': sum(point['Average'] for point in connections_response['Datapoints']) / len(connections_response['Datapoints']),
                        'max': max(point['Maximum'] for point in connections_response['Datapoints'])
                    }
                
                # 읽기/쓰기 지연 시간
                read_latency_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='ReadLatency',
                    Dimensions=[
                        {'Name': 'DBInstanceIdentifier', 'Value': instance_id}
                    ],
                    StartTime=start_time,
                    EndTime=current_time,
                    Period=3600,
                    Statistics=['Average']
                )
                
                if read_latency_response['Datapoints']:
                    instance_data['metrics']['read_latency'] = sum(point['Average'] for point in read_latency_response['Datapoints']) / len(read_latency_response['Datapoints'])
                
                write_latency_response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='WriteLatency',
                    Dimensions=[
                        {'Name': 'DBInstanceIdentifier', 'Value': instance_id}
                    ],
                    StartTime=start_time,
                    EndTime=current_time,
                    Period=3600,
                    Statistics=['Average']
                )
                
                if write_latency_response['Datapoints']:
                    instance_data['metrics']['write_latency'] = sum(point['Average'] for point in write_latency_response['Datapoints']) / len(write_latency_response['Datapoints'])
                
            except Exception as e:
                logger.error(f"{log_prefix}Error getting metrics for {instance_id}: {str(e)}")
            
            # 보안 그룹 정보 수집
            try:
                security_groups = []
                for sg in instance.get('VpcSecurityGroups', []):
                    security_groups.append({
                        'id': sg.get('VpcSecurityGroupId'),
                        'status': sg.get('Status')
                    })
                instance_data['security_groups'] = security_groups
            except Exception as e:
                logger.error(f"{log_prefix}Error getting security groups for {instance_id}: {str(e)}")
            
            instances.append(instance_data)
        
        result = {'instances': instances}
        logger.info(f"{log_prefix}Successfully collected data for {len(instances)} RDS instances")
        return result
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_rds_data: {str(e)}")
        return {'error': str(e)}