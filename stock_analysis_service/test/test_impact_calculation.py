#!/usr/bin/env python3
"""
키워드 조회와 영향도 계산 기능 테스트 스크립트
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.news_service.main import NewsService
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_keyword_retrieval():
    """키워드 조회 기능 테스트"""
    print("🔍 키워드 조회 기능 테스트 시작...")
    
    try:
        # 뉴스 서비스 초기화
        service = NewsService()
        
        # 테스트용 종목 코드
        test_stock_codes = ["005930", "006800", "000660"]
        
        for stock_code in test_stock_codes:
            print(f"\n📊 종목 {stock_code} 키워드 조회 테스트:")
            
            # 키워드 조회
            keywords = service.get_latest_impact_keywords(stock_code)
            
            if keywords:
                print(f"✅ 키워드 조회 성공: {len(keywords)}개")
                print(f"📝 키워드 목록: {list(keywords.keys())[:5]}...")
            else:
                print(f"⚠️ 키워드 조회 실패: 빈 결과")
        
        print("\n✅ 키워드 조회 테스트 완료")
        
    except Exception as e:
        print(f"❌ 키워드 조회 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_impact_calculation():
    """영향도 계산 기능 테스트"""
    print("\n🎯 영향도 계산 기능 테스트 시작...")
    
    try:
        # 뉴스 서비스 초기화
        service = NewsService()
        
        # 테스트용 뉴스 데이터
        test_news = [
            {
                "stock_code": "005930",
                "title": "삼성전자, 1분기 실적 발표...영업이익 10조원 돌파",
                "content": "삼성전자가 1분기 실적을 발표했다. 영업이익이 10조원을 돌파하며 시장 기대치를 상회했다. 반도체 부문 실적이 크게 개선되면서 전체 실적을 견인했다."
            },
            {
                "stock_code": "006800",
                "title": "미래에셋증권, 신규 투자 계약 체결",
                "content": "미래에셋증권이 새로운 투자 계약을 체결했다. 이번 계약으로 인해 회사의 수익성이 크게 개선될 것으로 예상된다."
            },
            {
                "stock_code": "000660",
                "title": "SK하이닉스, 신제품 출시 예정",
                "content": "SK하이닉스가 새로운 제품을 출시할 예정이다. 이번 신제품은 시장에서 큰 관심을 받고 있다."
            }
        ]
        
        for i, news_item in enumerate(test_news, 1):
            print(f"\n📰 테스트 뉴스 {i}: {news_item['title']}")
            
            # 영향도 계산
            impact_score = service.calculate_basic_impact_score_with_db(news_item)
            
            print(f"🎯 영향도 점수: {impact_score}/10")
            
            # 내용 기반 점수도 별도로 계산
            content_score = service._calculate_content_based_score(news_item)
            print(f"📝 내용 기반 점수: {content_score}/10")
        
        print("\n✅ 영향도 계산 테스트 완료")
        
    except Exception as e:
        print(f"❌ 영향도 계산 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_content_based_scoring():
    """내용 기반 점수 계산 테스트"""
    print("\n📝 내용 기반 점수 계산 테스트 시작...")
    
    try:
        # 뉴스 서비스 초기화
        service = NewsService()
        
        # 다양한 패턴의 테스트 뉴스
        test_cases = [
            {
                "title": "삼성전자 실적 발표",
                "content": "삼성전자가 1분기 실적을 발표했다. 영업이익이 크게 증가했다.",
                "expected_keywords": ["실적", "영업이익"]
            },
            {
                "title": "M&A 인수합병 소식",
                "content": "대형 M&A 인수합병이 발표되었다. 시장에 큰 영향을 줄 것으로 예상된다.",
                "expected_keywords": ["M&A", "인수합병"]
            },
            {
                "title": "신제품 출시",
                "content": "새로운 제품이 출시되었다. 시장에서 큰 관심을 받고 있다.",
                "expected_keywords": ["신제품", "출시"]
            },
            {
                "title": "일반 뉴스",
                "content": "일반적인 뉴스 내용입니다. 특별한 키워드가 없습니다.",
                "expected_keywords": []
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📰 테스트 케이스 {i}: {test_case['title']}")
            
            news_item = {
                "stock_code": "005930",
                "title": test_case["title"],
                "content": test_case["content"]
            }
            
            # 내용 기반 점수 계산
            score = service._calculate_content_based_score(news_item)
            print(f"📝 내용 기반 점수: {score}/10")
            
            # 예상 키워드 확인
            text = (test_case["title"] + " " + test_case["content"]).lower()
            found_keywords = []
            for keyword in test_case["expected_keywords"]:
                if keyword.lower() in text:
                    found_keywords.append(keyword)
            
            print(f"🎯 발견된 키워드: {found_keywords}")
        
        print("\n✅ 내용 기반 점수 계산 테스트 완료")
        
    except Exception as e:
        print(f"❌ 내용 기반 점수 계산 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 키워드 조회 및 영향도 계산 테스트 시작")
    print("=" * 60)
    
    # 1. 키워드 조회 테스트
    test_keyword_retrieval()
    
    # 2. 영향도 계산 테스트
    test_impact_calculation()
    
    # 3. 내용 기반 점수 계산 테스트
    test_content_based_scoring()
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료") 