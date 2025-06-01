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
        
        # pricing 클라이언트는 us-east-1 리전에서만 사용 가능
        # 별도의 세션을 생성하여 pricing 클라이언트 초기화
        import boto3
        pricing_session = boto3.Session(region_name='us-east-1')
        self.pricing_client = pricing_session.client('pricing')
    
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
            
            # 리전 내 가용 영역 정보 수집
            az_info = self._get_availability_zones()
            
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
                    
                    # 가용 영역 정보 추가
                    if instance.az in az_info:
                        instance_dict['az_info'] = az_info[instance.az]
                    
                    instances.append(instance_dict)
            
            # 인스턴스 유형별 요약 정보
            instance_types = {}
            for instance in instances:
                instance_type = instance['type']
                if instance_type not in instance_types:
                    instance_types[instance_type] = {
                        'count': 0,
                        'running': 0,
                        'stopped': 0
                    }
                
                instance_types[instance_type]['count'] += 1
                if instance['state'] == 'running':
                    instance_types[instance_type]['running'] += 1
                elif instance['state'] == 'stopped':
                    instance_types[instance_type]['stopped'] += 1
            
            # 가용 영역별 요약 정보
            az_distribution = {}
            for instance in instances:
                az = instance['az']
                if az not in az_distribution:
                    az_distribution[az] = {
                        'count': 0,
                        'running': 0,
                        'stopped': 0
                    }
                
                az_distribution[az]['count'] += 1
                if instance['state'] == 'running':
                    az_distribution[az]['running'] += 1
                elif instance['state'] == 'stopped':
                    az_distribution[az]['stopped'] += 1
            
            result = {
                'instances': instances,
                'summary': {
                    'total_instances': len(instances),
                    'running_instances': sum(1 for i in instances if i['state'] == 'running'),
                    'stopped_instances': sum(1 for i in instances if i['state'] == 'stopped'),
                    'instance_types': instance_types,
                    'az_distribution': az_distribution
                }
            }
            
            self.logger.info(f"{log_prefix}EC2 인스턴스 {len(instances)}개 데이터 수집 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"{log_prefix}EC2 데이터 수집 중 오류 발생: {str(e)}")
            return {'error': str(e)}
    
    def _get_availability_zones(self) -> Dict[str, Dict[str, Any]]:
        """
        가용 영역 정보 수집
        
        Returns:
            Dict[str, Dict[str, Any]]: 가용 영역 정보
        """
        try:
            response = self.ec2_client.describe_availability_zones()
            az_info = {}
            
            for az in response['AvailabilityZones']:
                az_info[az['ZoneName']] = {
                    'zone_id': az['ZoneId'],
                    'zone_type': az['ZoneType'],
                    'state': az['State'],
                    'region': az['RegionName'],
                    'messages': az.get('Messages', [])
                }
            
            return az_info
        except Exception as e:
            self.logger.error(f"가용 영역 정보 수집 중 오류 발생: {str(e)}")
            return {}
    
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
        
        # 추가 인스턴스 정보 수집
        instance.architecture = instance_data.get('Architecture')
        instance.hypervisor = instance_data.get('Hypervisor')
        instance.root_device_type = instance_data.get('RootDeviceType')
        instance.root_device_name = instance_data.get('RootDeviceName')
        instance.virtualization_type = instance_data.get('VirtualizationType')
        
        # 네트워크 인터페이스 정보 수집
        instance.network_interfaces = []
        for ni in instance_data.get('NetworkInterfaces', []):
            ni_info = {
                'id': ni.get('NetworkInterfaceId'),
                'subnet_id': ni.get('SubnetId'),
                'vpc_id': ni.get('VpcId'),
                'private_ip': ni.get('PrivateIpAddress'),
                'public_ip': ni.get('Association', {}).get('PublicIp'),
                'status': ni.get('Status')
            }
            instance.network_interfaces.append(ni_info)
        
        # 보안 그룹 정보 수집
        self._collect_security_groups(instance, instance_data, log_prefix)
        
        # 상태 변경 시간 수집 (중지된 인스턴스만)
        if instance.state == 'stopped':
            self._collect_state_transition_time(instance, current_time, log_prefix)
        
        # CPU 사용률 데이터 수집 (실행 중인 인스턴스만)
        if instance.state == 'running':
            self._collect_cpu_metrics(instance, current_time, log_prefix)
            self._collect_network_metrics(instance, current_time, log_prefix)
            self._collect_memory_metrics(instance, current_time, log_prefix)
            self._collect_disk_metrics(instance, current_time, log_prefix)
        
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
                        'group_name': sg['GroupName'],
                        'description': sg_details['SecurityGroups'][0].get('Description', ''),
                        'inbound_rules': [],
                        'outbound_rules': []
                    }
                    
                    # 인바운드 규칙
                    for rule in sg_details['SecurityGroups'][0].get('IpPermissions', []):
                        rule_info = {
                            'protocol': rule.get('IpProtocol', 'all'),
                            'from_port': rule.get('FromPort', 0),
                            'to_port': rule.get('ToPort', 0),
                            'ip_ranges': [ip.get('CidrIp') for ip in rule.get('IpRanges', [])],
                            'ipv6_ranges': [ip.get('CidrIpv6') for ip in rule.get('Ipv6Ranges', [])]
                        }
                        sg_info['inbound_rules'].append(rule_info)
                    
                    # 아웃바운드 규칙
                    for rule in sg_details['SecurityGroups'][0].get('IpPermissionsEgress', []):
                        rule_info = {
                            'protocol': rule.get('IpProtocol', 'all'),
                            'from_port': rule.get('FromPort', 0),
                            'to_port': rule.get('ToPort', 0),
                            'ip_ranges': [ip.get('CidrIp') for ip in rule.get('IpRanges', [])],
                            'ipv6_ranges': [ip.get('CidrIpv6') for ip in rule.get('Ipv6Ranges', [])]
                        }
                        sg_info['outbound_rules'].append(rule_info)
                    
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
                Statistics=['Average', 'Maximum', 'Minimum']
            )
            
            # CPU 메트릭 수집
            if cpu_metrics['Datapoints']:
                # 최신 데이터포인트를 현재 CPU 사용률로 설정
                latest_point = max(cpu_metrics['Datapoints'], key=lambda x: x['Timestamp'])
                instance.cpu_utilization = latest_point['Average']
                instance.cpu_max = latest_point['Maximum']
                instance.cpu_min = latest_point['Minimum']
                
                # 추세 데이터 (최대 24개 포인트)
                sorted_points = sorted(cpu_metrics['Datapoints'], key=lambda x: x['Timestamp'])
                instance.cpu_trend = [
                    {
                        'timestamp': point['Timestamp'].isoformat(),
                        'average': point['Average'],
                        'maximum': point['Maximum'],
                        'minimum': point['Minimum']
                    }
                    for point in sorted_points[-24:]
                ]
        except Exception as e:
            self.logger.error(f"{log_prefix}CPU 메트릭 수집 중 오류 발생: {str(e)}")
    
    def _collect_memory_metrics(self, instance: EC2Instance, current_time: datetime, log_prefix: str) -> None:
        """
        메모리 사용률 데이터 수집 (CloudWatch 에이전트 필요)
        
        Args:
            instance: EC2 인스턴스 객체
            current_time: 현재 시간
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}메모리 메트릭 수집 중: {instance.id}")
        try:
            # 시간 파라미터 설정
            end_time = current_time
            start_time = end_time - timedelta(hours=1)
            
            # 메모리 사용률 메트릭 (CloudWatch 에이전트 필요)
            memory_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='CWAgent',
                MetricName='mem_used_percent',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance.id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5분 간격
                Statistics=['Average']
            )
            
            if memory_metrics['Datapoints']:
                latest_point = max(memory_metrics['Datapoints'], key=lambda x: x['Timestamp'])
                instance.memory_utilization = latest_point['Average']
        except Exception as e:
            # CloudWatch 에이전트가 설치되지 않은 경우 무시
            self.logger.debug(f"{log_prefix}메모리 메트릭 수집 중 오류 발생 (무시): {str(e)}")
    
    def _collect_disk_metrics(self, instance: EC2Instance, current_time: datetime, log_prefix: str) -> None:
        """
        디스크 사용률 데이터 수집 (CloudWatch 에이전트 필요)
        
        Args:
            instance: EC2 인스턴스 객체
            current_time: 현재 시간
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}디스크 메트릭 수집 중: {instance.id}")
        try:
            # 시간 파라미터 설정
            end_time = current_time
            start_time = end_time - timedelta(hours=1)
            
            # 디스크 사용률 메트릭 (CloudWatch 에이전트 필요)
            disk_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='CWAgent',
                MetricName='disk_used_percent',
                Dimensions=[
                    {'Name': 'InstanceId', 'Value': instance.id},
                    {'Name': 'path', 'Value': '/'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5분 간격
                Statistics=['Average']
            )
            
            if disk_metrics['Datapoints']:
                latest_point = max(disk_metrics['Datapoints'], key=lambda x: x['Timestamp'])
                instance.disk_utilization = latest_point['Average']
        except Exception as e:
            # CloudWatch 에이전트가 설치되지 않은 경우 무시
            self.logger.debug(f"{log_prefix}디스크 메트릭 수집 중 오류 발생 (무시): {str(e)}")
    
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
                Statistics=['Average', 'Sum']
            )
            
            # NetworkOut 메트릭
            network_out = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkOut',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance.id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5분 간격
                Statistics=['Average', 'Sum']
            )
            
            # 최신 데이터 저장 (MB 단위로 변환)
            if network_in['Datapoints']:
                latest_in = max(network_in['Datapoints'], key=lambda x: x['Timestamp'])
                instance.network_in = latest_in['Average'] / (1024 * 1024)  # Bytes to MB
                instance.network_in_sum = latest_in['Sum'] / (1024 * 1024)  # Bytes to MB
                
            if network_out['Datapoints']:
                latest_out = max(network_out['Datapoints'], key=lambda x: x['Timestamp'])
                instance.network_out = latest_out['Average'] / (1024 * 1024)  # Bytes to MB
                instance.network_out_sum = latest_out['Sum'] / (1024 * 1024)  # Bytes to MB
                
            # 네트워크 추세 데이터
            if network_in['Datapoints'] and network_out['Datapoints']:
                in_points = sorted(network_in['Datapoints'], key=lambda x: x['Timestamp'])
                out_points = sorted(network_out['Datapoints'], key=lambda x: x['Timestamp'])
                
                # 타임스탬프 매칭
                timestamps = sorted(set([p['Timestamp'] for p in in_points + out_points]))
                
                instance.network_trend = []
                for ts in timestamps[-12:]:  # 최근 1시간 (5분 간격 = 12개 포인트)
                    in_point = next((p for p in in_points if p['Timestamp'] == ts), None)
                    out_point = next((p for p in out_points if p['Timestamp'] == ts), None)
                    
                    trend_point = {
                        'timestamp': ts.isoformat(),
                        'in': in_point['Average'] / (1024 * 1024) if in_point else 0,
                        'out': out_point['Average'] / (1024 * 1024) if out_point else 0
                    }
                    instance.network_trend.append(trend_point)
                
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
                    'iops': volume.get('Iops'),
                    'throughput': volume.get('Throughput'),
                    'encrypted': volume['Encrypted'],
                    'state': volume['State'],
                    'create_time': volume['CreateTime'].isoformat(),
                    'attachments': []
                }
                
                # 볼륨 연결 정보
                for attachment in volume.get('Attachments', []):
                    attachment_info = {
                        'device': attachment.get('Device'),
                        'state': attachment.get('State'),
                        'attach_time': attachment.get('AttachTime').isoformat() if attachment.get('AttachTime') else None,
                        'delete_on_termination': attachment.get('DeleteOnTermination', False)
                    }
                    volume_info['attachments'].append(attachment_info)
                
                # 볼륨 태그
                volume_info['tags'] = volume.get('Tags', [])
                
                instance.volumes.append(volume_info)
                
        except Exception as e:
            self.logger.error(f"{log_prefix}볼륨 정보 수집 중 오류 발생: {str(e)}")