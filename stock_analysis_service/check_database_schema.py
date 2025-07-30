#!/usr/bin/env python3
"""
데이터베이스 스키마 확인 스크립트
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from config.env_local import get_config

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_database_schema():
    """데이터베이스 스키마 확인"""
    try:
        logger.info("🔍 데이터베이스 스키마 확인 시작")
        
        # MySQL 클라이언트 초기화
        mysql_client = get_mysql_client()
        
        # 테이블 목록 조회
        tables_query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = 'HyperAsset'
        ORDER BY TABLE_NAME
        """
        
        tables_result = await mysql_client.execute_query_async(tables_query, fetch=True)
        logger.info("📊 HyperAsset 데이터베이스 테이블 목록:")
        for row in tables_result:
            logger.info(f"  - {row['TABLE_NAME']}")
        
        # 주요 테이블 스키마 확인
        target_tables = [
            'user_profiles',
            'user_stocks', 
            'user_model',
            'user_wanted_service'
        ]
        
        for table_name in target_tables:
            logger.info(f"\n🔍 {table_name} 테이블 스키마:")
            
            # 컬럼 정보 조회
            columns_query = f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'HyperAsset' AND TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
            """
            
            columns_result = await mysql_client.execute_query_async(columns_query, fetch=True)
            
            if columns_result:
                for col in columns_result:
                    nullable = "NULL" if col['IS_NULLABLE'] == 'YES' else "NOT NULL"
                    default = col['COLUMN_DEFAULT'] if col['COLUMN_DEFAULT'] else "NULL"
                    logger.info(f"  - {col['COLUMN_NAME']}: {col['DATA_TYPE']} {nullable} DEFAULT {default}")
            else:
                logger.warning(f"  ⚠️ {table_name} 테이블이 존재하지 않습니다.")
        
        # 샘플 데이터 확인
        logger.info("\n📊 샘플 데이터 확인:")
        
        for table_name in target_tables:
            count_query = f"SELECT COUNT(*) as count FROM HyperAsset.{table_name}"
            try:
                count_result = await mysql_client.execute_query_async(count_query, fetch=True)
                if count_result:
                    logger.info(f"  - {table_name}: {count_result[0]['count']}개 레코드")
                else:
                    logger.info(f"  - {table_name}: 0개 레코드")
            except Exception as e:
                logger.error(f"  - {table_name}: 조회 실패 - {e}")
        
        logger.info("✅ 데이터베이스 스키마 확인 완료")
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 스키마 확인 실패: {e}")

async def main():
    """메인 실행 함수"""
    try:
        await check_database_schema()
    except Exception as e:
        logger.error(f"❌ 스크립트 실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 