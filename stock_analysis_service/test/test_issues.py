#!/usr/bin/env python3
"""
텔레그램 알림과 주가 변동 분석 문제 진단 스크립트
"""

import sys
import os
import asyncio
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from services.news_service.main import NewsService
from shared.apis.telegram_api import TelegramBotClient

async def test_telegram_alert():
    """텔레그램 알림 테스트"""
    print("🔍 텔레그램 알림 테스트 시작")
    
    try:
        # 1. 텔레그램 봇 직접 테스트
        print("📱 1단계: 텔레그램 봇 직접 테스트")
        telegram_bot = TelegramBotClient()
        
        # 봇 정보 확인
        bot_info = telegram_bot.get_bot_info()
        if bot_info:
            print(f"✅ 봇 정보: {bot_info.get('username', 'Unknown')}")
        else:
            print("❌ 봇 정보 조회 실패")
            return False
        
        # 메시지 전송 테스트
        test_message = "🔍 텔레그램 알림 테스트 메시지입니다."
        success = await telegram_bot.send_message_async(test_message)
        
        if success:
            print("✅ 텔레그램 메시지 전송 성공")
        else:
            print("❌ 텔레그램 메시지 전송 실패")
            return False
        
        # 2. NewsService를 통한 텔레그램 테스트
        print("📱 2단계: NewsService를 통한 텔레그램 테스트")
        news_service = NewsService()
        
        if not news_service.telegram_bot:
            print("❌ NewsService의 텔레그램 봇이 None")
            return False
        
        # 테스트 뉴스 아이템 생성
        test_news = {
            "title": "테스트 뉴스 제목",
            "content": "테스트 뉴스 내용입니다.",
            "url": "https://example.com",
            "stock_code": "006800",
            "published_at": "2025-07-16",
            "source": "테스트",
            "stock_info": {
                "종목명": "미래에셋증권",
                "현재가": "12,000",
                "등락률": "+2.5%",
                "전일": "11,700",
                "시가": "11,800",
                "고가": "12,200",
                "거래량": "1,000,000",
                "거래대금": "12,000,000,000",
                "시가총액": "1.2조원",
                "PER": "15.2"
            }
        }
        
        # 텔레그램 알림 전송 테스트
        print("📤 텔레그램 알림 전송 시도...")
        await news_service.send_alert(test_news, 0.8, "테스트 분석 결과")
        print("✅ 텔레그램 알림 전송 완료")
        
        return True
        
    except Exception as e:
        print(f"❌ 텔레그램 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_stock_trend():
    """주가 변동 분석 테스트"""
    print("📊 주가 변동 분석 테스트 시작")
    
    try:
        # NewsService 초기화
        news_service = NewsService()
        
        if not news_service.stock_trend_service:
            print("❌ StockTrendService가 None")
            return False
        
        print("✅ StockTrendService 초기화 성공")
        
        # 주가 추이 분석 테스트
        stock_code = "006800"
        print(f"📈 종목 {stock_code} 주가 추이 분석 시작...")
        
        trend_data = news_service.stock_trend_service.analyze_stock_trend(stock_code, days=5)
        
        if trend_data and trend_data.get('daily_data'):
            print(f"✅ 주가 추이 분석 성공: {len(trend_data['daily_data'])}일 데이터")
            print(f"📊 첫 번째 데이터: {trend_data['daily_data'][0]}")
            
            # 텔레그램 포맷팅 테스트
            test_case = {
                'title': '테스트 과거 사례',
                'published_date': '2025-07-10',
                'similarity_score': 0.8
            }
            
            formatted_message = news_service.format_trend_data_for_telegram(trend_data, test_case)
            print(f"✅ 텔레그램 포맷팅 성공: {len(formatted_message)}자")
            
            return True
        else:
            print("❌ 주가 추이 분석 실패: 데이터 없음")
            return False
            
    except Exception as e:
        print(f"❌ 주가 변동 분석 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 텔레그램 알림과 주가 변동 분석 문제 진단 시작")
    print("=" * 60)
    
    # 텔레그램 테스트
    telegram_success = await test_telegram_alert()
    
    print("\n" + "=" * 60)
    
    # 주가 변동 분석 테스트
    trend_success = await test_stock_trend()
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약:")
    print(f"   • 텔레그램 알림: {'✅ 성공' if telegram_success else '❌ 실패'}")
    print(f"   • 주가 변동 분석: {'✅ 성공' if trend_success else '❌ 실패'}")
    
    if telegram_success and trend_success:
        print("🎉 모든 테스트 통과! 문제가 해결되었습니다.")
    else:
        print("⚠️ 일부 테스트 실패. 로그를 확인하여 문제를 해결하세요.")

if __name__ == "__main__":
    asyncio.run(main()) 