# Orchestrator Dockerfile
FROM hyperasset-base:latest

COPY stock_analysis_service/services/orchestrator/ ./services/orchestrator/

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Orchestrator 실행
CMD ["python", "services/orchestrator/main.py"]