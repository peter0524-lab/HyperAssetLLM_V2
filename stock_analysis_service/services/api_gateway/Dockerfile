FROM hyperasset-base:latest

# 서비스별 코드만 복사
COPY stock_analysis_service/services/api_gateway/ ./services/api_gateway/

# 포트 노출
EXPOSE 8005

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# API Gateway 실행
CMD ["python", "services/api_gateway/main.py"]