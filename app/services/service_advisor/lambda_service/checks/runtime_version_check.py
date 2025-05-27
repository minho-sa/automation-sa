import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    Lambda 함수가 최신 런타임 버전을 사용하고 있는지 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        
        # Lambda 함수 목록 가져오기
        functions = lambda_client.list_functions()
        
        # 최신 런타임 버전 정의 (2023년 기준 최신 버전)
        latest_runtimes = {
            'nodejs': 'nodejs22.x',  # Node.js 22가 최신
            'python': 'python3.13',  # Python 3.13이 최신
            'java': 'java21',        # Java 21이 최신
            'dotnet': 'dotnet8',     # .NET 8이 최신 (dotnet9은 컨테이너만 해당)
            'ruby': 'ruby3.4',       # Ruby 3.4가 최신
            'provided': 'provided.al2023'  # Amazon Linux 2023 기반 OS 전용 런타임
        }
        
        # 지원 종료 예정 런타임 (2025년 내에 지원 종료 예정인 런타임)
        deprecated_runtimes = [
            'nodejs18.x',  # 2025년 9월 1일 지원 종료
            'python3.9',   # 2025년 11월 3일 지원 종료
        ]
        
        # 곧 지원 종료 예정 런타임 (2026년 내에 지원 종료 예정인 런타임)
        soon_deprecated_runtimes = [
            'nodejs20.x',  # 2026년 4월 30일 지원 종료
            'python3.11',  # 2026년 6월 30일 지원 종료
            'python3.10',  # 2026년 6월 30일 지원 종료
            'java17',      # 2026년 6월 30일 지원 종료
            'java11',      # 2026년 6월 30일 지원 종료
            'java8.al2',   # 2026년 6월 30일 지원 종료
            'ruby3.2',     # 2026년 3월 31일 지원 종료
            'provided.al2' # 2026년 6월 30일 지원 종료
        ]
        
        # 런타임 업데이트가 필요한 함수 목록
        outdated_functions = []
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            runtime = function.get('Runtime', 'custom')
            
            if runtime == 'custom':
                continue  # 컨테이너 이미지 기반 함수는 건너뜀
            
            # 런타임 접두사 추출 (예: nodejs22.x -> nodejs)
            runtime_prefix = ''.join(c for c in runtime if not c.isdigit() and c != '.')
            
            status = "최신"
            recommendation = "현재 최신 런타임을 사용 중입니다."
            
            # 지원 종료 예정 런타임 확인 (2025년 내)
            if runtime in deprecated_runtimes:
                status = "지원 종료 임박"
                recommendation = f"현재 런타임({runtime})은 2025년 내에 지원 종료 예정입니다. 최신 버전({latest_runtimes.get(runtime_prefix, '최신 버전')})으로 업그레이드하세요."
            # 곧 지원 종료 예정 런타임 확인 (2026년 내)
            elif runtime in soon_deprecated_runtimes:
                status = "지원 종료 예정"
                recommendation = f"현재 런타임({runtime})은 2026년 내에 지원 종료 예정입니다. 최신 버전({latest_runtimes.get(runtime_prefix, '최신 버전')})으로 업그레이드를 계획하세요."
            # 최신 버전이 아닌 경우
            elif runtime_prefix in latest_runtimes and runtime != latest_runtimes[runtime_prefix]:
                status = "업데이트 권장"
                recommendation = f"현재 런타임({runtime})보다 더 최신 버전({latest_runtimes[runtime_prefix]})이 있습니다. 업그레이드를 고려하세요."
            
            if status != "최신":
                outdated_functions.append({
                    'function_name': function_name,
                    'current_runtime': runtime,
                    'recommended_runtime': latest_runtimes.get(runtime_prefix, "알 수 없음"),
                    'status': status,
                    'recommendation': recommendation
                })
        
        # 결과 생성
        if outdated_functions:
            return {
                'status': 'warning',
                'data': {
                    'functions': outdated_functions
                },
                'recommendations': [
                    '지원 종료가 임박한 런타임은 보안 업데이트가 중단될 수 있으므로 우선적으로 업그레이드하세요.',
                    '최신 런타임 버전은 성능 향상과 새로운 기능을 제공합니다.',
                    '런타임 업그레이드 시 코드 호환성을 확인하세요.',
                    '새로운 런타임 버전으로 테스트 환경에서 먼저 테스트한 후 프로덕션에 적용하세요.',
                    'Amazon Linux 2023 기반 런타임(nodejs22.x, python3.13 등)은 더 긴 지원 기간을 제공합니다.'
                ],
                'message': f'{len(outdated_functions)}개의 Lambda 함수가 최신 런타임 버전을 사용하지 않고 있습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {},
                'recommendations': [],
                'message': '모든 Lambda 함수가 최신 런타임 버전을 사용하고 있습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'런타임 버전 검사 중 오류가 발생했습니다: {str(e)}'
        }