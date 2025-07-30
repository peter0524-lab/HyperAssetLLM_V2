#!/usr/bin/env python3
"""
데이터베이스 직접 연결 및 데이터 확인
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.database.mysql_client import MySQLClient

async def check_database():
    """데이터베이스 직접 확인"""
    print("🔍 데이터베이스 직접 확인")
    
    try:
        mysql_client = MySQLClient()
        
        # 1. 사용자 프로필 확인
        print("\n1️⃣ 사용자 프로필 확인...")
        check_user = "SELECT * FROM user_profiles WHERE user_id = %s"
        user_result = await mysql_client.execute_query_async(check_user, ("1",), fetch=True)
        if user_result:
            user = user_result[0]
            print(f"✅ 사용자 프로필: {user['username']} ({user['phone_number']})")
        else:
            print("❌ 사용자 프로필 없음")
        
        # 2. 사용자 종목 확인
        print("\n2️⃣ 사용자 종목 확인...")
        check_stocks = "SELECT * FROM user_stocks WHERE user_id = %s"
        stocks_result = await mysql_client.execute_query_async(check_stocks, ("1",), fetch=True)
        if stocks_result:
            print(f"✅ 등록된 종목: {len(stocks_result)}개")
            for stock in stocks_result:
                print(f"  - {stock['stock_code']} ({stock['stock_name']}): {'활성화' if stock['enabled'] else '비활성화'}")
        else:
            print("❌ 등록된 종목 없음")
        
        # 3. 텔레그램 설정 확인
        print("\n3️⃣ 텔레그램 설정 확인...")
        check_telegram = "SELECT * FROM user_telegram_configs WHERE user_id = %s"
        telegram_result = await mysql_client.execute_query_async(check_telegram, ("1",), fetch=True)
        if telegram_result:
            config = telegram_result[0]
            print("✅ 텔레그램 설정:")
            print(f"  - 전체 알림: {'활성화' if config['enabled'] else '비활성화'}")
            print(f"  - 뉴스 알림: {'활성화' if config['news_alerts'] else '비활성화'}")
            print(f"  - 공시 알림: {'활성화' if config['disclosure_alerts'] else '비활성화'}")
            print(f"  - 차트 알림: {'활성화' if config['chart_alerts'] else '비활성화'}")
            print(f"  - 가격 알림: {'활성화' if config['price_alerts'] else '비활성화'}")
            print(f"  - 주간보고서: {'활성화' if config['weekly_reports'] else '비활성화'}")
            print(f"  - 에러 알림: {'활성화' if config['error_alerts'] else '비활성화'}")
        else:
            print("❌ 텔레그램 설정 없음")
        
        # 4. User Service API 테스트
        print("\n4️⃣ User Service API 테스트...")
        import requests
        
        # 종목 조회 API 테스트
        response = requests.get("http://localhost:8006/users/1/stocks")
        print(f"종목 조회 API 응답: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"종목 조회 결과: {result}")
        else:
            print(f"종목 조회 실패: {response.text}")
        
        # 텔레그램 설정 조회 API 테스트
        response = requests.get("http://localhost:8006/users/1/telegram-config")
        print(f"텔레그램 설정 조회 API 응답: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"텔레그램 설정 결과: {result}")
        else:
            print(f"텔레그램 설정 조회 실패: {response.text}")
        
        await mysql_client.close()
        
        print("\n✅ 데이터베이스 확인 완료!")
        
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")

async def main():
    """메인 함수"""
    print("🔍 데이터베이스 직접 확인 및 API 테스트")
    print("=" * 50)
    
    await check_database()

if __name__ == "__main__":
    asyncio.run(main()) 