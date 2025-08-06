FROM hyperasset-base:latest

# 서비스별 코드만 복사
COPY stock_analysis_service/services/news_service/ ./services/news_service/

# 포트 노출
EXPOSE 8001

# ChromaDB 데이터 디렉토리 (볼륨 마운트용)
VOLUME ["/app/data/chroma"]

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# News Service 실행
CMD ["python", "services/news_service/main.py"]