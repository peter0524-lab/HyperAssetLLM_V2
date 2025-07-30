#!/usr/bin/env python3
"""
테스트 사용자 정보 확인
"""

import pymysql
from config.env_local import get_config

def check_test_user():
    """테스트 사용자 정보 확인"""
    config = get_config()
    
    try:
        # 데이터베이스 연결
        connection = pymysql.connect(
            host=config['mysql']['host'],
            port=config['mysql']['port'],
            user=config['mysql']['user'],
            password=config['mysql']['password'],
            database=config['mysql']['database'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # 1. 사용자 프로필 확인
        print("🔍 테스트 사용자 프로필 확인...")
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = 'mirae_test_user_001'")
        user_profile = cursor.fetchone()
        if user_profile:
            print(f"✅ 사용자 프로필: {user_profile}")
        else:
            print("❌ 사용자 프로필 없음")
        
        # 2. 사용자 종목 확인
        print("\n🔍 테스트 사용자 종목 확인...")
        cursor.execute("SELECT * FROM user_stocks WHERE user_id = 'mirae_test_user_001'")
        user_stocks = cursor.fetchall()
        if user_stocks:
            print(f"✅ 사용자 종목: {len(user_stocks)}개")
            for stock in user_stocks:
                print(f"  - {stock}")
        else:
            print("❌ 사용자 종목 없음")
        
        # 3. 사용자 서비스 설정 확인
        print("\n🔍 테스트 사용자 서비스 설정 확인...")
        cursor.execute("SELECT * FROM user_wanted_service WHERE user_id = 'mirae_test_user_001'")
        user_services = cursor.fetchall()
        if user_services:
            print(f"✅ 사용자 서비스: {len(user_services)}개")
            for service in user_services:
                print(f"  - {service}")
        else:
            print("❌ 사용자 서비스 설정 없음")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    check_test_user() 