#!/usr/bin/env python3
"""
테스트용 사용자 데이터 설정 스크립트
사용자 ID "1"에 미래에셋(005930) 종목과 모든 알림 설정을 추가
"""

import asyncio
import sys
import os
from pathlib import Path
import requests
import json

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

async def setup_test_user():
    """테스트용 사용자 데이터 설정"""
    print("🧪 테스트용 사용자 데이터 설정 시작")
    
    # User Service URL
    user_service_url = "http://localhost:8006"
    
    try:
        # 1. 사용자 프로필 생성
        print("\n1️⃣ 사용자 프로필 생성...")
        profile_data = {
            "username": "test_user",
            "phone_number": "01012345678"
        }
        
        response = requests.post(f"{user_service_url}/users/profile", json=profile_data)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                user_id = result.get("data", {}).get("user_id")
                print(f"✅ 사용자 프로필 생성 완료: {user_id}")
            else:
                print(f"❌ 사용자 프로필 생성 실패: {result.get('message')}")
                return None
        else:
            print(f"❌ 사용자 프로필 생성 실패: {response.status_code}")
            return None
        
        # 2. 미래에셋 종목 추가
        print("\n2️⃣ 미래에셋 종목 추가...")
        stock_data = {
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "enabled": True
        }
        
        response = requests.post(f"{user_service_url}/users/{user_id}/stocks", json=stock_data)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 미래에셋 종목 추가 완료")
            else:
                print(f"❌ 미래에셋 종목 추가 실패: {result.get('message')}")
        else:
            print(f"❌ 미래에셋 종목 추가 실패: {response.status_code}")
        
        # 3. 텔레그램 설정 추가 (모든 알림 활성화)
        print("\n3️⃣ 텔레그램 설정 추가...")
        telegram_data = {
            "bot_token": "7888091225:AAHMqbCQV4_so7VqDeLqbWaiGTvVyQ698-M",
            "chat_id": "-1002819230740",
            "enabled": True,
            "news_alerts": True,
            "disclosure_alerts": True,
            "chart_alerts": True,
            "price_alerts": True,
            "weekly_reports": True,
            "error_alerts": True
        }
        
        response = requests.post(f"{user_service_url}/users/{user_id}/telegram-config", json=telegram_data)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 텔레그램 설정 추가 완료")
            else:
                print(f"❌ 텔레그램 설정 추가 실패: {result.get('message')}")
        else:
            print(f"❌ 텔레그램 설정 추가 실패: {response.status_code}")
        
        # 4. 설정 확인
        print("\n4️⃣ 설정 확인...")
        
        # 종목 목록 확인
        response = requests.get(f"{user_service_url}/users/{user_id}/stocks")
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                stocks = result.get("data", {}).get("stocks", [])
                print(f"✅ 등록된 종목: {len(stocks)}개")
                for stock in stocks:
                    print(f"  - {stock.get('stock_code')} ({stock.get('stock_name')}): {'활성화' if stock.get('enabled') else '비활성화'}")
            else:
                print(f"❌ 종목 목록 조회 실패: {result.get('message')}")
        else:
            print(f"❌ 종목 목록 조회 실패: {response.status_code}")
        
        # 텔레그램 설정 확인
        response = requests.get(f"{user_service_url}/users/{user_id}/telegram-config")
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                config = result.get("data", {})
                if config:
                    print("✅ 텔레그램 설정:")
                    print(f"  - 전체 알림: {'활성화' if config.get('enabled') else '비활성화'}")
                    print(f"  - 뉴스 알림: {'활성화' if config.get('news_alerts') else '비활성화'}")
                    print(f"  - 공시 알림: {'활성화' if config.get('disclosure_alerts') else '비활성화'}")
                    print(f"  - 차트 알림: {'활성화' if config.get('chart_alerts') else '비활성화'}")
                    print(f"  - 가격 알림: {'활성화' if config.get('price_alerts') else '비활성화'}")
                    print(f"  - 주간보고서: {'활성화' if config.get('weekly_reports') else '비활성화'}")
                    print(f"  - 에러 알림: {'활성화' if config.get('error_alerts') else '비활성화'}")
                else:
                    print("❌ 텔레그램 설정이 없습니다")
            else:
                print(f"❌ 텔레그램 설정 조회 실패: {result.get('message')}")
        else:
            print(f"❌ 텔레그램 설정 조회 실패: {response.status_code}")
        
        print(f"\n✅ 테스트용 사용자 데이터 설정 완료!")
        print(f"📋 사용자 ID: {user_id}")
        print(f"📱 전화번호: 01012345678")
        print(f"📈 관심 종목: 삼성전자 (005930)")
        print(f"🔔 모든 알림 활성화됨")
        
        return user_id
        
    except Exception as e:
        print(f"❌ 테스트 데이터 설정 실패: {e}")
        return None

