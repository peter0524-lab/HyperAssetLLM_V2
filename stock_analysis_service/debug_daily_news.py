#!/usr/bin/env python3
"""
daily_news ChromaDB 저장 문제 디버깅 스크립트
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database.vector_db import VectorDBClient
from services.news_service.main import NewsService
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_daily_news():
    """daily_news 저장 문제 디버깅"""
    try:
        # 1. ChromaDB 클라이언트 초기화
        logger.info("🔧 ChromaDB 클라이언트 초기화")
        vector_db = VectorDBClient()
        
        # 2. daily_news 컬렉션 클린업
        logger.info("🧹 daily_news 컬렉션 클린업 시작")
        cleanup_count = vector_db.cleanup_daily_news()
        logger.info(f"🧹 클린업 완료: {cleanup_count}개 삭제")
        
        # 3. 클린업 후 상태 확인
        stats = vector_db.get_collection_stats()
        daily_news_count = stats.get("daily_news", {}).get("count", 0)
        logger.info(f"🔍 클린업 후 daily_news 개수: {daily_news_count}")
        
        # 4. 뉴스 서비스 초기화
        logger.info("📰 뉴스 서비스 초기화")
        news_service = NewsService()
        
        # 5. 한 종목만 테스트 (006800 - 미래에셋증권)
        test_stock_code = "006800"
        logger.info(f"🎯 테스트 종목: {test_stock_code}")
        
        # 6. 뉴스 크롤링 및 저장
        logger.info("🚀 뉴스 크롤링 및 저장 시작")
        await news_service.crawl_news_for_stock(test_stock_code)
        
        # 7. 저장 후 상태 확인
        stats_after = vector_db.get_collection_stats()
        daily_news_count_after = stats_after.get("daily_news", {}).get("count", 0)
        logger.info(f"🔍 저장 후 daily_news 개수: {daily_news_count_after}")
        
        # 8. 실제 저장된 문서 확인
        logger.info("📋 실제 저장된 문서 확인")
        documents = vector_db.get_all_documents("daily_news", limit=100)
        
        logger.info(f"📊 실제 조회된 문서 수: {len(documents)}")
        
        # 9. 문서 상세 정보 출력
        for i, doc in enumerate(documents[:10], 1):  # 상위 10개만 출력
            logger.info(f"📄 [{i}] ID: {doc.get('id', 'NO_ID')}")
            logger.info(f"    제목: {doc.get('metadata', {}).get('title', 'NO_TITLE')[:50]}")
            logger.info(f"    종목: {doc.get('metadata', {}).get('stock_code', 'NO_STOCK')}")
            logger.info(f"    시간: {doc.get('metadata', {}).get('created_at', 'NO_TIME')}")
            logger.info(f"    ---")
        
        # 10. ID 중복 확인
        ids = [doc.get('id') for doc in documents]
        unique_ids = set(ids)
        logger.info(f"🔍 ID 중복 확인: 총 {len(ids)}개 중 고유한 ID {len(unique_ids)}개")
        
        if len(ids) != len(unique_ids):
            logger.warning("⚠️ ID 중복 발견!")
            duplicates = [id for id in ids if ids.count(id) > 1]
            logger.warning(f"중복 ID: {set(duplicates)}")
        else:
            logger.info("✅ ID 중복 없음")
        
        # 11. 종료
        news_service.close_driver()
        logger.info("✅ 디버깅 완료")
        
    except Exception as e:
        logger.error(f"❌ 디버깅 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(debug_daily_news()) 