import boto3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from app.services.service_advisor.aws_client import create_boto3_client
from app.services.service_advisor.check_result import (
    create_check_result, create_resource_result,
    create_error_result, STATUS_OK, STATUS_WARNING, STATUS_ERROR,
    RESOURCE_STATUS_PASS, RESOURCE_STATUS_FAIL, RESOURCE_STATUS_WARNING, RESOURCE_STATUS_UNKNOWN
)

def run() -> Dict[str, Any]:
    """
    Lambda 함수의 런타임 버전이 최신인지 검사하고 업그레이드 방안을 제안합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        
        # Lambda 함수 정보 수집
        functions = lambda_client.list_functions()
        
        # 함수 분석 결과
        function_analysis = []
        
        # 오래된 런타임 버전 정의
        outdated_runtimes = {
            'nodejs10.x': 'Node.js 14.x 이상',
            'nodejs12.x': 'Node.js 14.x 이상',
            'python2.7': 'Python 3.8 이상',
            'python3.6': 'Python 3.8 이상',
            'python3.7': 'Python 3.8 이상',
            'ruby2.5': 'Ruby 2.7 이상',
            'java8': 'Java 11 이상',
            'dotnetcore2.1': '.NET Core 3.1 이상',
            'dotnetcore3.1': '.NET 6 이상'
        }
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            runtime = function.get('Runtime', 'Container Image')
            
            # 함수 태그 가져오기
            try:
                tags_response = lambda_client.list_tags(Resource=function['FunctionArn'])
                tags = tags_response.get('Tags', {})
            except Exception:
                tags = {}
            
            # 런타임 버전 분석
            status = RESOURCE_STATUS_PASS  # 기본값은 통과
            advice = None
            status_text = None
            
            # 컨테이너 이미지 기반 함수는 건너뜀
            if runtime == 'Container Image':
                status = RESOURCE_STATUS_PASS
                status_text = '컨테이너 이미지'
                advice = '컨테이너 이미지 기반 함수는 런타임 버전을 직접 관리해야 합니다. 컨테이너 내 런타임이 최신 버전인지 확인하세요.'
            # 오래된 런타임 버전 검사
            elif runtime in outdated_runtimes:
                status = RESOURCE_STATUS_FAIL
                status_text = '업그레이드 필요'
                advice = f'런타임 버전({runtime})이 오래되었습니다. {outdated_runtimes[runtime]}으로 업그레이드하세요.'
            else:
                status_text = '최신 버전'
                advice = f'현재 런타임 버전({runtime})은 최신 상태입니다.'
            
            # 표준화된 리소스 결과 생성
            function_result = create_resource_result(
                resource_id=function_name,
                status=status,
                advice=advice,
                status_text=status_text,
                function_name=function_name,
                runtime=runtime,
                recommended_runtime=outdated_runtimes.get(runtime, '해당 없음')
            )
            
            function_analysis.append(function_result)
        
        # 결과 분류
        passed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_PASS]
        failed_functions = [f for f in function_analysis if f['status'] == RESOURCE_STATUS_FAIL]
        
        # 업그레이드 필요 함수 카운트
        upgrade_needed_count = len(failed_functions)
        
        # 권장사항 생성 (문자열 배열)
        recommendations = []
        
        # 오래된 런타임 함수 찾기
        if failed_functions:
            for runtime in outdated_runtimes.keys():
                runtime_functions = [f for f in failed_functions if f.get('runtime') == runtime]
                if runtime_functions:
                    recommendations.append(f'{runtime} 런타임을 사용하는 {len(runtime_functions)}개 함수는 {outdated_runtimes[runtime]}으로 업그레이드하세요. (영향받는 함수: {", ".join([f["function_name"] for f in runtime_functions])})')
        
        # 데이터 준비
        data = {
            'functions': function_analysis,
            'passed_functions': passed_functions,
            'failed_functions': failed_functions,
            'upgrade_needed_count': upgrade_needed_count,
            'total_functions_count': len(function_analysis)
        }
        
        # 전체 상태 결정 및 결과 생성
        if upgrade_needed_count > 0:
            message = f'{len(function_analysis)}개 함수 중 {upgrade_needed_count}개가 런타임 업그레이드가 필요합니다.'
            return create_check_result(
                status=STATUS_WARNING,
                message=message,
                data=data,
                recommendations=recommendations
            )
        else:
            message = f'모든 함수({len(passed_functions)}개)가 최신 런타임 버전을 사용하고 있습니다.'
            return create_check_result(
                status=STATUS_OK,
                message=message,
                data=data,
                recommendations=recommendations
            )
    
    except Exception as e:
        return create_error_result(f'Lambda 런타임 버전 검사 중 오류가 발생했습니다: {str(e)}')