async def test_notification_filtering(user_id):
    """알림 필터링 테스트"""
    print(f"\n🧪 사용자 {user_id}의 알림 필터링 테스트")
    
    try:
        from shared.service_config.user_config_loader import UserConfigLoader
        
        config_loader = UserConfigLoader()
        
        # 테스트할 종목들
        test_stocks = [
            "005930",  # 삼성전자 (관심 종목)
            "000660",  # SK하이닉스 (관심 없음)
            "035420",  # NAVER (관심 없음)
        ]
        
        print("\n📊 종목별 알림 필터링 테스트:")
        
        for stock_code in test_stocks:
            print(f"\n🔍 종목 {stock_code} 테스트:")
            
            # 1. 종목 관심도 확인
            try:
                is_interested = await config_loader.is_user_interested_in_stock(user_id, stock_code)
                print(f"  📈 종목 관심도: {'✅ 관심 있음' if is_interested else '❌ 관심 없음'}")
                
                if not is_interested:
                    print(f"  ⏭️ 알림 전송 안함 (관심 종목 아님)")
                    continue
                    
            except Exception as e:
                print(f"  ⚠️ 종목 관심도 확인 실패: {e}")
                continue
            
            # 2. 알림 설정 확인
            try:
                notification_settings = await config_loader.get_user_notification_settings(user_id)
                print(f"  🔔 알림 설정:")
                for setting, value in notification_settings.items():
                    status = "✅ 활성화" if value else "❌ 비활성화"
                    print(f"    - {setting}: {status}")
                    
            except Exception as e:
                print(f"  ⚠️ 알림 설정 확인 실패: {e}")
            
            # 3. 텔레그램 설정 확인
            try:
                telegram_config = await config_loader.get_user_telegram_config(user_id)
                if telegram_config and telegram_config.get("enabled", True):
                    chat_id = telegram_config.get("chat_id")
                    print(f"  📱 텔레그램 설정: ✅ 활성화 (채팅 ID: {chat_id})")
                    print(f"  📤 알림 전송 가능: ✅")
                else:
                    print(f"  📱 텔레그램 설정: ❌ 비활성화")
                    print(f"  📤 알림 전송 가능: ❌")
                    
            except Exception as e:
                print(f"  ⚠️ 텔레그램 설정 확인 실패: {e}")
        
        print("\n✅ 알림 필터링 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 알림 필터링 테스트 실패: {e}")

async def main():
    """메인 함수"""
    print("🚀 테스트용 사용자 데이터 설정 및 알림 필터링 테스트")
    print("=" * 60)
    
    # 1. 테스트 데이터 설정
    user_id = await setup_test_user()
    
    if user_id:
        # 2. 알림 필터링 테스트
        await test_notification_filtering(user_id)
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print(f"💡 이제 실제 서비스에서 사용자 {user_id}에 대한 알림이 필터링됩니다!")
    else:
        print("❌ 테스트 데이터 설정 실패")

if __name__ == "__main__":
    asyncio.run(main()) 