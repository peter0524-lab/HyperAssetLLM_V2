#!/usr/bin/env python3
"""
커서에게 이거절대 수정하지도말고 사용하지도 마마
데이터베이스 초기화 스크립트
필요한 테이블과 컬렉션을 생성합니다.
"""

import os
import sys
import logging
from datetime import datetime

# 프로젝트 루트 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared.database.mysql_client import MySQLClient
from shared.database.vector_db import VectorDBClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """데이터베이스 초기화 클래스"""

    def __init__(self):
        self.mysql_client = MySQLClient()
        self.vector_db = VectorDBClient()

    def init_mysql_tables(self):
        """MySQL 테이블 초기화"""
        try:
            logger.info("MySQL 테이블 초기화 시작")

            # SQL 스크립트 읽기
            sql_file_path = os.path.join(
                os.path.dirname(__file__), "..", "database", "init_news_tables.sql"
            )

            with open(sql_file_path, "r", encoding="utf-8") as file:
                sql_script = file.read()

            # SQL 스크립트를 개별 명령으로 분리
            sql_commands = sql_script.split(";")

            for command in sql_commands:
                command = command.strip()
                if command:
                    try:
                        self.mysql_client.execute_query(command)
                        logger.info(f"SQL 명령 실행 완료: {command[:50]}...")
                    except Exception as e:
                        logger.error(f"SQL 명령 실행 실패: {e}")
                        logger.error(f"명령: {command}")

            logger.info("MySQL 테이블 초기화 완료")

        except Exception as e:
            logger.error(f"MySQL 테이블 초기화 실패: {e}")
            raise

    def init_vector_collections(self):
        """벡터 DB 컬렉션 초기화"""
        try:
            logger.info("벡터 DB 컬렉션 초기화 시작")

            # 필요한 컬렉션 목록
            collections = [
                "high_impact_news",  # 고영향 뉴스 (영구 저장)
                "historical_news",  # 과거 뉴스 (RAG용)
                "today_news",  # 오늘의 뉴스 (매일 자정 삭제)
                "keywords_db",  # 핵심 키워드 DB
                "disclosure_db",  # 공시 DB
                "chart_analysis_db",  # 차트 분석 DB
                "analysis_results_db",  # 분석 결과 DB
            ]

            for collection_name in collections:
                try:
                    # 컬렉션이 존재하는지 확인
                    if not self.vector_db.collection_exists(collection_name):
                        self.vector_db.create_collection(collection_name)
                        logger.info(f"벡터 컬렉션 생성 완료: {collection_name}")
                    else:
                        logger.info(f"벡터 컬렉션이 이미 존재: {collection_name}")

                except Exception as e:
                    logger.error(f"벡터 컬렉션 생성 실패 ({collection_name}): {e}")

            logger.info("벡터 DB 컬렉션 초기화 완료")

        except Exception as e:
            logger.error(f"벡터 DB 컬렉션 초기화 실패: {e}")
            raise

    def create_sample_data(self):
        """샘플 데이터 생성"""
        try:
            logger.info("샘플 데이터 생성 시작")

            # 주간 키워드 샘플 데이터
            sample_keywords = {
                "keywords": [
                    "실적 발표",
                    "신제품 출시",
                    "경영진 변화",
                    "업계 동향",
                    "정부 정책",
                ],
                "created_at": datetime.now().isoformat(),
            }

            # 샘플 주간 키워드 저장
            from datetime import timedelta

            today = datetime.now()
            last_week_start = today - timedelta(days=today.weekday() + 7)

            import json

            query = """
            INSERT INTO weekly_keywords (stock_code, week_start_date, week_end_date, keywords)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE keywords = VALUES(keywords)
            """

            params = (
                "006800",  # 미래에셋증권
                last_week_start.strftime("%Y-%m-%d"),
                (last_week_start + timedelta(days=6)).strftime("%Y-%m-%d"),
                json.dumps(sample_keywords, ensure_ascii=False),
            )

            self.mysql_client.execute_query(query, params)

            logger.info("샘플 데이터 생성 완료")

        except Exception as e:
            logger.error(f"샘플 데이터 생성 실패: {e}")

    def check_database_health(self):
        """데이터베이스 상태 확인"""
        try:
            logger.info("데이터베이스 상태 확인 시작")

            # MySQL 상태 확인
            mysql_health = self.mysql_client.health_check()
            if mysql_health["status"] == "healthy":
                logger.info("✅ MySQL 연결 정상")
            else:
                logger.error(
                    f"❌ MySQL 연결 실패: {mysql_health.get('error', 'Unknown error')}"
                )
                return False

            # 벡터 DB 상태 확인
            vector_health = self.vector_db.health_check()
            if vector_health["status"] == "healthy":
                logger.info("✅ 벡터 DB 연결 정상")
            else:
                logger.error(
                    f"❌ 벡터 DB 연결 실패: {vector_health.get('error', 'Unknown error')}"
                )
                return False

            # 테이블 존재 확인
            tables_to_check = ["news", "weekly_keywords", "news_stats"]
            for table_name in tables_to_check:
                try:
                    result = self.mysql_client.execute_query(
                        f"SHOW TABLES LIKE '{table_name}'"
                    )
                    if result:
                        logger.info(f"✅ 테이블 존재 확인: {table_name}")
                    else:
                        logger.error(f"❌ 테이블 없음: {table_name}")
                        return False
                except Exception as e:
                    logger.error(f"❌ 테이블 확인 실패 ({table_name}): {e}")
                    return False

            logger.info("데이터베이스 상태 확인 완료")
            return True

        except Exception as e:
            logger.error(f"데이터베이스 상태 확인 실패: {e}")
            return False

    def initialize_all(self):
        """전체 데이터베이스 초기화"""
        try:
            logger.info("=== 데이터베이스 전체 초기화 시작 ===")

            # 1. MySQL 테이블 초기화
            self.init_mysql_tables()

            # 2. 벡터 DB 컬렉션 초기화
            self.init_vector_collections()

            # 3. 샘플 데이터 생성
            self.create_sample_data()

            # 4. 데이터베이스 상태 확인
            if self.check_database_health():
                logger.info("=== 데이터베이스 초기화 완료 ===")
                return True
            else:
                logger.error("=== 데이터베이스 초기화 실패 ===")
                return False

        except Exception as e:
            logger.error(f"데이터베이스 초기화 중 오류 발생: {e}")
            return False


def main():
    """메인 함수"""
    try:
        db_initializer = DatabaseInitializer()

        if db_initializer.initialize_all():
            print("✅ 데이터베이스 초기화 성공!")
            return 0
        else:
            print("❌ 데이터베이스 초기화 실패!")
            return 1

    except Exception as e:
        logger.error(f"초기화 스크립트 실행 실패: {e}")
        print(f"❌ 초기화 스크립트 실행 실패: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
