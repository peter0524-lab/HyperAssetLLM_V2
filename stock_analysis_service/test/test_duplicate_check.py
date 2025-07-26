#!/usr/bin/env python3
"""
크로마 DB 중복 체크 기능 테스트 스크립트
"""

import sys
import os
from datetime import datetime, date
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.database.vector_db import VectorDBClient
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_high_impact_news_duplicate_check():
    """고영향 뉴스 중복 체크 테스트"""
    print("🔍 고영향 뉴스 중복 체크 테스트 시작...")
    
    try:
        # 벡터 DB 클라이언트 초기화
        vector_db = VectorDBClient()
        
        # 테스트용 뉴스 데이터
        test_news = {
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "title": "삼성전자, 반도체 시장 회복세로 실적 개선 전망",
            "summary": "삼성전자가 반도체 시장 회복세를 타고 실적 개선이 예상된다는 분석이 나왔다.",
            "impact_score": 0.85,
            "publication_date": datetime.now()
        }
        
        # 첫 번째 저장
        print("📝 첫 번째 뉴스 저장...")
        first_id = vector_db.add_high_impact_news(test_news)
        print(f"✅ 첫 번째 저장 완료: {first_id}")
        
        # 두 번째 저장 (같은 제목)
        print("📝 두 번째 뉴스 저장 (같은 제목)...")
        second_id = vector_db.add_high_impact_news(test_news)
        print(f"✅ 두 번째 저장 완료: {second_id}")
        
        # 결과 확인
        if first_id == second_id:
            print("🎉 중복 체크 성공! 같은 ID 반환됨")
        else:
            print("❌ 중복 체크 실패! 다른 ID 반환됨")
            
        # 제목이 다른 뉴스 저장
        different_news = test_news.copy()
        different_news["title"] = "삼성전자, 새로운 기술 개발로 시장 점유율 확대"
        
        print("📝 다른 제목의 뉴스 저장...")
        different_id = vector_db.add_high_impact_news(different_news)
        print(f"✅ 다른 제목 저장 완료: {different_id}")
        
        if different_id != first_id:
            print("🎉 다른 제목은 정상적으로 새로 저장됨")
        else:
            print("❌ 다른 제목도 같은 ID 반환됨")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_daily_news_duplicate_check():
    """일일 뉴스 중복 체크 테스트"""
    print("\n🔍 일일 뉴스 중복 체크 테스트 시작...")
    
    try:
        vector_db = VectorDBClient()
        
        # 테스트용 일일 뉴스 데이터
        test_daily_news = {
            "stock_code": "000660",
            "stock_name": "SK하이닉스",
            "title": "SK하이닉스, 메모리 반도체 가격 상승으로 실적 개선",
            "content": "SK하이닉스가 메모리 반도체 가격 상승으로 실적 개선이 예상된다.",
            "url": "https://example.com/news1",
            "publication_date": datetime.now()
        }
        
        # 첫 번째 저장
        print("📝 첫 번째 일일 뉴스 저장...")
        first_id = vector_db.add_daily_news(test_daily_news)
        print(f"✅ 첫 번째 저장 완료: {first_id}")
        
        # 두 번째 저장 (같은 제목)
        print("📝 두 번째 일일 뉴스 저장 (같은 제목)...")
        second_id = vector_db.add_daily_news(test_daily_news)
        print(f"✅ 두 번째 저장 완료: {second_id}")
        
        # 결과 확인
        if first_id == second_id:
            print("🎉 일일 뉴스 중복 체크 성공!")
        else:
            print("❌ 일일 뉴스 중복 체크 실패!")
            
    except Exception as e:
        print(f"❌ 일일 뉴스 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_past_event_duplicate_check():
    """과거 이벤트 중복 체크 테스트"""
    print("\n🔍 과거 이벤트 중복 체크 테스트 시작...")
    
    try:
        vector_db = VectorDBClient()
        
        # 테스트용 과거 이벤트 데이터
        test_event = {
            "stock_code": "035420",
            "stock_name": "NAVER",
            "title": "NAVER, AI 기술 혁신으로 주가 상승",
            "event_type": "기술 혁신",
            "event_date": date(2024, 1, 15),
            "price_change": 15.5,
            "volume": 5000000,
            "description": "NAVER이 AI 기술 혁신을 통해 주가가 상승했다."
        }
        
        # 첫 번째 저장
        print("📝 첫 번째 과거 이벤트 저장...")
        first_id = vector_db.add_past_event(test_event)
        print(f"✅ 첫 번째 저장 완료: {first_id}")
        
        # 두 번째 저장 (같은 제목)
        print("📝 두 번째 과거 이벤트 저장 (같은 제목)...")
        second_id = vector_db.add_past_event(test_event)
        print(f"✅ 두 번째 저장 완료: {second_id}")
        
        # 결과 확인
        if first_id == second_id:
            print("🎉 과거 이벤트 중복 체크 성공!")
        else:
            print("❌ 과거 이벤트 중복 체크 실패!")
            
    except Exception as e:
        print(f"❌ 과거 이벤트 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_keywords_duplicate_check():
    """키워드 중복 체크 테스트"""
    print("\n🔍 키워드 중복 체크 테스트 시작...")
    
    try:
        vector_db = VectorDBClient()
        
        # 테스트용 키워드 데이터
        test_keywords = {
            "stock_code": "051910",
            "stock_name": "LG화학",
            "keywords": ["배터리", "전기차", "친환경", "신재생에너지"],
            "importance_scores": [0.9, 0.8, 0.7, 0.6],
            "week_start": date(2024, 1, 8),
            "week_end": date(2024, 1, 14)
        }
        
        # 첫 번째 저장
        print("📝 첫 번째 키워드 저장...")
        first_id = vector_db.add_keywords(test_keywords)
        print(f"✅ 첫 번째 저장 완료: {first_id}")
        
        # 두 번째 저장 (같은 주차)
        print("📝 두 번째 키워드 저장 (같은 주차)...")
        second_id = vector_db.add_keywords(test_keywords)
        print(f"✅ 두 번째 저장 완료: {second_id}")
        
        # 결과 확인
        if first_id == second_id:
            print("🎉 키워드 중복 체크 성공!")
        else:
            print("❌ 키워드 중복 체크 실패!")
            
    except Exception as e:
        print(f"❌ 키워드 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 테스트 함수"""
    print("🚀 크로마 DB 중복 체크 기능 테스트 시작")
    print("=" * 60)
    
    # 각 테스트 실행
    test_high_impact_news_duplicate_check()
    test_daily_news_duplicate_check()
    test_past_event_duplicate_check()
    test_keywords_duplicate_check()
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")

if __name__ == "__main__":
    main() 