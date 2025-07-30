# HyperAsset LLM Stock Analysis System
# Production Dockerfile for Google Cloud Run

FROM python:3.11-slim

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 환경 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENV=production

# Python 의존성 설치 (캐시 최적화)
COPY requirements_final.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_final.txt

# 애플리케이션 코드 복사 (상위 디렉토리에서)
COPY . .

# ChromaDB 데이터 디렉토리 생성
RUN mkdir -p /tmp/chroma

# 포트 노출
EXPOSE 8005

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "1"] 