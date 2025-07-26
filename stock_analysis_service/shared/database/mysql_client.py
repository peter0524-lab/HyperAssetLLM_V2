# type: ignore
"""
MySQL 데이터베이스 클라이언트 모듈
차트 패턴 데이터와 공시 데이터를 관리하는 MySQL 연결 및 쿼리 기능 제공
"""

import pymysql
import pymysql.cursors
from pymysql import Error as PyMySQLError
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, date
import json
from contextlib import contextmanager
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가 (stock_analysis_service)
project_root = Path(__file__).parent.parent.parent  # shared/database -> shared -> stock_analysis_service
sys.path.append(str(project_root))

# config 모듈 직접 import
config_path = project_root / "config"
sys.path.append(str(config_path))

from env_local import get_env_var, get_int_env_var, get_bool_env_var, load_env_vars
import asyncio
import threading
import queue
import time

# 환경 변수 로드 강제 실행
load_env_vars()

# 로깅 설정
logger = logging.getLogger(__name__)


class MySQLConnectionPool:
    """PyMySQL 기반 연결 풀 구현"""
    
    def __init__(self, pool_size: int = 10, **connection_params):
        self.pool_size = pool_size
        self.connection_params = connection_params
        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self._create_pool()
    
    def _create_pool(self):
        """연결 풀 생성"""
        for _ in range(self.pool_size):
            try:
                connection = pymysql.connect(**self.connection_params)
                self.pool.put(connection)
            except Exception as e:
                logger.error(f"연결 풀 생성 실패: {e}")
                raise
    
    def get_connection(self):
        """연결 풀에서 연결 가져오기"""
        try:
            connection = self.pool.get(timeout=5)  # 타임아웃 단축
            if not connection.open:
                # 연결이 닫혔다면 새로 생성
                connection.close()  # 기존 연결 완전히 닫기
                connection = pymysql.connect(**self.connection_params)
            return connection
        except queue.Empty:
            # 풀에 연결이 없다면 새로 생성 (임시 연결)
            logger.warning("연결 풀 고갈, 임시 연결 생성")
            return pymysql.connect(**self.connection_params)
    
    def return_connection(self, connection):
        """연결을 풀에 반환"""
        if connection:
            try:
                if connection.open:
                    # 연결이 정상이면 풀에 반환
                    self.pool.put_nowait(connection)
                else:
                    # 연결이 닫혔으면 완전히 닫기
                    connection.close()
            except queue.Full:
                # 풀이 가득 차면 연결 닫기
                logger.warning("연결 풀 가득참, 연결 닫기")
                connection.close()
            except Exception as e:
                # 예외 발생시 연결 닫기
                logger.error(f"연결 반환 중 오류: {e}")
                try:
                    connection.close()
                except:
                    pass


