#!/usr/bin/env python3
"""
수정된 주가 추이 함수 테스트
"""

import sys
import os
import logging
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_stock_history_fix():
    """수정된 주가 추이 함수 테스트"""
    print("🔍 수정된 주가 추이 함수 테스트 시작")
    
    try:
        from services.news_service.main import NewsService
        service = NewsService()
        
        # 테스트 종목
        stock_code = "005930"  # 삼성전자
        
        # 테스트 날짜 (과거 뉴스 발생일)
        test_news_date = "2024-01-15"  # 과거 날짜로 테스트
        
        print(f"📊 테스트 종목: {stock_code} (삼성전자)")
        print(f"📅 뉴스 발생일: {test_news_date}")
        print(f"📈 조회 기간: T일({test_news_date}) ~ T+4일")
        
        # 1. 주가 데이터 조회 테스트
        print("\n📈 1. 주가 데이터 조회 테스트")
        try:
            price_history = service.get_stock_price_history(stock_code, test_news_date, days=5)
            
            if price_history:
                print(f"✅ 주가 데이터 조회 성공: {len(price_history)}일")
                print("📊 조회된 데이터:")
                
                for i, day in enumerate(price_history):
                    date = day['date']
                    close_price = day['close']
                    change_percent = day['change_percent']
                    
                    # T일부터 T+4까지 표시
                    if i == 0:
                        day_label = "T일"
                    else:
                        day_label = f"T+{i}일"
                    
                    print(f"  {day_label} ({date}): {close_price:,.0f}원 ({change_percent:+.1f}%)")
                
                # 2. 텔레그램 포맷팅 테스트
                print("\n📱 2. 텔레그램 포맷팅 테스트")
                try:
                    # 가상의 유사 사례 생성
                    similar_case = {
                        'title': '삼성전자 실적 발표 관련 뉴스',
                        'published_date': test_news_date,
                        'similarity_score': 0.85
                    }
                    
                    formatted_message = service.format_price_history_for_telegram(price_history, similar_case)
                    print("✅ 포맷팅 성공")
                    print("📱 포맷된 메시지:")
                    print("-" * 50)
                    print(formatted_message)
                    print("-" * 50)
                    
                except Exception as format_error:
                    print(f"❌ 포맷팅 실패: {format_error}")
                    
            else:
                print("❌ 주가 데이터 조회 실패")
                
        except Exception as e:
            print(f"❌ 주가 데이터 조회 실패: {e}")
            import traceback
            print(f"❌ 상세 에러: {traceback.format_exc()}")
        
        print("\n✅ 수정된 주가 추이 함수 테스트 완료")
        
    except ImportError as e:
        print(f"❌ import 실패: {e}")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 에러: {traceback.format_exc()}")

if __name__ == "__main__":
    test_stock_history_fix() 