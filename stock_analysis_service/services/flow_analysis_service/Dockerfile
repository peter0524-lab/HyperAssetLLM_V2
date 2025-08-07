FROM hyperasset-base:latest

# 서비스별 코드만 복사
COPY stock_analysis_service/services/flow_analysis_service/ ./services/flow_analysis_service/

# 포트 노출
EXPOSE 8010

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Flow Analysis Service 실행
CMD ["python", "services/flow_analysis_service/flow_analysis_service.py"]