#!/usr/bin/env python3
"""
LLM 재시도 로직 테스트 스크립트
"""

import sys
import os
import logging
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from services.news_service.main import NewsService

async def test_llm_retry():
    """LLM 재시도 로직 테스트"""
    print("🔍 LLM 재시도 로직 테스트 시작")
    
    try:
        # NewsService 인스턴스 생성
        print("📋 NewsService 초기화 중...")
        news_service = NewsService()
        print("✅ NewsService 초기화 완료")
        
        # 테스트용 뉴스 아이템
        test_news = {
            "title": "삼성전자, 2분기 실적 발표...매출 증가세",
            "content": "삼성전자가 2분기 실적을 발표했다. 매출이 전년 동기 대비 증가세를 보이고 있다.",
            "stock_code": "005930",
            "stock_name": "삼성전자"
        }
        
        print(f"🔍 종목 관련성 평가 테스트 시작...")
        
        # 종목 관련성 평가 테스트 (재시도 로직 포함)
        is_relevant, relevance_score, reasoning = await news_service.evaluate_stock_relevance(test_news)
        
        print(f"✅ 종목 관련성 평가 결과:")
        print(f"  • 관련성: {is_relevant}")
        print(f"  • 점수: {relevance_score:.2f}")
        print(f"  • 근거: {reasoning}")
        
        print("\n✅ LLM 재시도 로직 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 에러: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_llm_retry()) 