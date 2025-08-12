#!/usr/bin/env python3
"""
Lambda 코드 크기 문제 디버깅을 위한 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.resource.lambda_collector import LambdaCollector
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_lambda_code_size():
    """Lambda 함수의 코드 크기 수집 테스트"""
    print("Lambda 코드 크기 수집 테스트 시작...")
    
    try:
        # Lambda 수집기 생성
        collector = LambdaCollector()
        
        # 데이터 수집
        result = collector.collect(collection_id="test")
        
        print(f"\n=== 수집 결과 ===")
        print(f"총 함수 개수: {result.get('summary', {}).get('total_functions', 0)}")
        print(f"총 코드 크기: {result.get('summary', {}).get('total_code_size', 0)} bytes")
        print(f"총 코드 크기 (MB): {result.get('summary', {}).get('total_code_size', 0) / 1024 / 1024:.2f} MB")
        
        # 개별 함수 정보 출력
        functions = result.get('functions', [])
        print(f"\n=== 개별 함수 정보 ===")
        for i, func in enumerate(functions[:5]):  # 처음 5개만 출력
            print(f"{i+1}. {func.get('name', 'Unknown')}: {func.get('code_size', 0)} bytes")
        
        if len(functions) > 5:
            print(f"... 총 {len(functions)}개 함수 중 5개만 표시")
        
        # 런타임별 분포
        runtime_summary = result.get('summary', {}).get('runtime_summary', {})
        print(f"\n=== 런타임별 분포 ===")
        for runtime, data in runtime_summary.items():
            print(f"{runtime}: {data.get('count', 0)}개, {data.get('total_size', 0)} bytes")
        
        return result
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_lambda_code_size()