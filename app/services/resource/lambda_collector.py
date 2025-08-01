from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytz
import logging
from app.services.resource.common.base_collector import BaseCollector
from app.services.resource.common.resource_model import LambdaFunction

class LambdaCollector(BaseCollector):
    """
    Lambda 함수 데이터 수집기
    """
    
    def _init_clients(self) -> None:
        """
        필요한 AWS 클라이언트 초기화
        """
        self.lambda_client = self.get_client('lambda')
        self.cloudwatch = self.get_client('cloudwatch')
        self.logs_client = self.get_client('logs')
    
    def collect(self, collection_id: str = None) -> Dict[str, Any]:
        """
        Lambda 함수 데이터 수집
        
        Args:
            collection_id: 수집 ID (선택 사항)
            
        Returns:
            Dict[str, Any]: 수집된 Lambda 데이터
        """
        log_prefix = f"[{collection_id}] " if collection_id else ""
        self.logger.info(f"{log_prefix}Lambda 데이터 수집 시작")
        
        try:
            current_time = datetime.now(pytz.UTC)
            response = self.lambda_client.list_functions()
            functions = []
            
            self.logger.info(f"{log_prefix}Lambda 함수 {len(response.get('Functions', []))}개 발견")
            
            for function_data in response.get('Functions', []):
                try:
                    function = self._process_function(function_data, current_time, log_prefix)
                    
                    # datetime 객체를 문자열로 변환
                    function_dict = function.to_dict()
                    if 'last_modified' in function_dict and isinstance(function_dict['last_modified'], datetime):
                        function_dict['last_modified'] = function_dict['last_modified'].isoformat()
                    
                    functions.append(function_dict)
                except Exception as func_error:
                    self.logger.error(f"{log_prefix}함수 {function_data.get('FunctionName', 'Unknown')} 처리 중 오류: {str(func_error)}")
                    continue
            
            # 런타임별 요약 정보
            runtime_summary = {}
            for function in functions:
                runtime = function['runtime']
                if runtime not in runtime_summary:
                    runtime_summary[runtime] = {'count': 0, 'total_size': 0}
                runtime_summary[runtime]['count'] += 1
                runtime_summary[runtime]['total_size'] += function.get('code_size', 0)
            
            result = {
                'functions': functions,
                'summary': {
                    'total_functions': len(functions),
                    'runtime_summary': runtime_summary,
                    'total_code_size': sum(f.get('code_size', 0) for f in functions)
                }
            }
            
            self.logger.info(f"{log_prefix}Lambda 함수 {len(functions)}개 데이터 수집 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"{log_prefix}Lambda 데이터 수집 중 오류 발생: {str(e)}")
            return {
                'functions': [],
                'summary': {
                    'total_functions': 0,
                    'runtime_summary': {},
                    'total_code_size': 0
                },
                'error': str(e)
            }
    
    def _process_function(self, function_data: Dict[str, Any], current_time: datetime, log_prefix: str) -> LambdaFunction:
        """
        Lambda 함수 데이터 처리
        
        Args:
            function_data: Lambda 함수 원시 데이터
            current_time: 현재 시간
            log_prefix: 로그 접두사
            
        Returns:
            LambdaFunction: 처리된 Lambda 함수 객체
        """
        function_name = function_data['FunctionName']
        self.logger.debug(f"{log_prefix}함수 처리 중: {function_name}")
        
        # 기본 함수 정보로 객체 생성
        function = LambdaFunction(
            id=function_name,  # ResourceModel의 id 필드 필요
            name=function_name,
            region=self.region,
            runtime=function_data['Runtime'],
            handler=function_data['Handler'],
            code_size=function_data['CodeSize'],
            description=function_data.get('Description', ''),
            timeout=function_data['Timeout'],
            memory_size=function_data['MemorySize'],
            last_modified=datetime.fromisoformat(function_data['LastModified'].replace('Z', '+00:00')),
            version=function_data['Version'],
            role=function_data['Role']
        )
        
        # 추가 함수 정보 수집
        self._collect_function_configuration(function, log_prefix)
        self._collect_function_metrics(function, current_time, log_prefix)
        self._collect_function_tags(function, log_prefix)
        
        return function
    
    def _collect_function_configuration(self, function: LambdaFunction, log_prefix: str) -> None:
        """
        함수 구성 정보 수집
        
        Args:
            function: Lambda 함수 객체
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}함수 구성 정보 수집 중: {function.name}")
        try:
            config = self.lambda_client.get_function_configuration(FunctionName=function.name)
            
            function.environment_variables = config.get('Environment', {}).get('Variables', {})
            function.layers = [layer['Arn'] for layer in config.get('Layers', [])]
            function.dead_letter_config = config.get('DeadLetterConfig', {})
            function.tracing_config = config.get('TracingConfig', {})
            function.vpc_config = config.get('VpcConfig', {})
            
            # AWS 콘솔과 동일한 구성 정보 추가
            function.ephemeral_storage = config.get('EphemeralStorage', {}).get('Size', 512)
            function.snap_start = config.get('SnapStart', {}).get('ApplyOn', 'None')
            function.architectures = config.get('Architectures', ['x86_64'])
            
        except Exception as e:
            self.logger.error(f"{log_prefix}함수 구성 정보 수집 중 오류 발생: {str(e)}")
    
    def _collect_function_metrics(self, function: LambdaFunction, current_time: datetime, log_prefix: str) -> None:
        """
        함수 메트릭 수집
        
        Args:
            function: Lambda 함수 객체
            current_time: 현재 시간
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}함수 메트릭 수집 중: {function.name}")
        try:
            end_time = current_time
            start_time = end_time - timedelta(hours=24)
            
            # 호출 횟수
            invocations = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': function.name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            
            # 오류 횟수
            errors = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                Dimensions=[{'Name': 'FunctionName', 'Value': function.name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            
            # 실행 시간
            duration = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Duration',
                Dimensions=[{'Name': 'FunctionName', 'Value': function.name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average', 'Maximum']
            )
            
            # 메트릭 데이터 저장
            if invocations['Datapoints']:
                function.invocations = int(sum(point['Sum'] for point in invocations['Datapoints']))
            else:
                function.invocations = 0
            
            if errors['Datapoints']:
                function.errors = int(sum(point['Sum'] for point in errors['Datapoints']))
            else:
                function.errors = 0
            
            if duration['Datapoints']:
                latest_duration = max(duration['Datapoints'], key=lambda x: x['Timestamp'])
                function.avg_duration = latest_duration['Average']
                function.max_duration = latest_duration['Maximum']
            else:
                function.avg_duration = None
                function.max_duration = None
            
        except Exception as e:
            self.logger.error(f"{log_prefix}함수 메트릭 수집 중 오류 발생: {str(e)}")
    
    def _collect_function_tags(self, function: LambdaFunction, log_prefix: str) -> None:
        """
        함수 태그 수집
        
        Args:
            function: Lambda 함수 객체
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}함수 태그 수집 중: {function.name}")
        try:
            # Lambda 함수 ARN 생성 - role ARN에서 account ID 추출
            if ':' in function.role:
                account_id = function.role.split(':')[4]
                function_arn = f"arn:aws:lambda:{self.region}:{account_id}:function:{function.name}"
                tags_response = self.lambda_client.list_tags(Resource=function_arn)
                function.tags = [{'Key': k, 'Value': v} for k, v in tags_response.get('Tags', {}).items()]
            else:
                function.tags = []
            
        except Exception as e:
            self.logger.debug(f"{log_prefix}함수 태그 수집 중 오류 발생 (무시): {str(e)}")
            function.tags = []