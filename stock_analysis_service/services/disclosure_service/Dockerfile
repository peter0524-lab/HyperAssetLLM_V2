FROM hyperasset-base:latest

# 서비스별 코드만 복사
COPY stock_analysis_service/services/disclosure_service/ ./services/disclosure_service/

# 포트 노출
EXPOSE 8002

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Disclosure Service 실행
CMD ["python", "services/disclosure_service/disclosure_service.py"]