class MySQLClient:
    """MySQL 데이터베이스 클라이언트 클래스"""

    def __init__(self, custom_config: Dict = None):
        """MySQL 연결 풀 초기화"""
        self.pool = None
        self._initialize_pool(custom_config)

    def _initialize_pool(self, custom_config: Dict = None) -> None:
        """MySQL 연결 풀 생성"""
        try:
            env_config = {
                "user": get_env_var("DATABASE_USER", "root"),
                "password": get_env_var("DATABASE_PASSWORD", ""),
                "host": get_env_var("DATABASE_HOST", "127.0.0.1"),
                "port": get_int_env_var("DATABASE_PORT", 3306),
                "database": get_env_var("DATABASE_NAME", "backendTest"),
                "charset": "utf8mb4",
                "autocommit": True,
                "cursorclass": pymysql.cursors.DictCursor,
                "connect_timeout": 30,
                "read_timeout": 30,
                "write_timeout": 30,
                "ssl_disabled": True,  # AWS RDS SSL 비활성화
            }
            
            # custom_config가 전달되면 env_config을 덮어쓰기
            if custom_config:
                env_config.update(custom_config)
            config = env_config

            # 연결 풀 크기 설정 (매우 작게 설정)
            pool_size = min(2, max(1, get_int_env_var("DATABASE_CONNECTION_LIMIT", 1)))
            
            # 연결 풀에서 사용하지 않는 설정 제거
            pool_config = {k: v for k, v in config.items() if k not in ['pool_name', 'pool_size', 'pool_reset_session', 'sql_mode']}
            
            self.pool = MySQLConnectionPool(pool_size=pool_size, **pool_config)
            logger.info(
                f"MySQL 연결 풀 생성 완료: {config['host']}:{config['port']}/{config['database']}"
            )

        except Exception as e:
            logger.error(f"MySQL 연결 풀 생성 실패: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기 (컨텍스트 매니저)"""
        connection = None
        try:
            connection = self.pool.get_connection()
            yield connection
        except Exception as e:
            logger.error(f"MySQL 연결 오류: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                self.pool.return_connection(connection)

    def execute_query(
        self, query: str, params: Optional[tuple] = None, fetch: bool = True
    ) -> Optional[List[Dict]]:
        """쿼리 실행 및 결과 반환"""
        try:
            if not self.pool:
                return None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)

                if fetch:
                    result = cursor.fetchall()
                    cursor.close()
                    return result
                else:
                    conn.commit()
                    affected_rows = cursor.rowcount
                    cursor.close()
                    return [{"affected_rows": affected_rows}]

        except Exception as e:
            logger.error(f"쿼리 실행 오류: {e}")
            logger.error(f"쿼리: {query}")
            logger.error(f"파라미터: {params}")
            raise

    def execute_many(self, query: str, params_list: List[tuple]) -> Dict:
        """여러 행 일괄 삽입/업데이트"""
        try:
            if not self.pool:
                return {"affected_rows": 0}
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                affected_rows = cursor.rowcount
                cursor.close()
                return {"affected_rows": affected_rows}

        except Exception as e:
            logger.error(f"일괄 쿼리 실행 오류: {e}")
            return {"affected_rows": 0}

    # === 비동기 래퍼 메서드 ===
    async def execute_query_async(
        self, query: str, params: tuple = None, fetch: bool = True
    ) -> Optional[List[Dict]]:
        """비동기 쿼리 실행 (ThreadPoolExecutor 래퍼)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.execute_query, query, params, fetch
        )

    async def execute_many_async(self, query: str, params_list: List[tuple]) -> Dict:
        """비동기 executemany 실행 (ThreadPoolExecutor 래퍼)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_many, query, params_list)

    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """단일 행 조회"""
        try:
            if not self.pool:
                return None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
                cursor.close()
                return result
        except Exception as e:
            logger.error(f"fetch_one 실행 오류: {e}")
            return None

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """모든 행 조회"""
        try:
            if not self.pool:
                return []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall()
                cursor.close()
                return result if result else []
        except Exception as e:
            logger.error(f"fetch_all 실행 오류: {e}")
            return []

    async def fetch_one_async(self, query: str, params: tuple = None) -> Optional[tuple]:
        """비동기 단일 레코드 조회 (ThreadPoolExecutor 래퍼)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_one, query, params)

    async def fetch_all_async(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """비동기 모든 행 조회"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_all, query, params)

    async def close(self) -> None:
        """연결 풀 정리"""
        try:
            if self.pool:
                logger.info("MySQL 연결 풀 정리 중...")
                # 모든 연결 닫기
                while not self.pool.pool.empty():
                    conn = self.pool.pool.get_nowait()
                    if conn and conn.open:
                        conn.close()
                logger.info("MySQL 연결 풀 정리 완료")
        except Exception as e:
            logger.error(f"MySQL 연결 풀 정리 실패: {e}")
            raise

    def get_current_price_data(self, stock_code: str) -> Optional[Dict]:
        """현재 주가 데이터 조회"""
        query = """
        SELECT stock_code, current_price, change_rate, volume, trade_date
        FROM stock_prices 
        WHERE stock_code = %s 
        ORDER BY trade_date DESC, trade_time DESC 
        LIMIT 1
        """
        return self.fetch_one(query, (stock_code,))

    def run_service(self, service_name: str) -> Dict:
        """서비스 실행 상태 업데이트"""
        query = """
        UPDATE service_status 
        SET status = 'running', last_updated = NOW()
        WHERE service_name = %s
        """
        return self.execute_query(query, (service_name,), fetch=False)

    def get_chart_patterns(
        self,
        stock_code: str,
        condition_id: str = None,
        start_date: date = None,
        end_date: date = None,
    ) -> List[Dict]:
        """차트 패턴 데이터 조회"""
        query = """
        SELECT 
            id, stock_code, stock_name, condition_id, condition_name,
            trigger_date, trigger_time, price, volume, 
            pattern_data, similar_volume, created_at
        FROM chart_patterns 
        WHERE stock_code = %s
        """
        params = [stock_code]

        if condition_id:
            query += " AND condition_id = %s"
            params.append(condition_id)

        if start_date:
            query += " AND trigger_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND trigger_date <= %s"
            params.append(end_date)

        query += " ORDER BY trigger_date DESC, trigger_time DESC"

        return self.execute_query(query, tuple(params))

    def save_chart_pattern(self, pattern_data: Dict) -> int:
        """차트 패턴 데이터 저장"""
        query = """
        INSERT INTO chart_patterns (
            stock_code, stock_name, condition_id, condition_name,
            trigger_date, trigger_time, price, volume, 
            pattern_data, similar_volume, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        params = (
            pattern_data["stock_code"],
            pattern_data["stock_name"],
            pattern_data["condition_id"],
            pattern_data["condition_name"],
            pattern_data["trigger_date"],
            pattern_data["trigger_time"],
            pattern_data["price"],
            pattern_data["volume"],
            json.dumps(pattern_data.get("pattern_data", {}), ensure_ascii=False),
            pattern_data.get("similar_volume", 0),
            datetime.now(),
        )

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                pattern_id = cursor.lastrowid
                cursor.close()
                logger.info(f"차트 패턴 저장 완료: ID={pattern_id}")
                return pattern_id

        except Exception as e:
            logger.error(f"차트 패턴 저장 오류: {e}")
            raise

    def get_disclosures(
        self, stock_code: str, start_date: date = None, end_date: date = None
    ) -> List[Dict]:
        """공시 데이터 조회"""
        query = """
        SELECT 
            id, stock_code, stock_name, disclosure_type, title, 
            summary, impact_score, similar_case, publication_date,
            created_at, updated_at
        FROM disclosures 
        WHERE stock_code = %s
        """
        params = [stock_code]

        if start_date:
            query += " AND publication_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND publication_date <= %s"
            params.append(end_date)

        query += " ORDER BY publication_date DESC"

        return self.execute_query(query, tuple(params))

    def save_disclosure(self, disclosure_data: Dict) -> int:
        """공시 데이터 저장"""
        query = """
        INSERT INTO disclosures (
            stock_code, stock_name, disclosure_type, title, 
            summary, impact_score, similar_case, publication_date,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        params = (
            disclosure_data["stock_code"],
            disclosure_data["stock_name"],
            disclosure_data["disclosure_type"],
            disclosure_data["title"],
            disclosure_data["summary"],
            disclosure_data.get("impact_score", 0.0),
            disclosure_data.get("similar_case", ""),
            disclosure_data["publication_date"],
            datetime.now(),
            datetime.now(),
        )

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                disclosure_id = cursor.lastrowid
                cursor.close()
                logger.info(f"공시 데이터 저장 완료: ID={disclosure_id}")
                return disclosure_id

        except Exception as e:
            logger.error(f"공시 데이터 저장 오류: {e}")
            raise

    def get_similar_chart_pattern(
        self, stock_code: str, condition_id: str, current_volume: int
    ) -> Optional[Dict]:
        """유사한 차트 패턴 검색 (가장 유사한 거래량 + 최근 케이스)"""
        query = """
        SELECT 
            id, stock_code, stock_name, condition_id, condition_name,
            trigger_date, trigger_time, price, volume, 
            pattern_data, similar_volume, created_at,
            ABS(volume - %s) as volume_diff
        FROM chart_patterns 
        WHERE stock_code = %s AND condition_id = %s
        ORDER BY volume_diff ASC, trigger_date DESC
        LIMIT 1
        """

        params = (current_volume, stock_code, condition_id)
        result = self.execute_query(query, params)

        return result[0] if result else None

    def get_system_metrics(self) -> Dict:
        """시스템 메트릭 조회"""
        queries = {
            "chart_patterns_count": "SELECT COUNT(*) as count FROM chart_patterns",
            "disclosures_count": "SELECT COUNT(*) as count FROM disclosures",
            "recent_chart_patterns": """
                SELECT COUNT(*) as count FROM chart_patterns 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """,
            "recent_disclosures": """
                SELECT COUNT(*) as count FROM disclosures 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """,
        }

        metrics = {}
        for key, query in queries.items():
            try:
                result = self.execute_query(query)
                metrics[key] = result[0]["count"] if result else 0
            except Exception as e:
                logger.error(f"메트릭 조회 오류 ({key}): {e}")
                metrics[key] = 0

        return metrics

    def health_check(self) -> Dict:
        """데이터베이스 상태 확인"""
        try:
            start_time = time.time()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT VERSION()")
                version_result = cursor.fetchone()
                version = version_result.get('VERSION()', 'Unknown') if version_result else 'Unknown'
                
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()

                connection_time = time.time() - start_time

                return {
                    "status": "healthy",
                    "version": version,
                    "connection_time": f"{connection_time:.3f}s",
                    "connection_pool_size": self.pool.pool_size,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"데이터베이스 상태 확인 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


def init_database() -> None:
    """데이터베이스 초기화 - 테이블 생성"""
    client = MySQLClient()

    # 차트 패턴 테이블
    chart_patterns_table = """
    CREATE TABLE IF NOT EXISTS chart_patterns (
        id INT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL,
        stock_name VARCHAR(100) NOT NULL,
        condition_id VARCHAR(50) NOT NULL,
        condition_name VARCHAR(100) NOT NULL,
        trigger_date DATE NOT NULL,
        trigger_time TIME NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        volume BIGINT NOT NULL,
        pattern_data JSON,
        similar_volume BIGINT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_stock_code (stock_code),
        INDEX idx_condition_id (condition_id),
        INDEX idx_trigger_date (trigger_date),
        INDEX idx_volume (volume),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    # 공시 데이터 테이블
    disclosures_table = """
    CREATE TABLE IF NOT EXISTS disclosures (
        id INT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL,
        stock_name VARCHAR(100) NOT NULL,
        disclosure_type VARCHAR(50) NOT NULL,
        title VARCHAR(500) NOT NULL,
        summary TEXT,
        impact_score DECIMAL(3, 2) DEFAULT 0.00,
        similar_case TEXT,
        publication_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_stock_code (stock_code),
        INDEX idx_disclosure_type (disclosure_type),
        INDEX idx_publication_date (publication_date),
        INDEX idx_impact_score (impact_score),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    try:
        # 테이블 생성
        client.execute_query(chart_patterns_table, fetch=False)
        client.execute_query(disclosures_table, fetch=False)

        logger.info("데이터베이스 초기화 완료")
        print("✅ 데이터베이스 초기화 완료")

    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        raise


# 전역 MySQL 클라이언트 인스턴스 (지연 초기화)
mysql_client = None


def get_mysql_client() -> MySQLClient:
    """MySQL 클라이언트 인스턴스 반환 (지연 초기화)"""
    global mysql_client
    if mysql_client is None:
        mysql_client = MySQLClient()
    return mysql_client
