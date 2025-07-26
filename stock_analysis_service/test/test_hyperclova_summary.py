#!/usr/bin/env python3
"""
HyperCLOVA 뉴스 요약 기능 테스트 스크립트
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.news_service.main import NewsService
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_hyperclova_summary():
    """HyperCLOVA 요약 기능 테스트"""
    try:
        logger.info("🧪 HyperCLOVA 요약 기능 테스트 시작")
        
        # 뉴스 서비스 초기화
        news_service = NewsService()
        
        # 테스트용 뉴스 데이터
        test_news = {
            "stock_code": "006800",
            "title": "미래에셋증권, 3분기 실적 전년 대비 20% 증가",
            "content": """
미래에셋증권이 3분기 실적에서 전년 동기 대비 20% 증가한 매출을 기록했다고 발표했다. 
회사는 브로커리지 수수료 증가와 투자은행 부문의 호조로 실적이 개선됐다고 설명했다. 
특히 해외 주식 거래량이 크게 늘면서 수수료 수익이 증가했다. 
투자은행 부문에서도 IPO 주관 업무와 M&A 자문 업무가 늘어 수익성이 개선됐다.
회사 관계자는 "4분기에도 이러한 성장세가 지속될 것"이라고 전망했다.
            """,
            "url": "https://example.com/news/123",
            "published_at": datetime.now()
        }
        
        # 1. 정상적인 뉴스 요약 테스트
        logger.info("📝 테스트 1: 정상적인 뉴스 요약")
        summary1 = await news_service.generate_news_summary(test_news)
        logger.info(f"✅ 결과 1: {summary1}")
        
        # 2. 내용 없는 뉴스 테스트
        logger.info("📝 테스트 2: 내용 없는 뉴스")
        test_news_no_content = test_news.copy()
        test_news_no_content["content"] = ""
        summary2 = await news_service.generate_news_summary(test_news_no_content)
        logger.info(f"✅ 결과 2: {summary2}")
        
        # 3. 제목 없는 뉴스 테스트
        logger.info("📝 테스트 3: 제목 없는 뉴스")
        test_news_no_title = test_news.copy()
        test_news_no_title["title"] = ""
        summary3 = await news_service.generate_news_summary(test_news_no_title)
        logger.info(f"✅ 결과 3: {summary3}")
        
        # 4. 매우 짧은 내용 테스트
        logger.info("📝 테스트 4: 매우 짧은 내용")
        test_news_short = test_news.copy()
        test_news_short["content"] = "짧은 내용"
        summary4 = await news_service.generate_news_summary(test_news_short)
        logger.info(f"✅ 결과 4: {summary4}")
        
        # 5. 텔레그램 메시지 형태 테스트
        logger.info("📝 테스트 5: 텔레그램 메시지 형태 확인")
        test_news["stock_info"] = {
            "종목명": "미래에셋증권",
            "현재가": "22,000",
            "등락률": "+6.28%",
            "전일": "20,700",
            "시가": "21,150",
            "고가": "23,050",
            "거래량": "1,234,567",
            "거래대금": "270억",
            "시가총액": "3.2조",
            "PER": "8.5"
        }
        
        # 텔레그램 메시지 생성 시뮬레이션
        stock_name = "미래에셋증권"
        stock_code = "006800"
        current_price = test_news["stock_info"]["현재가"]
        prev_close = test_news["stock_info"]["전일"]
        open_price = test_news["stock_info"]["시가"]
        high_price = test_news["stock_info"]["고가"]
        market_cap = test_news["stock_info"]["시가총액"]
        per_ratio = test_news["stock_info"]["PER"]
        impact_score = 0.75
        
        # 수정된 메시지 포맷 테스트
        message = f"""
🚨🔥 <b>고영향 뉴스 알림</b>

📊 <b>종목 현황</b>
• 종목: <b>{stock_name}</b> ({stock_code})
• 현재가: <b>{current_price}</b> 원
• 전일종가: {prev_close} 원
• 시가: {open_price} 원 | 고가: {high_price} 원

📈 <b>기업 정보</b>
• 시가총액: {market_cap}
• PER: {per_ratio}

📰 <b>뉴스 정보</b>
• 제목: {test_news['title']}
• 발행: {test_news['published_at'].strftime('%Y-%m-%d %H:%M:%S')}
• 출처: 테스트

🔍 <b>네이버 HyperClova의 핵심요약</b>
{summary1}

💡 <b>분석 지표</b>
• 영향도: <b>{impact_score:.2f}/1.0</b> (높음)
• 필터링: 3단계 통과
• 분석시간: {datetime.now().strftime('%H:%M:%S')}

🔗 <b>상세 보기</b>
{test_news['url']}

⚠️ <i>이 분석은 참고용이며, 투자 결정은 신중하게 하시기 바랍니다.</i>
"""
        
        logger.info("📱 수정된 텔레그램 메시지 확인:")
        logger.info(message)
        
        logger.info("✅ 모든 테스트 완료!")
        
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_hyperclova_summary()) 