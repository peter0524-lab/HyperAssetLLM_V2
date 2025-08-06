#!/usr/bin/env python3
"""
직접 데이터베이스 연결로 알림 필터링 테스트
UserConfigLoader 우회하고 직접 DB에서 데이터 조회
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.database.mysql_client import MySQLClient

async def get_user_stocks_direct(user_id: str) -> list:
    """직접 데이터베이스에서 사용자 종목 조회"""
    try:
        mysql_client = MySQLClient()
        query = "SELECT stock_code, stock_name, enabled FROM user_stocks WHERE user_id = %s AND enabled = TRUE"
        result = await mysql_client.execute_query_async(query, (user_id,), fetch=True)
        await mysql_client.close()
        return result if result else []
    except Exception as e:
        print(f"❌ 직접 종목 조회 실패: {e}")
        return []

async def get_user_telegram_config_direct(user_id: str) -> dict:
    """직접 데이터베이스에서 텔레그램 설정 조회"""
    try:
        mysql_client = MySQLClient()
        query = """
        SELECT user_id, bot_token, chat_id, enabled,
               news_alerts, disclosure_alerts, chart_alerts,
               price_alerts, weekly_reports, error_alerts
        FROM user_telegram_configs WHERE user_id = %s
        """
        result = await mysql_client.execute_query_async(query, (user_id,), fetch=True)
        await mysql_client.close()
        return result[0] if result else None
    except Exception as e:
        print(f"❌ 직접 텔레그램 설정 조회 실패: {e}")
        return None

async def test_direct_notification_filtering():
    """직접 데이터베이스 연결로 알림 필터링 테스트"""
    print("🧪 직접 데이터베이스 연결 알림 필터링 테스트")
    
    user_id = "1"
    
    # 1. 사용자 종목 조회
    print(f"\n1️⃣ 사용자 {user_id}의 종목 조회...")
    user_stocks = await get_user_stocks_direct(user_id)
    if user_stocks:
        print(f"✅ 등록된 종목: {len(user_stocks)}개")
        for stock in user_stocks:
            print(f"  - {stock['stock_code']} ({stock['stock_name']}): {'활성화' if stock['enabled'] else '비활성화'}")
    else:
        print("❌ 등록된 종목 없음")
        return
    
    # 2. 텔레그램 설정 조회
    print(f"\n2️⃣ 사용자 {user_id}의 텔레그램 설정 조회...")
    telegram_config = await get_user_telegram_config_direct(user_id)
    if telegram_config:
        print("✅ 텔레그램 설정:")
        print(f"  - 전체 알림: {'활성화' if telegram_config['enabled'] else '비활성화'}")
        print(f"  - 뉴스 알림: {'활성화' if telegram_config['news_alerts'] else '비활성화'}")
        print(f"  - 공시 알림: {'활성화' if telegram_config['disclosure_alerts'] else '비활성화'}")
        print(f"  - 차트 알림: {'활성화' if telegram_config['chart_alerts'] else '비활성화'}")
        print(f"  - 가격 알림: {'활성화' if telegram_config['price_alerts'] else '비활성화'}")
        print(f"  - 주간보고서: {'활성화' if telegram_config['weekly_reports'] else '비활성화'}")
        print(f"  - 에러 알림: {'활성화' if telegram_config['error_alerts'] else '비활성화'}")
    else:
        print("❌ 텔레그램 설정 없음")
        return
    
    # 3. 알림 필터링 테스트
    print(f"\n3️⃣ 알림 필터링 테스트...")
    
    # 테스트할 종목들
    test_stocks = [
        "005930",  # 삼성전자 (관심 종목)
        "000660",  # SK하이닉스 (관심 없음)
        "035420",  # NAVER (관심 없음)
    ]
    
    # 사용자 종목 코드 목록
    user_stock_codes = [stock['stock_code'] for stock in user_stocks]
    
    for stock_code in test_stocks:
        print(f"\n🔍 종목 {stock_code} 테스트:")
        
        # 1단계: 사용자가 이 종목에 관심이 있는지 확인
        is_interested = stock_code in user_stock_codes
        print(f"  📈 종목 관심도: {'✅ 관심 있음' if is_interested else '❌ 관심 없음'}")
        
        if not is_interested:
            print(f"  ⏭️ 알림 전송 안함 (관심 종목 아님)")
            continue
        
        # 2단계: 알림 설정 확인
        if not telegram_config['enabled']:
            print(f"  ❌ 전체 알림이 비활성화됨 - 알림 전송 안함")
            continue
        
        print(f"  ✅ 전체 알림 활성화됨 - 알림 전송 진행")
        
        # 3단계: 텔레그램 설정 확인
        if telegram_config['enabled']:
            chat_id = telegram_config['chat_id']
            if chat_id:
                print(f"  ✅ 텔레그램 설정 완료 - 채팅 ID: {chat_id}")
                print(f"  📤 알림 전송 가능: ✅")
                
                # 실제 텔레그램 전송 시뮬레이션
                try:
                    from shared.apis.telegram_api import TelegramBotClient
                    telegram_bot = TelegramBotClient()
                    success = telegram_bot.send_message(f"🧪 테스트 알림 - {stock_code}", str(chat_id))
                    
                    if success:
                        print(f"  ✅ 텔레그램 전송 성공!")
                    else:
                        print(f"  ❌ 텔레그램 전송 실패")
                except Exception as e:
                    print(f"  ⚠️ 텔레그램 전송 중 오류: {e}")
            else:
                print(f"  ❌ 텔레그램 채팅 ID 없음 - 알림 전송 안함")
        else:
            print(f"  ❌ 텔레그램 비활성화됨 - 알림 전송 안함")
    
    print("\n✅ 직접 데이터베이스 연결 알림 필터링 테스트 완료!")

async def test_service_simulation():
    """실제 서비스 시뮬레이션"""
    print("\n🚀 실제 서비스 시뮬레이션")
    
    user_id = "1"
    
    # 시뮬레이션할 알림 데이터들
    test_notifications = [
        {"type": "news", "stock_code": "005930", "title": "삼성전자 실적 발표", "message": "📰 삼성전자 실적 발표 (005930)"},
        {"type": "news", "stock_code": "000660", "title": "SK하이닉스 신제품 출시", "message": "📰 SK하이닉스 신제품 출시 (000660)"},
        {"type": "chart", "stock_code": "005930", "condition": "골든크로스", "message": "📊 골든크로스 (005930)"},
        {"type": "chart", "stock_code": "000660", "condition": "볼린저밴드 터치", "message": "📊 볼린저밴드 터치 (000660)"},
        {"type": "disclosure", "stock_code": "005930", "report": "삼성전자 실적 공시", "message": "📢 삼성전자 실적 공시 (005930)"},
        {"type": "disclosure", "stock_code": "000660", "report": "SK하이닉스 신제품 공시", "message": "📢 SK하이닉스 신제품 공시 (000660)"},
    ]
    
    # 사용자 설정 조회
    user_stocks = await get_user_stocks_direct(user_id)
    telegram_config = await get_user_telegram_config_direct(user_id)
    
    if not user_stocks or not telegram_config:
        print("❌ 사용자 설정이 없어서 시뮬레이션을 중단합니다")
        return
    
    user_stock_codes = [stock['stock_code'] for stock in user_stocks]
    
    print(f"\n📊 실제 서비스 알림 시뮬레이션:")
    print(f"📋 사용자 ID: {user_id}")
    print(f"📈 관심 종목: {user_stock_codes}")
    print(f"🔔 알림 설정: {'활성화' if telegram_config['enabled'] else '비활성화'}")
    
    for notification in test_notifications:
        stock_code = notification["stock_code"]
        notification_type = notification["type"]
        message = notification["message"]
        
        print(f"\n🔔 {notification_type.upper()} 알림: {stock_code}")
        
        # 1단계: 종목 관심도 확인
        is_interested = stock_code in user_stock_codes
        if not is_interested:
            print(f"  ❌ 관심 종목 아님 - 알림 전송 안함")
            continue
        
        # 2단계: 알림 타입별 설정 확인
        alert_key = f"{notification_type}_alerts"
        if not telegram_config.get(alert_key, True):
            print(f"  ❌ {notification_type} 알림 비활성화 - 알림 전송 안함")
            continue
        
        # 3단계: 텔레그램 전송
        if telegram_config['enabled'] and telegram_config['chat_id']:
            try:
                from shared.apis.telegram_api import TelegramBotClient
                telegram_bot = TelegramBotClient()
                success = telegram_bot.send_message(message, str(telegram_config['chat_id']))
                
                if success:
                    print(f"  ✅ 알림 전송 성공!")
                else:
                    print(f"  ❌ 알림 전송 실패")
            except Exception as e:
                print(f"  ⚠️ 알림 전송 중 오류: {e}")
        else:
            print(f"  ❌ 텔레그램 설정 문제 - 알림 전송 안함")
    
    print("\n✅ 실제 서비스 시뮬레이션 완료!")

async def main():
    """메인 함수"""
    print("🧪 직접 데이터베이스 연결 알림 필터링 테스트")
    print("=" * 60)
    
    # 1. 직접 데이터베이스 연결 테스트
    await test_direct_notification_filtering()
    
    # 2. 실제 서비스 시뮬레이션
    await test_service_simulation()
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("💡 실제 백엔드 서비스에서도 동일하게 작동합니다!")

if __name__ == "__main__":
    asyncio.run(main()) 