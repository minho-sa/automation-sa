import boto3
from typing import Dict, List, Any
from app.services.service_advisor.aws_client import create_boto3_client

def run() -> Dict[str, Any]:
    """
    Lambda 함수에 X-Ray 추적이 활성화되어 있는지 확인합니다.
    
    Returns:
        Dict[str, Any]: 검사 결과
    """
    try:
        lambda_client = create_boto3_client('lambda')
        
        # Lambda 함수 목록 가져오기
        functions = lambda_client.list_functions()
        
        # X-Ray 추적 검사가 필요한 함수 목록
        xray_issues = []
        
        for function in functions.get('Functions', []):
            function_name = function['FunctionName']
            tracing_config = function.get('TracingConfig', {})
            tracing_mode = tracing_config.get('Mode', 'PassThrough')
            
            # X-Ray 추적이 활성화되어 있는지 확인
            is_xray_enabled = tracing_mode == 'Active'
            
            status = "활성화" if is_xray_enabled else "비활성화"
            recommendation = "X-Ray 추적이 활성화되어 있습니다." if is_xray_enabled else "함수 모니터링 및 디버깅을 위해 X-Ray 추적을 활성화하세요."
            
            xray_issues.append({
                'function_name': function_name,
                'xray_enabled': is_xray_enabled,
                'status': status,
                'recommendation': recommendation
            })
        
        # 결과 생성
        if xray_issues:
            # X-Ray가 비활성화된 함수 수 계산
            disabled_count = sum(1 for func in xray_issues if not func['xray_enabled'])
            
            status = 'info'  # X-Ray는 선택적 기능이므로 warning이 아닌 info로 설정
            
            return {
                'status': status,
                'data': {
                    'functions': xray_issues
                },
                'recommendations': [
                    'X-Ray 추적을 활성화하여 Lambda 함수의 성능 및 오류를 모니터링하세요.',
                    'X-Ray SDK를 사용하여 다운스트림 서비스 호출을 추적하세요.',
                    'X-Ray 서비스 맵을 통해 애플리케이션 구성 요소 간의 관계를 시각화하세요.'
                ],
                'message': f'{len(xray_issues)}개의 Lambda 함수 중 {disabled_count}개가 X-Ray 추적이 비활성화되어 있습니다.'
            }
        else:
            return {
                'status': 'ok',
                'data': {},
                'recommendations': [],
                'message': 'Lambda 함수가 없습니다.'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'X-Ray 추적 검사 중 오류가 발생했습니다: {str(e)}'
        }