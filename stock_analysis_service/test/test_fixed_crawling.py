#!/usr/bin/env python3
"""
수정된 크롤링 로직 테스트 스크립트
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from services.news_service.main import NewsService

def test_fixed_crawling():
    """수정된 크롤링 로직 테스트"""
    print("🔍 수정된 크롤링 로직 테스트 시작")
    
    try:
        # NewsService 인스턴스 생성
        print("📋 NewsService 초기화 중...")
        news_service = NewsService()
        print("✅ NewsService 초기화 완료")
        
        # 테스트 종목
        stock_code = "006800"  # 미래에셋증권
        
        print(f"🔍 종목 {stock_code} 크롤링 테스트 시작...")
        
        # 수정된 크롤링 함수 테스트
        print("\n📊 수정된 크롤링 로직 테스트 (pages=1, size=3)")
        news_list = news_service.crawl_naver_finance_news(stock_code, pages=1, size=3)
        
        print(f"✅ 크롤링 결과: {len(news_list)}개 뉴스")
        
        # 뉴스 제목 출력
        if news_list:
            print(f"\n📰 수집된 뉴스 목록:")
            for i, news in enumerate(news_list, 1):
                title = news.get('title', 'NO_TITLE')
                print(f"  {i}. {title[:60]}...")
        else:
            print("❌ 수집된 뉴스가 없습니다.")
        
        print("\n✅ 수정된 크롤링 로직 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 에러: {traceback.format_exc()}")

if __name__ == "__main__":
    test_fixed_crawling() 