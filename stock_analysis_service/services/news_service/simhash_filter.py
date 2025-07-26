"""
Enhanced SimHash Duplicate Filter for News Service
========================================================
SkillStack의 고도화된 SimHashFilter를 news_service에 통합
- SQLite 기반 영구 저장
- 해밍 거리 기반 중복 검사  
- TTL 기반 자동 정리
- 상세한 중복 로그 생성
"""

from __future__ import annotations
import sqlite3
import os
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from simhash import Simhash
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

# 설정값 (환경변수에서 가져오기)
def get_config_value(key: str, default):
    from config.env_local import get_env_var, get_int_env_var
    if isinstance(default, int):
        return get_int_env_var(key, default)
    else:
        return get_env_var(key, default)

HAMMING_THRESHOLD = 3  # 해밍 거리 임계값
TTL_HOURS = 48  # 보존 시간 (시간)

def hamming_distance(a: int, b: int) -> int:
    """해밍 거리 계산"""
    return bin(a ^ b).count('1')

def _to_signed64(x: int) -> int:
    """SQLite 호환성을 위한 64비트 부호 변환"""
    return x - (1 << 64) if x >= 1 << 63 else x

@dataclass
class MatchInfo:
    """중복 매칭 정보"""
    matched_id: int
    distance: int
    matched_title: str
    matched_url: str
    matched_time: str

