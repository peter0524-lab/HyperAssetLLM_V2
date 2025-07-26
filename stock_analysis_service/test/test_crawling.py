#!/usr/bin/env python3
"""
크롤링 설정과 API 재시도 로직 테스트 스크립트
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from services.news_service.main import NewsService

def test_crawling_settings():
    """크롤링 설정 테스트"""
    print("🔍 크롤링 설정 테스트 시작")
    
    try:
        # NewsService 인스턴스 생성
        print("📋 NewsService 초기화 중...")
        news_service = NewsService()
        print("✅ NewsService 초기화 완료")
        
        # 테스트 종목
        stock_code = "006800"  # 미래에셋증권
        
        print(f"🔍 종목 {stock_code} 크롤링 테스트 시작...")
        
        # 1. 기본 설정 테스트 (pages=1, size=3)
        print("\n📊 1단계: 기본 설정 테스트 (pages=1, size=3)")
        news_list_1 = news_service.crawl_naver_finance_news(stock_code, pages=1, size=3)
        print(f"✅ 기본 설정 결과: {len(news_list_1)}개 뉴스")
        
        # 2. 페이지 수 증가 테스트 (pages=2, size=3)
        print("\n📊 2단계: 페이지 수 증가 테스트 (pages=2, size=3)")
        news_list_2 = news_service.crawl_naver_finance_news(stock_code, pages=2, size=3)
        print(f"✅ 페이지 증가 결과: {len(news_list_2)}개 뉴스")
        
        # 3. 크기 증가 테스트 (pages=1, size=5)
        print("\n📊 3단계: 크기 증가 테스트 (pages=1, size=5)")
        news_list_3 = news_service.crawl_naver_finance_news(stock_code, pages=1, size=5)
        print(f"✅ 크기 증가 결과: {len(news_list_3)}개 뉴스")
        
        # 결과 비교
        print("\n📊 결과 비교:")
        print(f"  • 기본 설정 (1페이지, 3개): {len(news_list_1)}개")
        print(f"  • 페이지 증가 (2페이지, 3개): {len(news_list_2)}개")
        print(f"  • 크기 증가 (1페이지, 5개): {len(news_list_3)}개")
        
        # 뉴스 제목 샘플 출력
        if news_list_1:
            print(f"\n📰 기본 설정 뉴스 샘플:")
            for i, news in enumerate(news_list_1[:3], 1):
                print(f"  {i}. {news.get('title', 'NO_TITLE')[:50]}...")
        
        print("\n✅ 크롤링 설정 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 에러: {traceback.format_exc()}")

if __name__ == "__main__":
    test_crawling_settings() 