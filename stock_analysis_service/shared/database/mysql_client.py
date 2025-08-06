# type: ignore
"""
개선된 MySQL 데이터베이스 클라이언트 모듈
연결 풀 리소스 관리 및 안정성 개선
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
import threading
import queue
import time
import weakref
import atexit
import signal
import gc
import asyncio

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

config_path = project_root / "config"
sys.path.append(str(config_path))

from env_local import get_env_var, get_int_env_var, get_bool_env_var, load_env_vars, get_config

# 환경 변수 로드
load_env_vars()

# 로깅 설정
logger = logging.getLogger(__name__)


class ConnectionWrapper:
    """연결 래퍼 클래스 - 연결 상태 추적 및 자동 정리"""
    
    def __init__(self, connection, pool_ref):
        self.connection = connection
        self.pool_ref = pool_ref  # 약한 참조
        self.created_at = time.time()
        self.last_used = time.time()
        self.is_in_use = False
        self.use_count = 0
    
    def __getattr__(self, name):
        """연결 객체의 속성/메서드 프록시"""
        return getattr(self.connection, name)
    
    def mark_used(self):
        """사용 시점 기록"""
        self.last_used = time.time()
        self.use_count += 1
        self.is_in_use = True
    
    def mark_returned(self):
        """반환 시점 기록"""
        self.is_in_use = False
    
    def is_expired(self, max_age=1800):
        """연결 만료 확인 (기본 30분으로 단축)"""
        return (time.time() - self.created_at) > max_age
    
    def is_idle_too_long(self, max_idle=600):
        """유휴 시간 초과 확인 (기본 10분으로 단축)"""
        return not self.is_in_use and (time.time() - self.last_used) > max_idle


class MySQLConnectionPool:
    """개선된 PyMySQL 기반 연결 풀"""
    
    def __init__(self, pool_size: int = 3, max_overflow: int = 2, **connection_params):
        self.pool_size = min(pool_size, 3)  # 최대 3개로 제한
        self.max_overflow = min(max_overflow, 2)  # overflow도 2개로 제한
        self.connection_params = connection_params
        self.pool = queue.Queue(maxsize=self.pool_size + self.max_overflow)
        self.lock = threading.RLock()  # 재진입 가능한 락
        self.active_connections = set()  # 활성 연결 추적
        self.total_created = 0
        self.is_closed = False
        
        # 정리 스레드
        self.cleanup_thread = None
        self.stop_cleanup = threading.Event()
        
        # DB 이름 로깅을 위해 추가
        self.db_name = connection_params.get("database", "UNKNOWN_DB")
        
        self._create_initial_pool()
        self._start_cleanup_thread()
        
        # 프로그램 종료 시 정리
        atexit.register(self.close_all)
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        except ValueError:
            # 메인 스레드가 아닌 경우 시그널 핸들러 등록 불가
            pass
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info(f"시그널 {signum} 수신, 연결 풀 정리 중 ({self.db_name})...")
        self.close_all()
    
    def _create_initial_pool(self):
        """초기 연결 풀 생성 - 더 보수적으로"""
        initial_size = 1  # 초기에는 1개만 생성
        
        for i in range(initial_size):
            try:
                conn_wrapper = self._create_connection()
                if conn_wrapper:
                    self.pool.put_nowait(conn_wrapper)
                    logger.debug(f"[{self.db_name}] 초기 연결 {i+1}/{initial_size} 생성 완료")
            except Exception as e:
                logger.error(f"[{self.db_name}] 초기 연결 {i+1} 생성 실패: {e}")
                if i == 0:  # 첫 번째 연결도 실패하면 에러
                    raise
    
    def _create_connection(self) -> Optional[ConnectionWrapper]:
        """새 연결 생성"""
        try:
            # 연결 파라미터 최적화 - 더 짧은 타임아웃
            optimized_params = self.connection_params.copy()
            optimized_params.update({
                'connect_timeout': 15,      # 연결 타임아웃 단축
                'read_timeout': 30,         # 읽기 타임아웃
                'write_timeout': 30,        # 쓰기 타임아웃
                'autocommit': True,
                'charset': 'utf8mb4',
                'use_unicode': True,
                'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO',
                'init_command': "SET SESSION wait_timeout=1800, interactive_timeout=1800",  # 30분
            })
            
            connection = pymysql.connect(**optimized_params)
            wrapper = ConnectionWrapper(connection, weakref.ref(self))
            
            with self.lock:
                self.total_created += 1
                self.active_connections.add(wrapper)
            
            logger.debug(f"[{self.db_name}] 새 연결 생성 완료 (총 생성: {self.total_created})")
            return wrapper
            
        except Exception as e:
            logger.error(f"[{self.db_name}] 연결 생성 실패: {e}")
            return None
    
    def get_connection(self, timeout=20):
        """연결 풀에서 연결 가져오기 - 더 짧은 타임아웃"""
        if self.is_closed:
            raise RuntimeError(f"[{self.db_name}] 연결 풀이 닫혔습니다")
        
        start_time = time.time()
        
        try:
            # 1. 풀에서 사용 가능한 연결 찾기
            while time.time() - start_time < timeout:
                try:
                    wrapper = self.pool.get_nowait()
                    
                    # 연결 상태 확인
                    if self._is_connection_valid(wrapper):
                        wrapper.mark_used()
                        logger.debug(f"[{self.db_name}] 풀에서 연결 가져옴")
                        return wrapper
                    else:
                        # 유효하지 않은 연결 정리
                        self._close_connection(wrapper)
                        continue
                        
                except queue.Empty:
                    break
            
            # 2. 새 연결 생성 (overflow 허용)
            if self.total_created < (self.pool_size + self.max_overflow):
                wrapper = self._create_connection()
                if wrapper:
                    wrapper.mark_used()
                    logger.debug(f"[{self.db_name}] 새 연결 생성하여 반환")
                    return wrapper
            
            # 3. 대기 (blocking) - 더 짧은 대기
            logger.warning(f"[{self.db_name}] 연결 풀 고갈, 대기 중...")
            try:
                remaining_time = max(1, timeout - (time.time() - start_time))
                wrapper = self.pool.get(timeout=remaining_time)
                if self._is_connection_valid(wrapper):
                    wrapper.mark_used()
                    return wrapper
                else:
                    self._close_connection(wrapper)
                    raise queue.Empty()
            except queue.Empty:
                pass
        
        except Exception as e:
            logger.error(f"[{self.db_name}] 연결 가져오기 실패: {e}")
        
        raise RuntimeError(f"[{self.db_name}] 연결 획득 실패 (timeout: {timeout}s)")
    
    def return_connection(self, wrapper):
        """연결을 풀에 반환"""
        if not wrapper or self.is_closed:
            return
        
        try:
            wrapper.mark_returned()
            
            # 연결 상태 확인
            if not self._is_connection_valid(wrapper):
                self._close_connection(wrapper)
                return
            
            # 만료된 연결 정리
            if wrapper.is_expired() or wrapper.is_idle_too_long():
                logger.debug(f"[{self.db_name}] 만료된 연결 정리")
                self._close_connection(wrapper)
                return
            
            # 풀에 반환
            try:
                self.pool.put_nowait(wrapper)
                logger.debug(f"[{self.db_name}] 연결 풀에 반환")
            except queue.Full:
                # 풀이 가득 차면 연결 닫기
                logger.debug(f"[{self.db_name}] 풀 가득참, 연결 닫기")
                self._close_connection(wrapper)
                
        except Exception as e:
            logger.error(f"[{self.db_name}] 연결 반환 중 오류: {e}")
            self._close_connection(wrapper)
    
    def _is_connection_valid(self, wrapper) -> bool:
        """연결 유효성 검사"""
        try:
            if not wrapper or not hasattr(wrapper, 'connection'):
                return False
            
            connection = wrapper.connection
            if not connection or not connection.open:
                return False
            
            # ping 테스트 (빠른 실패)
            connection.ping(reconnect=False)
            return True
            
        except Exception as e:
            logger.debug(f"[{self.db_name}] 연결 유효성 검사 실패: {e}")
            return False
    
    def _close_connection(self, wrapper):
        """연결 안전하게 닫기"""
        try:
            if wrapper and hasattr(wrapper, 'connection'):
                with self.lock:
                    self.active_connections.discard(wrapper)
                
                if wrapper.connection and wrapper.connection.open:
                    wrapper.connection.close()
                    logger.debug(f"[{self.db_name}] 연결 정리 완료")
        except Exception as e:
            logger.debug(f"[{self.db_name}] 연결 정리 중 오류 (무시됨): {e}")
    
    def _start_cleanup_thread(self):
        """정리 스레드 시작"""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            return
        
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name=f"MySQL-Pool-Cleanup-{self.db_name}",
            daemon=True
        )
        self.cleanup_thread.start()
        logger.debug(f"[{self.db_name}] 정리 스레드 시작됨")
    
    def _cleanup_worker(self):
        """정리 작업자 스레드 - 더 자주 정리"""
        while not self.stop_cleanup.wait(30):  # 30초마다 정리
            try:
                self._cleanup_expired_connections()
                self._cleanup_memory()
            except Exception as e:
                logger.debug(f"[{self.db_name}] 정리 작업 중 오류: {e}")
    
    def _cleanup_expired_connections(self):
        """만료된 연결 정리"""
        expired_connections = []
        
        # 임시 리스트에 연결들 수집
        temp_connections = []
        while not self.pool.empty():
            try:
                wrapper = self.pool.get_nowait()
                temp_connections.append(wrapper)
            except queue.Empty:
                break
        
        # 유효한 연결만 다시 풀에 넣기
        for wrapper in temp_connections:
            if wrapper.is_expired() or wrapper.is_idle_too_long() or not self._is_connection_valid(wrapper):
                expired_connections.append(wrapper)
            else:
                try:
                    self.pool.put_nowait(wrapper)
                except queue.Full:
                    expired_connections.append(wrapper)
        
        # 만료된 연결 정리
        for wrapper in expired_connections:
            self._close_connection(wrapper)
        
        if expired_connections:
            logger.debug(f"[{self.db_name}] 만료된 연결 {len(expired_connections)}개 정리")
    
    def _cleanup_memory(self):
        """메모리 정리"""
        try:
            gc.collect()
        except Exception:
            pass
    
    def get_stats(self) -> Dict:
        """풀 통계 정보"""
        with self.lock:
            return {
                'pool_size': self.pool_size,
                'max_overflow': self.max_overflow,
                'active_connections': len(self.active_connections),
                'available_connections': self.pool.qsize(),
                'total_created': self.total_created,
                'is_closed': self.is_closed,
                'db_name': self.db_name # DB 이름 추가
            }
    
    def close_all(self):
        """모든 연결 정리"""
        if self.is_closed:
            return
        
        logger.info(f"[{self.db_name}] 연결 풀 정리 시작...")
        self.is_closed = True
        
        # 정리 스레드 중단
        if self.cleanup_thread:
            self.stop_cleanup.set()
            if self.cleanup_thread.is_alive():
                self.cleanup_thread.join(timeout=5)
        
        # 풀의 모든 연결 정리
        closed_count = 0
        while not self.pool.empty():
            try:
                wrapper = self.pool.get_nowait()
                self._close_connection(wrapper)
                closed_count += 1
            except queue.Empty:
                break
        
        # 활성 연결 정리
        with self.lock:
            active_copy = self.active_connections.copy()
            for wrapper in active_copy:
                self._close_connection(wrapper)
                closed_count += 1
            self.active_connections.clear()
        
        logger.info(f"[{self.db_name}] 연결 풀 정리 완료: {closed_count}개 연결 닫음")


class MySQLClient:
    """개선된 MySQL 데이터베이스 클라이언트"""

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
                "ssl_disabled": get_bool_env_var("DATABASE_SSL_DISABLED", True),
            }
            
            if custom_config:
                env_config.update(custom_config)

            # 연결 풀 설정 최적화 - custom_config에 connection_limit이 있다면 사용하고, 없으면 기존 env_config에서 가져옴
            pool_size = min(2, custom_config.get("connection_limit", get_int_env_var("DATABASE_CONNECTION_LIMIT", 2)))
            max_overflow = min(2, custom_config.get("max_overflow", get_int_env_var("DATABASE_MAX_OVERFLOW", 2)))
            
            self.pool = MySQLConnectionPool(
                pool_size=pool_size,
                max_overflow=max_overflow,
                **env_config
            )
            
            logger.info(f"MySQL 연결 풀 생성 완료: {env_config['host']}:{env_config['port']}/{env_config['database']} (pool_size={pool_size}, max_overflow={max_overflow})")

        except Exception as e:
            # 에러 로깅에 DB 이름 추가
            db_name = env_config.get('database', 'UNKNOWN_DB')
            logger.error(f"MySQL 연결 풀 생성 실패 ({db_name}): {e}")
            raise

    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기 (컨텍스트 매니저)"""
        if not self.pool:
            raise RuntimeError("연결 풀이 초기화되지 않았습니다")
        
        connection = None
        try:
            connection = self.pool.get_connection(timeout=20)
            yield connection
        except Exception as e:
            # 에러 로깅에 DB 이름 추가
            db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
            logger.error(f"[{db_name}] MySQL 연결 오류: {e}")
            if connection and hasattr(connection, 'rollback'):
                try:
                    connection.rollback()
                except:
                    pass
            raise
        finally:
            if connection:
                self.pool.return_connection(connection)

    def execute_query(
        self, query: str, params: Optional[tuple] = None, fetch: bool = True
    ) -> Optional[List[Dict]]:
        """쿼리 실행 및 결과 반환"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)

                    if fetch:
                        result = cursor.fetchall()
                    else:
                        conn.commit()
                        result = [{"affected_rows": cursor.rowcount}]
                    
                    cursor.close()
                    return result

            except Exception as e:
                # 에러 로깅에 DB 이름 추가
                db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
                logger.warning(f"[{db_name}] 쿼리 실행 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"[{db_name}] 쿼리 실행 최종 실패: {query}")
                raise
            time.sleep(0.5 * (attempt + 1))  # 점진적 대기

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
            # 에러 로깅에 DB 이름 추가
            db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
            logger.error(f"[{db_name}] 일괄 쿼리 실행 오류: {e}")
            return {"affected_rows": 0}

    # === 비동기 래퍼 메서드 ===
    async def execute_query_async(
        self, query: str, params: tuple = None, fetch: bool = True, max_retries: int = 3
    ) -> Optional[List[Dict]]:
        """비동기 쿼리 실행 (ThreadPoolExecutor 래퍼) - 재시도 로직 포함"""
        loop = asyncio.get_event_loop()
        
        for attempt in range(max_retries):
            try:
                return await loop.run_in_executor(
                    None, self.execute_query, query, params, fetch
                )
            except Exception as e:
                # 에러 로깅에 DB 이름 추가
                db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
                logger.warning(f"[{db_name}] 쿼리 실행 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"[{db_name}] 최대 재시도 횟수 초과, 쿼리 실행 실패: {query}")
                    raise
                # 재시도 전 잠시 대기
                await asyncio.sleep(1 * (attempt + 1))  # 지수 백오프
        
        return None

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
            # 에러 로깅에 DB 이름 추가
            db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
            logger.error(f"[{db_name}] fetch_one 실행 오류: {e}")
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
            # 에러 로깅에 DB 이름 추가
            db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
            logger.error(f"[{db_name}] fetch_all 실행 오류: {e}")
            return []

    async def fetch_one_async(self, query: str, params: tuple = None) -> Optional[Dict]:
        """비동기 단일 레코드 조회 (ThreadPoolExecutor 래퍼)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_one, query, params)

    async def fetch_all_async(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """비동기 모든 행 조회"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_all, query, params)

    def health_check(self) -> Dict:
        """데이터베이스 상태 확인"""
        try:
            start_time = time.time()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT VERSION() as version, CONNECTION_ID() as conn_id")
                result = cursor.fetchone()
                cursor.close()

                connection_time = time.time() - start_time
                pool_stats = self.pool.get_stats() if self.pool else {}

                return {
                    "status": "healthy",
                    "version": result.get('version', 'Unknown') if result else 'Unknown',
                    "connection_id": result.get('conn_id', 0) if result else 0,
                    "connection_time": f"{connection_time:.3f}s",
                    "pool_stats": pool_stats,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            # 에러 로깅에 DB 이름 추가
            db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
            logger.error(f"[{db_name}] 데이터베이스 상태 확인 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "pool_stats": self.pool.get_stats() if self.pool else {},
                "timestamp": datetime.now().isoformat(),
            }

    async def close(self) -> None:
        """연결 풀 정리"""
        try:
            if self.pool:
                self.pool.close_all()
                self.pool = None
                # 로깅에 DB 이름 추가
                logger.info(f"[{self.pool.db_name if self.pool else 'UNKNOWN_DB'}] MySQL 클라이언트 정리 완료")
        except Exception as e:
            # 로깅에 DB 이름 추가
            db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
            logger.error(f"[{db_name}] MySQL 클라이언트 정리 실패: {e}")

    # === 기존 데이터베이스 메서드들 유지 ===
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
                # 로깅에 DB 이름 추가
                db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
                logger.info(f"[{db_name}] 차트 패턴 저장 완료: ID={pattern_id}")
                return pattern_id

        except Exception as e:
            # 로깅에 DB 이름 추가
            db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
            logger.error(f"[{db_name}] 차트 패턴 저장 오류: {e}")
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
                # 로깅에 DB 이름 추가
                db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
                logger.info(f"[{db_name}] 공시 데이터 저장 완료: ID={disclosure_id}")
                return disclosure_id

        except Exception as e:
            # 로깅에 DB 이름 추가
            db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
            logger.error(f"[{db_name}] 공시 데이터 저장 오류: {e}")
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
                # 에러 로깅에 DB 이름 추가
                db_name = self.pool.db_name if self.pool else "UNKNOWN_DB"
                logger.error(f"[{db_name}] 메트릭 조회 오류 ({key}): {e}")
                metrics[key] = 0

        return metrics


def init_database(db_config_key: str = "mysql") -> None:
    """데이터베이스 초기화 - 테이블 생성"""
    client = get_mysql_client(db_config_key=db_config_key)

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

        logger.info(f"[{client.pool.db_name if client.pool else 'UNKNOWN_DB'}] 데이터베이스 초기화 완료")
        print(f"✅ [{client.pool.db_name if client.pool else 'UNKNOWN_DB'}] 데이터베이스 초기화 완료")

    except Exception as e:
        logger.error(f"[{client.pool.db_name if client.pool else 'UNKNOWN_DB'}] 데이터베이스 초기화 실패: {e}")
        print(f"❌ [{client.pool.db_name if client.pool else 'UNKNOWN_DB'}] 데이터베이스 초기화 실패: {e}")
        raise


# 전역 클라이언트 인스턴스 (싱글톤 패턴)
_mysql_client_instances: Dict[str, MySQLClient] = {}
_client_lock = threading.Lock()


def get_mysql_client(db_config_key: str = "mysql") -> MySQLClient:
    """MySQL 클라이언트 인스턴스 반환 (싱글톤)"""
    global _mysql_client_instances
    
    if db_config_key not in _mysql_client_instances:
        with _client_lock:
            if db_config_key not in _mysql_client_instances:
                custom_config = None
                
                if db_config_key == "mysql":
                    # 'mysql' (기본값 또는 명시적 호출)인 경우, custom_config를 None으로 전달
                    # MySQLClient가 기존 환경 변수 (DATABASE_HOST 등)를 사용하도록 함
                    custom_config = None
                elif db_config_key == "mysql2":
                    # 'mysql2'인 경우, env_local.py에서 해당 설정을 가져옴
                    full_config = get_config()
                    custom_config = full_config.get(db_config_key)
                    if not custom_config:
                        raise ValueError(f"환경 설정에 '{db_config_key}' 데이터베이스 설정이 없습니다.")
                else:
                    # 지원하지 않는 db_config_key인 경우 오류 발생
                    raise ValueError(f"지원하지 않는 데이터베이스 설정 키: {db_config_key}. 'mysql' 또는 'mysql2'를 사용하세요.")
                
                _mysql_client_instances[db_config_key] = MySQLClient(custom_config=custom_config)
    
    return _mysql_client_instances[db_config_key]


def cleanup_mysql_client():
    """전역 클라이언트 정리"""
    global _mysql_client_instances
    
    with _client_lock:
        for db_config_key, client_instance in list(_mysql_client_instances.items()):
            if client_instance:
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(client_instance.close())
                except RuntimeError:
                    # 이벤트 루프가 없는 경우 동기적으로 정리
                    if client_instance.pool:
                        client_instance.pool.close_all()
                del _mysql_client_instances[db_config_key]
        logger.info("모든 MySQL 클라이언트 정리 완료")


# 프로그램 종료 시 정리
atexit.register(cleanup_mysql_client)