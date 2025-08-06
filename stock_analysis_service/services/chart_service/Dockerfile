FROM hyperasset-base:latest

# 서비스별 코드만 복사
COPY stock_analysis_service/services/chart_service/ ./services/chart_service/

# 포트 노출
EXPOSE 8003

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Chart Service 실행
CMD ["python", "services/chart_service/chart_service.py"]