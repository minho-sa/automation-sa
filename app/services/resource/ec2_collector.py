from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytz
import logging
from app.services.resource.common.base_collector import BaseCollector
from app.services.resource.common.resource_model import EC2Instance

class EC2Collector(BaseCollector):
    """
    EC2 인스턴스 데이터 수집기
    """
    
    def _init_clients(self) -> None:
        """
        필요한 AWS 클라이언트 초기화
        """
        self.ec2_client = self.get_client('ec2')
        self.cloudwatch = self.get_client('cloudwatch')
    
    def collect(self, collection_id: str = None) -> Dict[str, Any]:
        """
        EC2 인스턴스 데이터 수집
        
        Args:
            collection_id: 수집 ID (선택 사항)
            
        Returns:
            Dict[str, Any]: 수집된 EC2 데이터
        """
        log_prefix = f"[{collection_id}] " if collection_id else ""
        self.logger.info(f"{log_prefix}EC2 데이터 수집 시작")
        
        try:
            # 현재 시간 설정
            current_time = datetime.now(pytz.UTC)
            response = self.ec2_client.describe_instances()
            instances = []
            
            self.logger.info(f"{log_prefix}EC2 인스턴스 {len(response['Reservations'])}개 예약 발견")
            
            for reservation in response['Reservations']:
                for instance_data in reservation['Instances']:
                    # EC2Instance 객체 생성
                    instance = self._process_instance(instance_data, current_time, log_prefix)
                    
                    # datetime 객체를 문자열로 변환
                    instance_dict = instance.to_dict()
                    if 'launch_time' in instance_dict and isinstance(instance_dict['launch_time'], datetime):
                        instance_dict['launch_time'] = instance_dict['launch_time'].isoformat()
                    if 'state_transition_time' in instance_dict and isinstance(instance_dict['state_transition_time'], datetime):
                        instance_dict['state_transition_time'] = instance_dict['state_transition_time'].isoformat()
                    
                    instances.append(instance_dict)
            
            result = {'instances': instances}
            self.logger.info(f"{log_prefix}EC2 인스턴스 {len(instances)}개 데이터 수집 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"{log_prefix}EC2 데이터 수집 중 오류 발생: {str(e)}")
            return {'error': str(e)}
    
    def _process_instance(self, instance_data: Dict[str, Any], current_time: datetime, log_prefix: str) -> EC2Instance:
        """
        EC2 인스턴스 데이터 처리
        
        Args:
            instance_data: EC2 인스턴스 원시 데이터
            current_time: 현재 시간
            log_prefix: 로그 접두사
            
        Returns:
            EC2Instance: 처리된 EC2 인스턴스 객체
        """
        instance_id = instance_data['InstanceId']
        self.logger.debug(f"{log_prefix}인스턴스 처리 중: {instance_id}")
        
        # 기본 인스턴스 정보로 객체 생성
        instance = EC2Instance(
            id=instance_id,
            region=self.region,
            type=instance_data['InstanceType'],
            state=instance_data['State']['Name'],
            az=instance_data['Placement']['AvailabilityZone'],
            launch_time=instance_data.get('LaunchTime'),
            tags=instance_data.get('Tags', [])
        )
        
        # 보안 그룹 정보 수집
        self._collect_security_groups(instance, instance_data, log_prefix)
        
        # 상태 변경 시간 수집 (중지된 인스턴스만)
        if instance.state == 'stopped':
            self._collect_state_transition_time(instance, current_time, log_prefix)
        
        # CPU 사용률 데이터 수집 (실행 중인 인스턴스만)
        if instance.state == 'running':
            self._collect_cpu_metrics(instance, current_time, log_prefix)
            self._collect_network_metrics(instance, current_time, log_prefix)
        
        # EBS 볼륨 정보 수집
        self._collect_volumes(instance, log_prefix)
        
        return instance
    
    def _collect_security_groups(self, instance: EC2Instance, instance_data: Dict[str, Any], log_prefix: str) -> None:
        """
        보안 그룹 정보 수집
        
        Args:
            instance: EC2 인스턴스 객체
            instance_data: EC2 인스턴스 원시 데이터
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}보안 그룹 정보 수집 중: {instance.id}")
        try:
            for sg in instance_data.get('SecurityGroups', []):
                sg_details = self.ec2_client.describe_security_groups(GroupIds=[sg['GroupId']])
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
                    
                    instance.security_groups.append(sg_info)
        except Exception as e:
            self.logger.error(f"{log_prefix}보안 그룹 정보 수집 중 오류 발생: {str(e)}")
    
    def _collect_state_transition_time(self, instance: EC2Instance, current_time: datetime, log_prefix: str) -> None:
        """
        인스턴스 상태 변경 시간 수집
        
        Args:
            instance: EC2 인스턴스 객체
            current_time: 현재 시간
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}상태 변경 시간 수집 중: {instance.id}")
        try:
            # 시간 파라미터 설정
            end_time = current_time
            start_time = end_time - timedelta(days=1)  # 1일로 축소
            
            status_checks = self.cloudwatch.get_metric_data(
                MetricDataQueries=[{
                    'Id': 'status',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': 'StatusCheckFailed',
                            'Dimensions': [{'Name': 'InstanceId', 'Value': instance.id}]
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
                instance.state_transition_time = current_time - timedelta(
                    hours=len(status_checks['MetricDataResults'][0]['Values'])
                )
        except Exception as e:
            self.logger.error(f"{log_prefix}상태 변경 시간 수집 중 오류 발생: {str(e)}")
    
    def _collect_cpu_metrics(self, instance: EC2Instance, current_time: datetime, log_prefix: str) -> None:
        """
        CPU 사용률 데이터 수집
        
        Args:
            instance: EC2 인스턴스 객체
            current_time: 현재 시간
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}CPU 메트릭 수집 중: {instance.id}")
        try:
            # 시간 파라미터 설정 - 24시간으로 축소
            end_time = current_time
            start_time = end_time - timedelta(hours=24)
                
            cpu_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance.id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1시간 간격
                Statistics=['Average']
            )
            
            # CPU 메트릭 수집
            if cpu_metrics['Datapoints']:
                # 최신 데이터포인트를 현재 CPU 사용률로 설정
                latest_point = max(cpu_metrics['Datapoints'], key=lambda x: x['Timestamp'])
                instance.cpu_utilization = latest_point['Average']
                
                # 추세 데이터 (최대 24개 포인트)
                sorted_points = sorted(cpu_metrics['Datapoints'], key=lambda x: x['Timestamp'])
                instance.cpu_trend = [point['Average'] for point in sorted_points[-24:]]
        except Exception as e:
            self.logger.error(f"{log_prefix}CPU 메트릭 수집 중 오류 발생: {str(e)}")
    
    def _collect_network_metrics(self, instance: EC2Instance, current_time: datetime, log_prefix: str) -> None:
        """
        네트워크 메트릭 수집
        
        Args:
            instance: EC2 인스턴스 객체
            current_time: 현재 시간
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}네트워크 메트릭 수집 중: {instance.id}")
        try:
            # 시간 파라미터 설정
            end_time = current_time
            start_time = end_time - timedelta(hours=1)
            
            # NetworkIn 메트릭
            network_in = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkIn',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance.id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5분 간격
                Statistics=['Average']
            )
            
            # NetworkOut 메트릭
            network_out = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkOut',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance.id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5분 간격
                Statistics=['Average']
            )
            
            # 최신 데이터 저장 (MB 단위로 변환)
            if network_in['Datapoints']:
                latest_in = max(network_in['Datapoints'], key=lambda x: x['Timestamp'])
                instance.network_in = latest_in['Average'] / (1024 * 1024)  # Bytes to MB
                
            if network_out['Datapoints']:
                latest_out = max(network_out['Datapoints'], key=lambda x: x['Timestamp'])
                instance.network_out = latest_out['Average'] / (1024 * 1024)  # Bytes to MB
                
        except Exception as e:
            self.logger.error(f"{log_prefix}네트워크 메트릭 수집 중 오류 발생: {str(e)}")
    
    def _collect_volumes(self, instance: EC2Instance, log_prefix: str) -> None:
        """
        EBS 볼륨 정보 수집
        
        Args:
            instance: EC2 인스턴스 객체
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}볼륨 정보 수집 중: {instance.id}")
        try:
            volumes = self.ec2_client.describe_volumes(
                Filters=[{'Name': 'attachment.instance-id', 'Values': [instance.id]}]
            )
            
            # 필요한 볼륨 정보만 저장
            for volume in volumes.get('Volumes', []):
                volume_info = {
                    'volume_id': volume['VolumeId'],
                    'size': volume['Size'],
                    'volume_type': volume['VolumeType'],
                    'encrypted': volume['Encrypted'],
                    'state': volume['State']
                }
                instance.volumes.append(volume_info)
                
        except Exception as e:
            self.logger.error(f"{log_prefix}볼륨 정보 수집 중 오류 발생: {str(e)}")