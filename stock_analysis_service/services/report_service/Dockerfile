FROM hyperasset-base:latest

# 서비스별 코드만 복사
COPY stock_analysis_service/services/report_service/ ./services/report_service/

# 포트 노출
EXPOSE 8004

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Report Service 실행
CMD ["python", "services/report_service/report_service.py"]