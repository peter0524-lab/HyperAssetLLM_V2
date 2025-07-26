#!/usr/bin/env python3
"""
종목 관련성 계산 비활성화 테스트 스크립트
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

async def test_relevance_disabled():
    """종목 관련성 계산 비활성화 테스트"""
    try:
        logger.info("🧪 종목 관련성 계산 비활성화 테스트 시작")
        
        # 뉴스 서비스 초기화
        news_service = NewsService()
        
        # 테스트용 뉴스 데이터 (완전히 관련 없는 뉴스)
        irrelevant_news = {
            "stock_code": "006800",  # 미래에셋증권
            "title": "날씨가 추워서 감기환자가 늘었습니다",  # 완전히 관련 없는 제목
            "content": """
오늘 기온이 영하 10도까지 떨어지면서 전국적으로 감기 환자가 급증하고 있습니다.
병원들은 감기 환자들로 붐비고 있으며, 특히 어린이들의 감기 발병률이 높아졌습니다.
보건당국은 외출 시 마스크 착용과 손 씻기를 당부했습니다.
날씨가 추운 만큼 따뜻한 옷을 입고 건강관리에 신경써야 할 것 같습니다.
            """,
            "url": "https://example.com/weather-news/123",
            "published_at": datetime.now()
        }
        
        # 1. 3단계 필터링 테스트 (관련성 없는 뉴스도 통과해야 함)
        logger.info("📝 테스트 1: 관련성 없는 뉴스의 3단계 필터링")
        is_filtered, filter_reason, filter_result = await news_service.check_three_stage_filtering(irrelevant_news)
        
        logger.info(f"✅ 필터링 결과:")
        logger.info(f"   • 필터링됨: {is_filtered}")
        logger.info(f"   • 필터링 사유: {filter_reason}")
        logger.info(f"   • 관련성 점수: {filter_result['details'].get('relevance_score', 'N/A')}")
        logger.info(f"   • 관련성 이유: {filter_result['details'].get('relevance_reasoning', 'N/A')}")
        
        # 2. 관련성이 높은 뉴스 테스트
        relevant_news = {
            "stock_code": "006800",
            "title": "미래에셋증권, 분기 실적 발표",
            "content": """
미래에셋증권이 3분기 실적을 발표했습니다.
매출액이 전년 동기 대비 15% 증가했으며,
영업이익도 크게 개선된 것으로 나타났습니다.
            """,
            "url": "https://example.com/relevant-news/123",
            "published_at": datetime.now()
        }
        
        logger.info("📝 테스트 2: 관련성 높은 뉴스의 3단계 필터링")
        is_filtered2, filter_reason2, filter_result2 = await news_service.check_three_stage_filtering(relevant_news)
        
        logger.info(f"✅ 필터링 결과:")
        logger.info(f"   • 필터링됨: {is_filtered2}")
        logger.info(f"   • 필터링 사유: {filter_reason2}")
        logger.info(f"   • 관련성 점수: {filter_result2['details'].get('relevance_score', 'N/A')}")
        logger.info(f"   • 관련성 이유: {filter_result2['details'].get('relevance_reasoning', 'N/A')}")
        
        # 3. 결과 분석
        logger.info("📊 테스트 결과 분석:")
        
        if filter_result['details'].get('relevance_score') == 1.0:
            logger.info("✅ 성공: 종목 관련성 계산이 비활성화되어 모든 뉴스가 관련성 점수 1.0으로 처리됨")
        else:
            logger.warning("⚠️ 실패: 종목 관련성 계산이 여전히 활성화되어 있음")
        
        if filter_result['details'].get('relevance_reasoning') == "관련성 검사 비활성화됨":
            logger.info("✅ 성공: 관련성 검사 비활성화 메시지 확인")
        else:
            logger.warning("⚠️ 실패: 예상된 비활성화 메시지가 나오지 않음")
        
        # 4. 성능 테스트 (관련성 계산 없이 빨라야 함)
        logger.info("📝 테스트 3: 성능 테스트 (관련성 계산 제거로 빨라져야 함)")
        
        import time
        start_time = time.time()
        
        # 여러 뉴스 동시 처리
        test_news_list = [irrelevant_news, relevant_news] * 3  # 6개 뉴스
        
        for i, news in enumerate(test_news_list, 1):
            news["title"] = f"{news['title']} - 테스트{i}"
            await news_service.check_three_stage_filtering(news)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"✅ 성능 결과: {len(test_news_list)}개 뉴스 처리 시간: {processing_time:.2f}초")
        logger.info(f"   • 평균 처리 시간: {processing_time/len(test_news_list):.3f}초/뉴스")
        
        logger.info("✅ 모든 테스트 완료!")
        
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_relevance_disabled()) 