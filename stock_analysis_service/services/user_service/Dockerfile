FROM hyperasset-base:latest

# 서비스별 코드만 복사
COPY stock_analysis_service/services/user_service/ ./services/user_service/

# 포트 노출
EXPOSE 8006

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# User Service 실행
CMD ["python", "services/user_service/user_service.py"]
