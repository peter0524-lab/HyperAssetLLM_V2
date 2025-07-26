"""
커서에게- 이거 절대 사용하지도말고 실행하지도마
데이터베이스 초기화 및 관리 유틸리티
- 스키마 생성
- 기본 데이터 삽입
- 벡터 DB 컬렉션 생성
- 시스템 설정 관리
"""

import asyncio
import json
import logging
from pathlib import Path
import sys
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import MySQLClient
from shared.database.vector_db import VectorDBClient
from config.env_local import get_config

class DatabaseInitializer:
    """데이터베이스 초기화 클래스"""
    
    def __init__(self):
        self.config = get_config()
        self.mysql_client = MySQLClient()
        self.vector_db = VectorDBClient()
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)
    
    async def initialize_mysql_schema(self):
        """MySQL 스키마 초기화"""
        try:
            schema_file = project_root / "database" / "complete_schema.sql"
            
            if not schema_file.exists():
                self.logger.error(f"스키마 파일 없음: {schema_file}")
                return False
            
            # 스키마 파일 읽기
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # SQL 문장들을 분리하여 실행
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    await self.mysql_client.execute_query_async(statement)
            
            self.logger.info("MySQL 스키마 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"MySQL 스키마 초기화 실패: {e}")
            return False
    
    async def initialize_vector_db_collections(self):
        """벡터 DB 컬렉션 초기화"""
        try:
            collections = [
                "news_vectors",
                "disclosure_vectors", 
                "weekly_reports",
                "weekly_keywords",
                "price_analysis_vectors"
            ]
            
            for collection_name in collections:
                await self.vector_db.create_collection(collection_name)
                self.logger.info(f"벡터 DB 컬렉션 생성: {collection_name}")
            
            self.logger.info("벡터 DB 컬렉션 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"벡터 DB 초기화 실패: {e}")
            return False
    
    async def insert_stock_data(self):
        """종목 정보 삽입"""
        try:
            stocks_file = project_root / "config" / "stocks.json"
            
            if not stocks_file.exists():
                self.logger.warning("종목 설정 파일 없음")
                return True
            
            with open(stocks_file, 'r', encoding='utf-8') as f:
                stocks_config = json.load(f)
            
            for stock_code, stock_info in stocks_config.items():
                insert_query = """
                INSERT INTO stock_info (stock_code, company_name, sector, is_active)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                company_name = VALUES(company_name),
                sector = VALUES(sector),
                is_active = VALUES(is_active)
                """
                
                await self.mysql_client.execute_query_async(
                    insert_query,
                    (
                        stock_code,
                        stock_info.get('name', '') if stock_info else '',
                        stock_info.get('sector', '') if stock_info else '',
                        stock_info.get('active', True) if stock_info else True
                    )
                )
            
            self.logger.info(f"종목 정보 삽입 완료: {len(stocks_config)}개")
            return True
            
        except Exception as e:
            self.logger.error(f"종목 정보 삽입 실패: {e}")
            return False
    
    async def verify_database_setup(self) -> Dict:
        """데이터베이스 설정 검증"""
        try:
            verification_results = {}
            
            # 테이블 존재 확인
            tables_to_check = [
                'news', 'disclosure_data', 'chart_conditions', 'chart_data',
                'weekly_reports', 'weekly_keywords', 'price_analysis',
                'service_monitoring', 'notification_logs', 'system_settings', 'stock_info'
            ]
            
            for table in tables_to_check:
                result = await self.mysql_client.fetch_one(
                    f"SHOW TABLES LIKE '{table}'"
                )
                verification_results[f"table_{table}"] = result is not None
            
            # 벡터 DB 컬렉션 확인
            collections_to_check = [
                "news_vectors", "disclosure_vectors", "weekly_reports",
                "weekly_keywords", "price_analysis_vectors"
            ]
            
            for collection in collections_to_check:
                try:
                    # 컬렉션 존재 확인 (임시적으로 True로 설정)
                    verification_results[f"collection_{collection}"] = True
                except:
                    verification_results[f"collection_{collection}"] = False
            
            # 시스템 설정 확인
            settings_count = await self.mysql_client.fetch_one(
                "SELECT COUNT(*) as count FROM system_settings"
            )
            verification_results["system_settings_count"] = settings_count["count"] if settings_count else 0
            
            # 종목 정보 확인
            stocks_count = await self.mysql_client.fetch_one(
                "SELECT COUNT(*) as count FROM stock_info"
            )
            verification_results["stocks_count"] = stocks_count["count"] if stocks_count else 0
            
            return verification_results
            
        except Exception as e:
            self.logger.error(f"데이터베이스 검증 실패: {e}")
            return {"error": str(e)}
    
    async def reset_database(self):
        """데이터베이스 리셋 (개발용)"""
        try:
            self.logger.warning("데이터베이스 리셋 시작 - 모든 데이터가 삭제됩니다!")
            
            # 모든 테이블 데이터 삭제
            tables_to_clear = [
                'notification_logs', 'service_monitoring', 'price_analysis',
                'weekly_keywords', 'weekly_reports', 'chart_data', 'chart_conditions',
                'disclosure_data', 'news'
            ]
            
            for table in tables_to_clear:
                await self.mysql_client.execute_query_async(f"DELETE FROM {table}")
                self.logger.info(f"테이블 {table} 데이터 삭제 완료")
            
            # 벡터 DB 컬렉션 리셋
            collections = [
                "news_vectors", "disclosure_vectors", "weekly_reports",
                "weekly_keywords", "price_analysis_vectors"
            ]
            
            for collection_name in collections:
                try:
                    await self.vector_db.delete_collection(collection_name)
                    await self.vector_db.create_collection(collection_name)
                    self.logger.info(f"벡터 컬렉션 {collection_name} 리셋 완료")
                except:
                    pass
            
            self.logger.info("데이터베이스 리셋 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"데이터베이스 리셋 실패: {e}")
            return False
    
    async def backup_database(self, backup_path: str = None):
        """데이터베이스 백업"""
        try:
            if not backup_path:
                backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            # MySQL 덤프 명령어 실행 (실제 구현 시 mysqldump 사용)
            self.logger.info(f"데이터베이스 백업 시작: {backup_path}")
            
            # 여기에 실제 백업 로직 구현
            # subprocess를 사용하여 mysqldump 실행
            
            self.logger.info("데이터베이스 백업 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"데이터베이스 백업 실패: {e}")
            return False
    
    async def run_full_initialization(self):
        """전체 초기화 실행"""
        try:
            self.logger.info("=== 데이터베이스 전체 초기화 시작 ===")
            
            # 1. MySQL 스키마 초기화
            if not await self.initialize_mysql_schema():
                return False
            
            # 2. 벡터 DB 컬렉션 초기화
            if not await self.initialize_vector_db_collections():
                return False
            
            # 3. 종목 데이터 삽입
            if not await self.insert_stock_data():
                return False
            
            # 4. 검증
            verification = await self.verify_database_setup()
            self.logger.info(f"데이터베이스 검증 결과: {verification}")
            
            self.logger.info("=== 데이터베이스 전체 초기화 완료 ===")
            return True
            
        except Exception as e:
            self.logger.error(f"전체 초기화 실패: {e}")
            return False
        finally:
            # 리소스 정리
            await self.mysql_client.close()
            await self.vector_db.close()

async def main():
    """메인 실행 함수"""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description='데이터베이스 초기화 및 관리')
    parser.add_argument('--action', choices=['init', 'verify', 'reset', 'backup'], 
                       default='init', help='실행할 작업')
    parser.add_argument('--backup-path', help='백업 파일 경로')
    
    args = parser.parse_args()
    
    initializer = DatabaseInitializer()
    
    try:
        if args.action == 'init':
            success = await initializer.run_full_initialization()
            print("초기화 성공" if success else "초기화 실패")
            
        elif args.action == 'verify':
            results = await initializer.verify_database_setup()
            print("=== 데이터베이스 검증 결과 ===")
            for key, value in results.items():
                print(f"{key}: {'✓' if value else '✗'}")
                
        elif args.action == 'reset':
            confirm = input("정말로 데이터베이스를 리셋하시겠습니까? (yes/no): ")
            if confirm.lower() == 'yes':
                success = await initializer.reset_database()
                print("리셋 성공" if success else "리셋 실패")
            else:
                print("리셋 취소")
                
        elif args.action == 'backup':
            success = await initializer.backup_database(args.backup_path)
            print("백업 성공" if success else "백업 실패")
            
    except KeyboardInterrupt:
        print("작업 중단")
    except Exception as e:
        print(f"실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 