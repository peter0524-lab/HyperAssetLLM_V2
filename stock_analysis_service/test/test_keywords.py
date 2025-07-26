#!/usr/bin/env python3
"""
키워드 조회 기능 테스트 스크립트
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로그 레벨을 DEBUG로 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from services.news_service.main import NewsService

def test_keywords_retrieval():
    """키워드 조회 기능 테스트"""
    print("🔍 키워드 조회 기능 테스트 시작")
    
    try:
        # NewsService 인스턴스 생성
        print("📋 NewsService 초기화 중...")
        news_service = NewsService()
        print("✅ NewsService 초기화 완료")
        
        # 키워드 조회 테스트
        stock_code = "006800"
        print(f"🔍 종목 {stock_code} 키워드 조회 중...")
        
        keywords = news_service.get_latest_impact_keywords(stock_code)
        
        if keywords:
            print(f"✅ 키워드 조회 성공: {len(keywords)}개 키워드")
            print("📋 키워드 목록:")
            for keyword, weight in list(keywords.items())[:10]:  # 처음 10개만 출력
                print(f"  • {keyword}: 가중치 {weight}")
            if len(keywords) > 10:
                print(f"  ... 외 {len(keywords) - 10}개")
        else:
            print("❌ 키워드 조회 실패")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_keywords_retrieval() 