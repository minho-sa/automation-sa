from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from app.services.resource.common.base_collector import BaseCollector
from app.services.resource.common.resource_model import RDSInstance

class RDSCollector(BaseCollector):
    """
    RDS 인스턴스 데이터 수집기
    """
    
    def _init_clients(self) -> None:
        """
        필요한 AWS 클라이언트 초기화
        """
        self.rds_client = self.get_client('rds')
    
    def collect(self, collection_id: str = None) -> Dict[str, Any]:
        """
        RDS 인스턴스 데이터 수집
        
        Args:
            collection_id: 수집 ID (선택 사항)
            
        Returns:
            Dict[str, Any]: 수집된 RDS 데이터
        """
        log_prefix = f"[{collection_id}] " if collection_id else ""
        self.logger.info(f"{log_prefix}RDS 데이터 수집 시작")
        
        try:
            response = self.rds_client.describe_db_instances()
            instances = []
            
            self.logger.info(f"{log_prefix}RDS 인스턴스 {len(response['DBInstances'])}개 발견")
            
            for instance_data in response['DBInstances']:
                instance = self._process_instance(instance_data, log_prefix)
                if instance:
                    instance_dict = instance.to_dict()
                    if 'instance_create_time' in instance_dict and isinstance(instance_dict['instance_create_time'], datetime):
                        instance_dict['instance_create_time'] = instance_dict['instance_create_time'].isoformat()
                    instances.append(instance_dict)
            
            # 엔진별 요약 정보
            engine_summary = {}
            for instance in instances:
                engine = instance['engine']
                if engine not in engine_summary:
                    engine_summary[engine] = {
                        'count': 0,
                        'available': 0,
                        'stopped': 0
                    }
                
                engine_summary[engine]['count'] += 1
                if instance['db_instance_status'] == 'available':
                    engine_summary[engine]['available'] += 1
                elif instance['db_instance_status'] == 'stopped':
                    engine_summary[engine]['stopped'] += 1
            
            result = {
                'instances': instances,
                'summary': {
                    'total_instances': len(instances),
                    'available_instances': sum(1 for i in instances if i['db_instance_status'] == 'available'),
                    'stopped_instances': sum(1 for i in instances if i['db_instance_status'] == 'stopped'),
                    'engine_summary': engine_summary
                }
            }
            
            self.logger.info(f"{log_prefix}RDS 인스턴스 {len(instances)}개 데이터 수집 완료")
            return result
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"{log_prefix}RDS 데이터 수집 중 오류 발생: {error_msg}")
            
            if 'AccessDenied' in error_msg or 'not authorized' in error_msg:
                self.logger.warning(f"{log_prefix}RDS 조회 권한이 없습니다. 빈 결과를 반환합니다.")
                return {
                    'instances': [],
                    'summary': {
                        'total_instances': 0,
                        'available_instances': 0,
                        'stopped_instances': 0,
                        'engine_summary': {}
                    },
                    'message': 'RDS 조회 권한이 없습니다. AWS IAM에서 rds:DescribeDBInstances 권한을 추가해주세요.',
                    'permission_error': True
                }
            
            return {
                'error': error_msg,
                'instances': [],
                'summary': {
                    'total_instances': 0,
                    'available_instances': 0,
                    'stopped_instances': 0,
                    'engine_summary': {}
                }
            }
    
    def _process_instance(self, instance_data: Dict[str, Any], log_prefix: str) -> Optional[RDSInstance]:
        """
        RDS 인스턴스 데이터 처리
        
        Args:
            instance_data: RDS 인스턴스 원시 데이터
            log_prefix: 로그 접두사
            
        Returns:
            Optional[RDSInstance]: 처리된 RDS 인스턴스 객체 또는 None
        """
        db_instance_identifier = instance_data['DBInstanceIdentifier']
        self.logger.debug(f"{log_prefix}RDS 인스턴스 처리 중: {db_instance_identifier}")
        
        try:
            instance = RDSInstance(
                id=db_instance_identifier,
                name=db_instance_identifier,  # RDS는 식별자가 이름 역할
                region=self.region,
                engine=instance_data.get('Engine', ''),
                engine_version=instance_data.get('EngineVersion', ''),
                db_instance_class=instance_data.get('DBInstanceClass', ''),
                db_instance_status=instance_data.get('DBInstanceStatus', ''),
                allocated_storage=instance_data.get('AllocatedStorage', 0),
                storage_type=instance_data.get('StorageType', ''),
                storage_encrypted=instance_data.get('StorageEncrypted', False),
                multi_az=instance_data.get('MultiAZ', False),
                publicly_accessible=instance_data.get('PubliclyAccessible', False),
                backup_retention_period=instance_data.get('BackupRetentionPeriod', 0),
                instance_create_time=instance_data.get('InstanceCreateTime'),
                vpc_security_groups=[sg['VpcSecurityGroupId'] for sg in instance_data.get('VpcSecurityGroups', [])],
                db_subnet_group_name=instance_data.get('DBSubnetGroup', {}).get('DBSubnetGroupName', ''),
                availability_zone=instance_data.get('AvailabilityZone', ''),
                endpoint=instance_data.get('Endpoint', {}).get('Address', '') if instance_data.get('Endpoint') else '',
                port=instance_data.get('Endpoint', {}).get('Port', 0) if instance_data.get('Endpoint') else 0
            )
            
            return instance
            
        except Exception as e:
            self.logger.error(f"{log_prefix}RDS 인스턴스 처리 중 오류 발생: {db_instance_identifier} - {str(e)}")
            return None