class EnhancedSimHashFilter:
    """향상된 SimHash 중복 검사 필터"""
    
    # 4개의 16비트 밴드 마스크
    _RAW_MASKS = [0xFFFF << (16 * i) for i in range(4)]
    _MASKS = [_to_signed64(m) for m in _RAW_MASKS]
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        hamming_threshold: int = HAMMING_THRESHOLD,
        ttl_hours: int = TTL_HOURS,
        log_path: Optional[str] = None
    ):
        """
        SimHash 필터 초기화
        
        Args:
            db_path: SQLite DB 파일 경로
            hamming_threshold: 해밍 거리 임계값
            ttl_hours: 데이터 보존 시간 (시간)
            log_path: 중복 로그 파일 경로
        """
        # 기본 경로 설정
        if db_path is None:
            # news_service 디렉토리에 DB 생성
            service_dir = Path(__file__).parent
            db_path = str(service_dir / "simhash_news.db")
        
        if log_path is None:
            # logs 디렉토리에 로그 생성
            logs_dir = Path(__file__).parent.parent.parent / "logs"
            logs_dir.mkdir(exist_ok=True)
            log_path = str(logs_dir / "simhash_duplicates.csv")
        
        self.db_path = Path(db_path)
        self.hamming_threshold = hamming_threshold
        self.ttl_sec = ttl_hours * 3600
        self.log_path = Path(log_path)
        
        # DB 연결 및 스키마 생성
        self.db = sqlite3.connect(str(self.db_path))
        self._ensure_schema()
        
        logger.info(f"SimHash 필터 초기화: DB={self.db_path}, 임계값={hamming_threshold}, TTL={ttl_hours}h")
    
    def _ensure_schema(self) -> None:
        """데이터베이스 스키마 생성"""
        try:
            logger.info("SimHash 데이터베이스 스키마 생성 시작")
            
            # 1. 테이블 생성
            table_sql = """
                CREATE TABLE IF NOT EXISTS simhash_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    hash64 TEXT NOT NULL,
                    title_snippet TEXT NOT NULL,
                    url TEXT,
                    created_timestamp INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """
            
            logger.debug("SimHash 테이블 생성 중...")
            self.db.execute(table_sql)
            logger.debug("SimHash 테이블 생성 완료")
            
            # 2. 인덱스 생성
            indices = [
                ("idx_simhash_stock", "stock_code"),
                ("idx_simhash_timestamp", "created_timestamp"),
                ("idx_simhash_combined", "stock_code, created_timestamp")
            ]
            
            for idx_name, idx_columns in indices:
                try:
                    idx_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON simhash_cache({idx_columns});"
                    logger.debug(f"인덱스 생성 중: {idx_name}")
                    self.db.execute(idx_sql)
                    logger.debug(f"인덱스 생성 완료: {idx_name}")
                except Exception as idx_error:
                    logger.error(f"인덱스 생성 실패 [{idx_name}]: {type(idx_error).__name__} - {idx_error}")
                    # 인덱스 생성 실패는 치명적이지 않으므로 계속 진행
            
            self.db.commit()
            logger.info("SimHash 데이터베이스 스키마 생성 완료")
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"SimHash 스키마 생성 실패 [{error_type}]: {e}")
            logger.error(f"에러 상세: DB 경로={self.db_path}, 에러 타입={error_type}")
            
            # 스키마 생성 실패 시 추가 정보
            if hasattr(e, 'args') and e.args:
                logger.error(f"에러 메시지: {e.args[0]}")
            
            raise RuntimeError(f"SimHash 데이터베이스 초기화 실패: {error_type} - {e}")
    
    def check_and_insert(
        self,
        stock_code: str,
        title: str,
        content: str = "",
        url: str = ""
    ) -> Tuple[bool, Optional[MatchInfo]]:
        """
        중복 검사 및 새 항목 삽입
        
        Args:
            stock_code: 종목 코드
            title: 뉴스 제목
            content: 뉴스 본문
            url: 뉴스 URL
            
        Returns:
            (is_duplicate, match_info)
        """
        try:
            # SimHash 생성
            text = f"{title} {content}".strip()
            if not text:
                logger.warning("빈 텍스트로 SimHash 생성 불가")
                return False, None
            
            # Simhash 계산
            simhash_obj = Simhash(text.split(), f=64)
            hash_value = int(simhash_obj.value) if simhash_obj.value is not None else 0
            
            # 중복 검사
            match_info = self._find_match(stock_code, hash_value)
            
            if match_info:
                # 중복 발견
                self._log_duplicate(stock_code, title, url, match_info)
                logger.info(f"SimHash 중복 감지: '{title[:50]}...' (거리: {match_info.distance})")
                return True, match_info
            
            # 새 항목 삽입
            self._insert(stock_code, hash_value, title, url)
            logger.debug(f"SimHash 새 항목 삽입: '{title[:50]}...'")
            return False, None
            
        except Exception as e:
            logger.error(f"SimHash 검사 실패: {e}")
            return False, None
    
    def _find_match(self, stock_code: str, hash_value: int) -> Optional[MatchInfo]:
        """해밍 거리 기반 매칭 검색"""
        try:
            cursor = self.db.cursor()
            
            # 4개 밴드에서 검색
            for mask_signed, mask_raw in zip(self._MASKS, self._RAW_MASKS):
                band_signed = _to_signed64(hash_value & mask_raw)
                
                cursor.execute("""
                    SELECT id, hash64, created_timestamp, title_snippet, url 
                    FROM simhash_cache 
                    WHERE stock_code = ? AND (CAST(hash64 AS INTEGER) & ?) = ?
                """, (stock_code, mask_signed, band_signed))
                
                for row in cursor.fetchall():
                    cache_id, old_hash_str, timestamp, title_snippet, old_url = row
                    
                    # 해밍 거리 계산
                    distance = hamming_distance(hash_value, int(old_hash_str))
                    
                    if distance <= self.hamming_threshold:
                        return MatchInfo(
                            matched_id=cache_id,
                            distance=distance,
                            matched_title=title_snippet,
                            matched_url=old_url or "",
                            matched_time=datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"SimHash 매칭 검색 실패: {e}")
            return None
    
    def _insert(self, stock_code: str, hash_value: int, title: str, url: str) -> None:
        """새 항목을 캐시에 삽입"""
        try:
            timestamp = int(datetime.now().timestamp())
            title_snippet = title[:100]  # 제목 스니펫
            
            self.db.execute("""
                INSERT INTO simhash_cache (stock_code, hash64, title_snippet, url, created_timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (stock_code, str(hash_value), title_snippet, url, timestamp))
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"SimHash 항목 삽입 실패: {e}")
    
    def _log_duplicate(self, stock_code: str, new_title: str, new_url: str, match_info: MatchInfo) -> None:
        """중복 항목을 CSV 로그에 기록"""
        try:
            # CSV 헤더 확인 및 생성
            if not self.log_path.exists():
                with open(self.log_path, 'w', encoding='utf-8') as f:
                    f.write("timestamp,stock_code,new_title,matched_id,distance,matched_title,matched_url,new_url\n")
            
            # 중복 로그 기록
            with open(self.log_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                new_title_clean = new_title[:60].replace(',', ' ').replace('\n', ' ')
                matched_title_clean = match_info.matched_title.replace(',', ' ').replace('\n', ' ')
                
                f.write(f"{timestamp},{stock_code},{new_title_clean},{match_info.matched_id},"
                       f"{match_info.distance},{matched_title_clean},{match_info.matched_url},{new_url}\n")
                
        except Exception as e:
            logger.error(f"SimHash 중복 로그 기록 실패: {e}")
    
    def vacuum(self) -> int:
        """오래된 항목 정리 (TTL 기반)"""
        try:
            cutoff_timestamp = int(datetime.now().timestamp()) - self.ttl_sec
            
            cursor = self.db.cursor()
            cursor.execute("SELECT COUNT(*) FROM simhash_cache WHERE created_timestamp < ?", (cutoff_timestamp,))
            count_before = cursor.fetchone()[0]
            
            self.db.execute("DELETE FROM simhash_cache WHERE created_timestamp < ?", (cutoff_timestamp,))
            self.db.commit()
            
            deleted_count = count_before
            if deleted_count > 0:
                logger.info(f"SimHash 캐시 정리: {deleted_count}개 항목 삭제 (TTL: {self.ttl_sec}초)")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"SimHash 캐시 정리 실패: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """캐시 통계 정보 반환"""
        try:
            cursor = self.db.cursor()
            
            # 전체 항목 수
            cursor.execute("SELECT COUNT(*) FROM simhash_cache")
            total_count = cursor.fetchone()[0]
            
            # 종목별 항목 수
            cursor.execute("SELECT stock_code, COUNT(*) FROM simhash_cache GROUP BY stock_code")
            by_stock = dict(cursor.fetchall())
            
            # 최근 24시간 항목 수
            cutoff_24h = int(datetime.now().timestamp()) - 86400
            cursor.execute("SELECT COUNT(*) FROM simhash_cache WHERE created_timestamp > ?", (cutoff_24h,))
            recent_count = cursor.fetchone()[0]
            
            return {
                "total_items": total_count,
                "recent_24h": recent_count,
                "by_stock": by_stock,
                "db_path": str(self.db_path),
                "log_path": str(self.log_path),
                "hamming_threshold": self.hamming_threshold,
                "ttl_hours": self.ttl_sec // 3600
            }
            
        except Exception as e:
            logger.error(f"SimHash 통계 조회 실패: {e}")
            return {}
    
    def close(self):
        """데이터베이스 연결 종료"""
        try:
            if hasattr(self, 'db'):
                self.db.close()
                logger.debug("SimHash 데이터베이스 연결 종료")
        except Exception as e:
            logger.error(f"SimHash DB 연결 종료 실패: {e}")
    
    def __del__(self):
        """소멸자"""
        self.close() 