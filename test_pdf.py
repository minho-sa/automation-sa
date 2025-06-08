"""
PDF 생성 테스트 스크립트
"""
import json
from app.utils.pdf_generator import generate_check_result_pdf

# 테스트 데이터
test_data = {
    "metadata": {
        "username": "admin", 
        "service_name": "ec2", 
        "check_id": "ec2-instance-type", 
        "timestamp": "2025-06-08T13:17:44.143214"
    }, 
    "result": {
        "id": "ec2-instance-type", 
        "status": "warning", 
        "message": "2\uac1c \uc778\uc2a4\ud134\uc2a4 \uc911 1\uac1c\uac00 \ucd5c\uc801\ud654\uac00 \ud544\uc694\ud569\ub2c8\ub2e4.", 
        "resources": [
            {
                "id": "i-0787a481d5ad3daed", 
                "name": "ttt", 
                "status": "fail", 
                "status_text": "\ucd5c\uc801\ud654 \ud544\uc694", 
                "advice": "CPU \uc0ac\uc6a9\ub960\uc774 \ub0ae\uc2b5\ub2c8\ub2e4(\ud3c9\uade0: 0.41%, \ucd5c\ub300: 26.78%). \uc774 \uc778\uc2a4\ud134\uc2a4\ub294 \uacfc\ub2e4 \ud504\ub85c\ube44\uc800\ub2dd\ub418\uc5b4 \uc788\uc2b5\ub2c8\ub2e4."
            }, 
            {
                "id": "i-0c85364be4c503455", 
                "name": "chat", 
                "status": "pass", 
                "status_text": "\ucd5c\uc801\ud654\ub428", 
                "advice": "CPU \uc0ac\uc6a9\ub960(\ud3c9\uade0: 4.85%, \ucd5c\ub300: 64.94%)\uc774 \uc801\uc808\ud55c \ubc94\uc704(10-80%) \ub0b4\uc5d0 \uc788\uc2b5\ub2c8\ub2e4."
            }
        ], 
        "recommendations": [
            "CPU \uc0ac\uc6a9\ub960\uc774 10% \ubbf8\ub9cc\uc778 \uc778\uc2a4\ud134\uc2a4\ub294 \ub354 \uc791\uc740 \uc778\uc2a4\ud134\uc2a4 \ud0c0\uc785\uc73c\ub85c \ubcc0\uacbd\ud558\uc5ec \ube44\uc6a9\uc744 \uc808\uac10\ud558\uc138\uc694.", 
            "CPU \uc0ac\uc6a9\ub960\uc774 80% \uc774\uc0c1\uc778 \uc778\uc2a4\ud134\uc2a4\ub294 \ub354 \ud070 \uc778\uc2a4\ud134\uc2a4 \ud0c0\uc785\uc73c\ub85c \ubcc0\uacbd\ud558\uc5ec \uc131\ub2a5\uc744 \uac1c\uc120\ud558\uc138\uc694.", 
            "\uc608\uc57d \uc778\uc2a4\ud134\uc2a4 \ub610\ub294 Savings Plans\ub97c \uace0\ub824\ud558\uc5ec \ube44\uc6a9\uc744 \uc808\uac10\ud558\uc138\uc694.", 
            "\uc778\uc2a4\ud134\uc2a4 \ud06c\uae30 \uc870\uc815 \uc2dc CPU \uc678\uc5d0\ub3c4 \uba54\ubaa8\ub9ac, \ub124\ud2b8\uc6cc\ud06c, \ub514\uc2a4\ud06c I/O \ub4f1 \ub2e4\ub978 \uc131\ub2a5 \uc9c0\ud45c\ub3c4 \ud568\uaed8 \uace0\ub824\ud558\uc138\uc694."
        ], 
        "problem_count": 1, 
        "total_count": 2
    }
}

# 테스트 실행
check_info = {
    "name": "EC2 인스턴스 타입 최적화 검사",
    "description": "EC2 인스턴스의 CPU 사용률을 분석하여 인스턴스 타입이 적절하게 선택되었는지 확인합니다."
}

# PDF 생성
pdf_buffer = generate_check_result_pdf(
    test_data["result"],
    test_data["metadata"]["service_name"],
    test_data["metadata"]["check_id"],
    check_info,
    test_data["metadata"]["username"],
    test_data["metadata"]["timestamp"]
)

# PDF 파일로 저장
with open('test_result.pdf', 'wb') as f:
    f.write(pdf_buffer.getvalue())

print("PDF 생성 완료: test_result.pdf")