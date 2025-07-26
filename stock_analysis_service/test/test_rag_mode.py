#!/usr/bin/env python3
"""
순수 RAG 방식 테스트 스크립트
"""

import asyncio
import logging
from services.news_service.main import NewsService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def test_rag_mode():
    """순수 RAG 방식 테스트"""
    try:
        logger.info("🧪 순수 RAG 방식 테스트 시작")
        
        # NewsService 초기화
        news_service = NewsService()
        logger.info("✅ NewsService 초기화 완료")
        
        # 테스트 뉴스 데이터
        test_news = {
            "title": "삼성전자, 3분기 실적 예상치 상회...반도체 부문 회복세",
            "content": "삼성전자가 3분기 실적이 시장 예상치를 상회했다고 발표했다. 반도체 부문에서 회복세를 보이고 있으며, 메모리 반도체 가격 상승과 수요 증가가 주요 요인으로 꼽힌다. 투자자들은 긍정적인 실적 발표에 주가 상승을 기대하고 있다.",
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "url": "https://test.com/news1",
            "source": "네이버 금융",
            "published_at": "2024-01-15 10:30:00"
        }
        
        logger.info(f"📝 테스트 뉴스: {test_news['title']}")
        logger.info(f"📊 종목: {test_news['stock_name']} ({test_news['stock_code']})")
        
        # RAG 방식 영향도 평가 테스트
        logger.info("🔍 RAG 방식 영향도 평가 시작")
        impact_score, reasoning = await news_service.evaluate_impact_with_rag(test_news)
        
        logger.info(f"✅ RAG 평가 완료:")
        logger.info(f"   • 영향도 점수: {impact_score:.3f}")
        logger.info(f"   • 분석 근거: {reasoning}")
        
        # 결과 검증
        if impact_score > 0:
            logger.info("✅ RAG 방식 정상 작동")
        else:
            logger.warning("⚠️ RAG 방식에서 낮은 점수 반환")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ RAG 방식 테스트 실패: {e}")
        return False

async def main():
    """메인 함수"""
    logger.info("🚀 순수 RAG 방식 테스트 시작")
    
    success = await test_rag_mode()
    
    if success:
        logger.info("✅ 순수 RAG 방식 테스트 성공")
    else:
        logger.error("❌ 순수 RAG 방식 테스트 실패")

if __name__ == "__main__":
    asyncio.run(main()) 