#!/usr/bin/env python3
"""
데이터베이스에 직접 테이블 생성 및 테스트 데이터 추가
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.database.mysql_client import MySQLClient

async def setup_database():
    """데이터베이스 테이블 생성 및 테스트 데이터 추가"""
    print("🗄️ 데이터베이스 설정 시작")
    
    try:
        mysql_client = MySQLClient()
        
        # 1. 사용자 프로필 테이블 생성
        print("\n1️⃣ 사용자 프로필 테이블 생성...")
        create_user_profiles = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id VARCHAR(50) PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            phone_number VARCHAR(20) NOT NULL UNIQUE,
            news_similarity_threshold FLOAT DEFAULT 0.7,
            news_impact_threshold FLOAT DEFAULT 0.8,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_phone_number (phone_number)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        await mysql_client.execute_query_async(create_user_profiles)
        print("✅ 사용자 프로필 테이블 생성 완료")
        
        # 2. 사용자 종목 테이블 생성
        print("\n2️⃣ 사용자 종목 테이블 생성...")
        create_user_stocks = """
        CREATE TABLE IF NOT EXISTS user_stocks (
            user_id VARCHAR(50),
            stock_code VARCHAR(20) NOT NULL,
            stock_name VARCHAR(100) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, stock_code),
            INDEX idx_user_enabled (user_id, enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        await mysql_client.execute_query_async(create_user_stocks)
        print("✅ 사용자 종목 테이블 생성 완료")
        
        # 3. 사용자 모델 테이블 생성
        print("\n3️⃣ 사용자 모델 테이블 생성...")
        create_user_model = """
        CREATE TABLE IF NOT EXISTS user_model (
            user_id VARCHAR(50),
            model_type ENUM('hyperclova', 'chatgpt', 'claude', 'grok', 'gemini') DEFAULT 'hyperclova',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
            PRIMARY KEY (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        await mysql_client.execute_query_async(create_user_model)
        print("✅ 사용자 모델 테이블 생성 완료")
        
        # 4. 텔레그램 설정 테이블 생성
        print("\n4️⃣ 텔레그램 설정 테이블 생성...")
        create_telegram_configs = """
        CREATE TABLE IF NOT EXISTS user_telegram_configs (
            user_id VARCHAR(50) PRIMARY KEY,
            bot_token VARCHAR(255) NOT NULL,
            chat_id VARCHAR(100) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            news_alerts BOOLEAN DEFAULT TRUE,
            disclosure_alerts BOOLEAN DEFAULT TRUE,
            chart_alerts BOOLEAN DEFAULT TRUE,
            price_alerts BOOLEAN DEFAULT TRUE,
            weekly_reports BOOLEAN DEFAULT FALSE,
            error_alerts BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        await mysql_client.execute_query_async(create_telegram_configs)
        print("✅ 텔레그램 설정 테이블 생성 완료")
        
        # 5. 테스트 사용자 데이터 추가
        print("\n5️⃣ 테스트 사용자 데이터 추가...")
        
        # 사용자 프로필 추가
        user_id = "1"
        insert_user = """
        INSERT INTO user_profiles (user_id, username, phone_number, news_similarity_threshold, news_impact_threshold)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        username = VALUES(username),
        phone_number = VALUES(phone_number),
        news_similarity_threshold = VALUES(news_similarity_threshold),
        news_impact_threshold = VALUES(news_impact_threshold)
        """
        await mysql_client.execute_query_async(
            insert_user, 
            (user_id, "test_user", "01012345678", 0.7, 0.8)
        )
        print("✅ 사용자 프로필 추가 완료")
        
        # 사용자 모델 설정 추가
        insert_model = """
        INSERT INTO user_model (user_id, model_type)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
        model_type = VALUES(model_type)
        """
        await mysql_client.execute_query_async(insert_model, (user_id, "hyperclova"))
        print("✅ 사용자 모델 설정 추가 완료")
        
        # 미래에셋 종목 추가
        insert_stock = """
        INSERT INTO user_stocks (user_id, stock_code, stock_name, enabled)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        stock_name = VALUES(stock_name),
        enabled = VALUES(enabled)
        """
        await mysql_client.execute_query_async(
            insert_stock, 
            (user_id, "005930", "삼성전자", True)
        )
        print("✅ 미래에셋 종목 추가 완료")
        
        # 텔레그램 설정 추가 (모든 알림 활성화)
        insert_telegram = """
        INSERT INTO user_telegram_configs (
            user_id, bot_token, chat_id, enabled,
            news_alerts, disclosure_alerts, chart_alerts,
            price_alerts, weekly_reports, error_alerts
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        bot_token = VALUES(bot_token),
        chat_id = VALUES(chat_id),
        enabled = VALUES(enabled),
        news_alerts = VALUES(news_alerts),
        disclosure_alerts = VALUES(disclosure_alerts),
        chart_alerts = VALUES(chart_alerts),
        price_alerts = VALUES(price_alerts),
        weekly_reports = VALUES(weekly_reports),
        error_alerts = VALUES(error_alerts)
        """
        await mysql_client.execute_query_async(
            insert_telegram,
            (user_id, "7888091225:AAHMqbCQV4_so7VqDeLqbWaiGTvVyQ698-M", "-1002819230740", True, True, True, True, True, True, True)
        )
        print("✅ 텔레그램 설정 추가 완료")
        
        # 6. 설정 확인
        print("\n6️⃣ 설정 확인...")
        
        # 사용자 프로필 확인
        check_user = "SELECT * FROM user_profiles WHERE user_id = %s"
        user_result = await mysql_client.execute_query_async(check_user, (user_id,), fetch=True)
        if user_result:
            print(f"✅ 사용자 프로필: {user_result[0]['username']} ({user_result[0]['phone_number']})")
        else:
            print("❌ 사용자 프로필 없음")
        
        # 종목 확인
        check_stocks = "SELECT * FROM user_stocks WHERE user_id = %s"
        stocks_result = await mysql_client.execute_query_async(check_stocks, (user_id,), fetch=True)
        if stocks_result:
            print(f"✅ 등록된 종목: {len(stocks_result)}개")
            for stock in stocks_result:
                print(f"  - {stock['stock_code']} ({stock['stock_name']}): {'활성화' if stock['enabled'] else '비활성화'}")
        else:
            print("❌ 등록된 종목 없음")
        
        # 텔레그램 설정 확인
        check_telegram = "SELECT * FROM user_telegram_configs WHERE user_id = %s"
        telegram_result = await mysql_client.execute_query_async(check_telegram, (user_id,), fetch=True)
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
        
        await mysql_client.close()
        
        print(f"\n✅ 데이터베이스 설정 완료!")
        print(f"📋 사용자 ID: {user_id}")
        print(f"📱 전화번호: 01012345678")
        print(f"📈 관심 종목: 삼성전자 (005930)")
        print(f"🔔 모든 알림 활성화됨")
        
        return user_id
        
    except Exception as e:
        print(f"❌ 데이터베이스 설정 실패: {e}")
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
    print("🚀 데이터베이스 직접 설정 및 알림 필터링 테스트")
    print("=" * 60)
    
    # 1. 데이터베이스 설정
    user_id = await setup_database()
    
    if user_id:
        # 2. 알림 필터링 테스트
        await test_notification_filtering(user_id)
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print(f"💡 이제 실제 서비스에서 사용자 {user_id}에 대한 알림이 필터링됩니다!")
    else:
        print("❌ 데이터베이스 설정 실패")

if __name__ == "__main__":
    asyncio.run(main()) 