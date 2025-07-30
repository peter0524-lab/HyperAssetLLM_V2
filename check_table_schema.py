#!/usr/bin/env python3
"""
실제 데이터베이스 테이블 구조 확인
"""

import pymysql
from config.env_local import get_config

def check_table_schema():
    """테이블 구조 확인"""
    config = get_config()
    
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
    
    # 테이블 목록 확인
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print("📋 데이터베이스 테이블 목록:")
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n" + "="*50)
    
    # 주요 테이블 구조 확인
    target_tables = ['user_profiles', 'user_stocks', 'user_model', 'user_wanted_service']
    
    for table_name in target_tables:
        try:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            print(f"\n📊 {table_name} 테이블 구조:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} ({col[2]})")
        except Exception as e:
            print(f"❌ {table_name} 테이블 확인 실패: {e}")
    
    # 기존 데이터 확인
    print("\n" + "="*50)
    print("📊 기존 데이터 확인:")
    
    for table_name in target_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count}개 레코드")
            
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print(f"    샘플 데이터:")
                for row in rows:
                    print(f"      {row}")
        except Exception as e:
            print(f"❌ {table_name} 데이터 확인 실패: {e}")
    
    connection.close()

if __name__ == "__main__":
    check_table_schema() 