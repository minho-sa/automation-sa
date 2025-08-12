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
        
        # 권한 확인
        if not self._check_permissions(log_prefix):
            return {
                'functions': [],
                'summary': {
                    'total_functions': 0,
                    'runtime_summary': {},
                    'total_code_size': 0
                },
                'error': 'Lambda 서비스에 대한 권한이 부족합니다. lambda:ListFunctions 권한이 필요합니다.'
            }
        
        try:
            current_time = datetime.now(pytz.UTC)
            response = self.lambda_client.list_functions()
            functions = []
            
            self.logger.info(f"{log_prefix}Lambda 함수 {len(response.get('Functions', []))}개 발견")
            
            for function_data in response.get('Functions', []):
                function_name = function_data.get('FunctionName', 'Unknown')
                try:
                    self.logger.debug(f"{log_prefix}함수 처리 시작: {function_name}")
                    # AWS API 응답 데이터 로그 추가
                    code_size_from_api = function_data.get('CodeSize', 0)
                    self.logger.info(f"{log_prefix}AWS API에서 받은 코드 크기: {function_name} = {code_size_from_api} bytes")
                    function = self._process_function(function_data, current_time, log_prefix)
                    
                    # datetime 객체를 문자열로 변환
                    function_dict = function.to_dict()
                    if 'last_modified' in function_dict and isinstance(function_dict['last_modified'], datetime):
                        function_dict['last_modified'] = function_dict['last_modified'].isoformat()
                    
                    # 코드 크기 로그 추가
                    code_size = function_dict.get('code_size', 0)
                    self.logger.info(f"{log_prefix}함수 처리 완료: {function_name}, 코드 크기: {code_size} bytes")
                    self.logger.debug(f"{log_prefix}함수 데이터 전체: {function_dict}")
                    
                    functions.append(function_dict)
                    self.logger.debug(f"{log_prefix}함수 처리 완료: {function_name}")
                    
                except Exception as func_error:
                    self.logger.error(f"{log_prefix}함수 {function_name} 처리 중 오류: {str(func_error)}")
                    # 오류가 발생해도 기본 정보만으로 추가
                    try:
                        code_size = function_data.get('CodeSize', 0)
                        self.logger.info(f"{log_prefix}기본 함수 정보 생성: {function_name}, 코드 크기: {code_size} bytes")
                        
                        basic_function = {
                            'id': function_name,
                            'name': function_name,
                            'region': self.region,
                            'runtime': function_data.get('Runtime', 'unknown'),
                            'handler': function_data.get('Handler', 'unknown'),
                            'code_size': code_size,
                            'description': function_data.get('Description', ''),
                            'timeout': function_data.get('Timeout', 0),
                            'memory_size': function_data.get('MemorySize', 0),
                            'last_modified': function_data.get('LastModified', ''),
                            'version': function_data.get('Version', ''),
                            'role': function_data.get('Role', ''),
                            'tags': [],
                            'error': str(func_error)
                        }
                        functions.append(basic_function)
                    except Exception as basic_error:
                        self.logger.error(f"{log_prefix}기본 함수 정보 생성 실패: {str(basic_error)}")
                    continue
            
            # 런타임별 요약 정보
            runtime_summary = {}
            total_code_size = 0
            
            self.logger.info(f"{log_prefix}코드 크기 합계 계산 시작, 총 {len(functions)}개 함수")
            
            for i, function in enumerate(functions):
                runtime = function['runtime']
                code_size = function.get('code_size', 0)
                function_name = function.get('name', f'function_{i}')
                
                # 각 함수의 코드 크기 로그
                self.logger.info(f"{log_prefix}함수 {function_name}: {code_size} bytes")
                
                if runtime not in runtime_summary:
                    runtime_summary[runtime] = {'count': 0, 'total_size': 0}
                runtime_summary[runtime]['count'] += 1
                runtime_summary[runtime]['total_size'] += code_size
                total_code_size += code_size
            
            # 디버깅 로그 추가
            self.logger.info(f"{log_prefix}총 코드 크기 계산 완료: {total_code_size} bytes ({total_code_size / 1024 / 1024:.2f} MB)")
            self.logger.info(f"{log_prefix}런타임별 요약: {runtime_summary}")
            
            result = {
                'functions': functions,
                'summary': {
                    'total_functions': len(functions),
                    'runtime_summary': runtime_summary,
                    'total_code_size': total_code_size
                }
            }
            
            # 최종 결과 로그 추가
            self.logger.info(f"{log_prefix}Lambda 함수 {len(functions)}개 데이터 수집 완료")
            self.logger.info(f"{log_prefix}최종 결과 - 총 함수: {result['summary']['total_functions']}, 총 코드 크기: {result['summary']['total_code_size']} bytes")
            
            # 개별 함수의 코드 크기 로그 (처음 3개만)
            for i, func in enumerate(functions[:3]):
                self.logger.info(f"{log_prefix}함수 {i+1}: {func.get('name', 'Unknown')} - {func.get('code_size', 0)} bytes")
            
            return result
            
        except Exception as e:
            self.logger.error(f"{log_prefix}Lambda 데이터 수집 중 전체 오류 발생: {str(e)}")
            # 부분적으로라도 수집된 데이터가 있으면 반환
            if 'functions' in locals() and functions:
                self.logger.info(f"{log_prefix}오류 발생했지만 {len(functions)}개 함수 데이터는 수집 완료")
                runtime_summary = {}
                total_code_size = 0
                
                for function in functions:
                    runtime = function.get('runtime', 'unknown')
                    code_size = function.get('code_size', 0)
                    
                    if runtime not in runtime_summary:
                        runtime_summary[runtime] = {'count': 0, 'total_size': 0}
                    runtime_summary[runtime]['count'] += 1
                    runtime_summary[runtime]['total_size'] += code_size
                    total_code_size += code_size
                
                self.logger.info(f"{log_prefix}부분 오류 발생했지만 총 코드 크기: {total_code_size} bytes")
                self.logger.info(f"{log_prefix}부분 오류 시 런타임별 요약: {runtime_summary}")
                
                result = {
                    'functions': functions,
                    'summary': {
                        'total_functions': len(functions),
                        'runtime_summary': runtime_summary,
                        'total_code_size': total_code_size
                    },
                    'partial_error': str(e)
                }
                
                # 부분 오류 시에도 최종 결과 로그
                self.logger.info(f"{log_prefix}부분 오류 발생했지만 최종 결과 - 총 함수: {result['summary']['total_functions']}, 총 코드 크기: {result['summary']['total_code_size']} bytes")
                
                return result
            else:
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
        try:
            last_modified_str = function_data['LastModified']
            if isinstance(last_modified_str, str):
                # ISO 형식 문자열을 datetime으로 변환
                if last_modified_str.endswith('Z'):
                    last_modified_str = last_modified_str.replace('Z', '+00:00')
                last_modified = datetime.fromisoformat(last_modified_str)
            else:
                # 이미 datetime 객체인 경우
                last_modified = last_modified_str
        except Exception as date_error:
            self.logger.warning(f"{log_prefix}날짜 변환 오류: {str(date_error)}")
            last_modified = datetime.now(pytz.UTC)
        
        code_size = function_data.get('CodeSize', 0)
        self.logger.info(f"{log_prefix}LambdaFunction 객체 생성: {function_name}, 코드 크기: {code_size} bytes")
        
        function = LambdaFunction(
            id=function_name,  # ResourceModel의 id 필드 필요
            name=function_name,
            region=self.region,
            runtime=function_data.get('Runtime', 'unknown'),
            handler=function_data.get('Handler', 'unknown'),
            code_size=code_size,
            description=function_data.get('Description', ''),
            timeout=function_data.get('Timeout', 0),
            memory_size=function_data.get('MemorySize', 0),
            last_modified=last_modified,
            version=function_data.get('Version', ''),
            role=function_data.get('Role', '')
        )
        
        # 객체 생성 후 코드 크기 확인
        self.logger.info(f"{log_prefix}LambdaFunction 객체 생성 후 코드 크기: {function.code_size} bytes")
        
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
        
        # 기본값 설정
        function.environment_variables = {}
        function.layers = []
        function.dead_letter_config = {}
        function.tracing_config = {}
        function.vpc_config = {}
        function.ephemeral_storage = 512
        function.snap_start = "None"
        function.architectures = ['x86_64']
        
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
            self.logger.warning(f"{log_prefix}함수 구성 정보 수집 중 오류 발생: {str(e)}")
    
    def _collect_function_metrics(self, function: LambdaFunction, current_time: datetime, log_prefix: str) -> None:
        """
        함수 메트릭 수집
        
        Args:
            function: Lambda 함수 객체
            current_time: 현재 시간
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}함수 메트릭 수집 중: {function.name}")
        
        # 기본값 설정
        function.invocations = 0
        function.errors = 0
        function.avg_duration = None
        function.max_duration = None
        
        try:
            end_time = current_time
            start_time = end_time - timedelta(hours=24)
            
            # 호출 횟수 수집
            try:
                invocations = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function.name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum']
                )
                if invocations.get('Datapoints'):
                    function.invocations = int(sum(point['Sum'] for point in invocations['Datapoints']))
            except Exception as e:
                self.logger.debug(f"{log_prefix}호출 횟수 메트릭 수집 실패: {str(e)}")
            
            # 오류 횟수 수집
            try:
                errors = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Errors',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function.name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum']
                )
                if errors.get('Datapoints'):
                    function.errors = int(sum(point['Sum'] for point in errors['Datapoints']))
            except Exception as e:
                self.logger.debug(f"{log_prefix}오류 횟수 메트릭 수집 실패: {str(e)}")
            
            # 실행 시간 수집
            try:
                duration = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Duration',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function.name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Average', 'Maximum']
                )
                if duration.get('Datapoints'):
                    latest_duration = max(duration['Datapoints'], key=lambda x: x['Timestamp'])
                    function.avg_duration = latest_duration.get('Average')
                    function.max_duration = latest_duration.get('Maximum')
            except Exception as e:
                self.logger.debug(f"{log_prefix}실행 시간 메트릭 수집 실패: {str(e)}")
            
        except Exception as e:
            self.logger.warning(f"{log_prefix}함수 메트릭 수집 중 전체 오류 발생: {str(e)}")
    
    def _collect_function_tags(self, function: LambdaFunction, log_prefix: str) -> None:
        """
        함수 태그 수집
        
        Args:
            function: Lambda 함수 객체
            log_prefix: 로그 접두사
        """
        self.logger.debug(f"{log_prefix}함수 태그 수집 중: {function.name}")
        try:
            # Lambda 함수 ARN 생성
            function_arn = f"arn:aws:lambda:{self.region}:{self._get_account_id()}:function:{function.name}"
            tags_response = self.lambda_client.list_tags(Resource=function_arn)
            function.tags = [{'Key': k, 'Value': v} for k, v in tags_response.get('Tags', {}).items()]
            
        except Exception as e:
            self.logger.debug(f"{log_prefix}함수 태그 수집 중 오류 발생 (무시): {str(e)}")
            function.tags = []
    
    def _get_account_id(self) -> str:
        """
        현재 AWS 계정 ID 가져오기
        
        Returns:
            str: AWS 계정 ID
        """
        try:
            sts_client = self.get_client('sts')
            response = sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            self.logger.warning(f"계정 ID 조회 실패: {str(e)}")
            return "000000000000"
    
    def _check_permissions(self, log_prefix: str) -> bool:
        """
        Lambda 서비스 접근 권한 확인
        
        Args:
            log_prefix: 로그 접두사
            
        Returns:
            bool: 권한 유무
        """
        try:
            # 간단한 권한 확인 - 함수 목록 조회 시도
            self.lambda_client.list_functions(MaxItems=1)
            self.logger.debug(f"{log_prefix}Lambda 권한 확인 성공")
            return True
        except Exception as e:
            error_msg = str(e)
            if 'AccessDenied' in error_msg or 'UnauthorizedOperation' in error_msg:
                self.logger.error(f"{log_prefix}Lambda 접근 권한 부족: {error_msg}")
            else:
                self.logger.error(f"{log_prefix}Lambda 권한 확인 중 오류: {error_msg}")
            return False