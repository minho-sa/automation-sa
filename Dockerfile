# Python 3.9 slim 이미지 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 로그 디렉토리 생성
RUN mkdir -p logs

# 세션 디렉토리 생성
RUN mkdir -p flask_session

# 포트 5000 노출
EXPOSE 5000

# 환경 변수 설정
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# 엔트리포인트 스크립트 복사 및 권한 설정
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 엔트리포인트 설정
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# 애플리케이션 실행
CMD ["python", "run.py"]