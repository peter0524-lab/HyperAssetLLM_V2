#!/usr/bin/env python3
"""
실제 데이터베이스 스키마 확인 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client

def check_database_schema():
    """데이터베이스 스키마 확인"""
    try:
        client = get_mysql_client()
        
        # 뉴스 테이블 스키마 확인
        print("=== 뉴스 테이블 스키마 ===")
        result = client.execute_query("DESCRIBE news")
        for row in result:
            print(f"{row['Field']} - {row['Type']}")
        
        print("\n=== 공시 테이블 스키마 ===")
        result = client.execute_query("DESCRIBE disclosure_history")
        for row in result:
            print(f"{row['Field']} - {row['Type']}")
            
        print("\n=== 차트 조건 테이블 스키마 ===")
        result = client.execute_query("DESCRIBE chart_conditions")
        for row in result:
            print(f"{row['Field']} - {row['Type']}")
            
        print("\n=== 차트 데이터 테이블 스키마 ===")
        result = client.execute_query("DESCRIBE chart_data")
        for row in result:
            print(f"{row['Field']} - {row['Type']}")
            
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    check_database_schema() 