import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_log_prefix(collection_id: str = None) -> str:
    """로그 접두사 생성"""
    if collection_id is None:
        collection_id = "lambda-check"
    return f"[{collection_id}]"