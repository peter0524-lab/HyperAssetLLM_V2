# Business Report Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 환경 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENV=production

# Python 의존성 설치
COPY requirements_final.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_final.txt

# 전체 프로젝트 복사
COPY . .

# 포트 노출
EXPOSE 8007

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

# Business Report Service 실행
CMD ["python", "services/business_report_service/business_report_service.py"]