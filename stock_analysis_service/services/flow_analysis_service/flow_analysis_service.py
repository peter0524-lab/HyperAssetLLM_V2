"""
수급 분석 서비스 (Flow Analysis Service)
- 실시간 프로그램 매매 데이터 수집 및 분석
- 일별 기관/외국인/개인 수급 데이터 수집 및 분석
- 복합 트리거 패턴 감지 및 알림
- 과거 유사 사례 검색 (SQL Only, RAG 없음)
"""
import os
import asyncio
import json
import logging
import os
import numpy as np
import pymysql.cursors
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import sys
import threading
import time

# 전역 로거 설정
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.llm.llm_manager import llm_manager
from shared.apis.kis_api import kis_client
from shared.apis.pykrx_api import pykrx_client
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config
from shared.user_config.user_config_manager import user_config_manager
from shared.service_config.user_config_loader import get_config_loader

# FastAPI 추가
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
import uvicorn

app = FastAPI(title="Flow Analysis Service", version="1.0.0")

class FlowAnalysisService:
    """수급 분석 서비스 클래스"""

    def __init__(self):
        # 개발자 기본 설정 로드
        self.config = get_config()
        
        # 사용자 설정 관리자 초기화
        self.user_config_manager = user_config_manager
        self.current_user_id = os.environ.get('HYPERASSET_USER_ID', "1")  # 🔥 환경변수에서 사용자 ID 읽기
        self.stocks_config = {}  # 사용자별 종목 설정 (MySQL에서 덮어쓰기)
        
        # 사용자별 개인화 설정 로더
        self.user_config_loader = None  # 비동기로 초기화됨
        self.personalized_configs = {}  # 사용자별 개인화 설정 캐시
        
        self.mysql_client = get_mysql_client()
        self.llm_manager = llm_manager
        self.telegram_bot = TelegramBotClient()

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # 트리거 설정값
        self.institutional_trigger_days = 5  # 최근 5일
        self.institutional_trigger_threshold = 3  # 5일 중 3일 이상
        self.program_trigger_lookback = 30  # 30일 평균 기준
        self.program_trigger_multiplier = 2.5  # 평균 대비 2.5배
        self.program_trigger_percentile = 90  # 90분위수

        # 실시간 데이터 캐시
        self.program_cache = {}  # {ticker: [volumes]}
        self.cache_lock = threading.Lock()

        # 서비스 상태
        self.is_running = False
        self.ws_thread = None
        
        # 사용자별 설정 로드 (MySQL에서 stock_code만 덮어쓰기)
        asyncio.create_task(self._load_user_settings())

    async def _load_user_settings(self):
        """사용자별 설정 로드 - 직접 DB 쿼리 방식"""
        try:
            # 🆕 직접 DB에서 사용자별 종목 조회 (사용자 제안 방식)
            query = """
            SELECT stock_code, stock_name 
            FROM user_stocks 
            WHERE user_id = %s AND enabled = 1
            """
            
            stocks_result = await self.mysql_client.execute_query_async(
                query, (self.current_user_id,), fetch=True
            )
            
            # 사용자 종목 설정으로 덮어쓰기
            self.stocks_config = {}
            if stocks_result:
                for row in stocks_result:
                    stock_code = row['stock_code']
                    stock_name = row['stock_name']
                    self.stocks_config[stock_code] = {
                        "name": stock_name,
                        "enabled": True
                    }
                self.logger.info(f"📊 DB에서 로드된 사용자 종목: {list(self.stocks_config.keys())}")
            else:
                self.logger.warning(f"⚠️ 사용자 {self.current_user_id}의 종목이 DB에 없습니다")
            
            self.logger.info(f"✅ 사용자 종목 설정 로드 완료: {len(self.stocks_config)}개 종목")
            
        except Exception as e:
            self.logger.error(f"❌ 사용자 설정 로드 실패 (기본값 유지): {e}")
            # 실패시 빈 종목 설정 (기본 종목 제거)
            self.stocks_config = {}
    
    async def set_user_id(self, user_id):
        """사용자 ID 설정 및 설정 재로드"""
        try:
            self.current_user_id = user_id
            self.logger.info(f"🔄 사용자 ID 변경: {user_id}")
            
            # ✅ 모든 사용자에 대해 DB에서 직접 종목 조회
            await self._load_user_settings()
                
            self.logger.info(f"✅ 사용자 ID 설정 및 설정 재로드 완료: {user_id}")
            self.logger.info(f"📋 최종 stocks_config: {self.stocks_config}")
        except Exception as e:
            self.logger.error(f"❌ 사용자 ID 설정 실패: {e}")
            raise

    async def initialize_database(self, force_init=False):
        """데이터베이스 초기화 및 테이블 생성 (필요한 경우만)"""
        try:
            # force_init이 False인 경우, 테이블 존재 여부 확인
            if not force_init:
                with self.mysql_client.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SHOW TABLES LIKE 'pattern_signals'")
                    if cursor.fetchone():
                        self.logger.info("수급 분석 테이블이 이미 존재합니다. 초기화를 건너뜁니다.")
                        return
            
            # 스키마 파일 실행
            schema_file = project_root / "database" / "flow_analysis_schema.sql"
            if schema_file.exists():
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                # SQL 문 분리 및 실행
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                with self.mysql_client.get_connection() as conn:
                    cursor = conn.cursor()
                    for statement in statements:
                        if statement and not statement.startswith('--'):
                            cursor.execute(statement)
                    conn.commit()
                
                self.logger.info("수급 분석 데이터베이스 초기화 완료")
            else:
                self.logger.warning("스키마 파일이 없습니다")

        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    # === 일별 수급 데이터 처리 ===
    
    async def collect_eod_flow_data(self, stock_code: str, target_date: str = None):
        """일별 수급 데이터 수집 및 저장"""
        try:
            if not pykrx_client:
                self.logger.error("pykrx 클라이언트가 초기화되지 않았습니다")
                return False

            # EOD 수급 데이터 조회
            flow_data = pykrx_client.get_eod_flow_data(stock_code, target_date)
            
            if flow_data.get("status") != "success":
                self.logger.warning(f"EOD 데이터 조회 실패: {flow_data.get('message')}")
                return False

            data = flow_data["data"]
            trade_date = flow_data["date"]

            # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
            if len(trade_date) == 8:
                formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
            else:
                formatted_date = trade_date

            # 데이터베이스에 저장
            query = """
                INSERT INTO eod_flows (
                    trade_date, ticker, inst_net, foreign_net, individ_net,
                    total_value, close_price, volume
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    inst_net = VALUES(inst_net),
                    foreign_net = VALUES(foreign_net),
                    individ_net = VALUES(individ_net),
                    total_value = VALUES(total_value),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume),
                    updated_at = CURRENT_TIMESTAMP
            """

            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    formatted_date, stock_code,
                    data["inst_net"], data["foreign_net"], data["individual_net"],
                    data["total_value"], data["close_price"], data["volume"]
                ))
                conn.commit()

            self.logger.info(f"EOD 수급 데이터 저장 완료: {stock_code} {formatted_date}")
            return True

        except Exception as e:
            self.logger.error(f"EOD 수급 데이터 수집 실패: {e}")
            return False

    async def check_institutional_buying_trigger(self, stock_code: str) -> Dict:
        """기관 강매수 트리거 체크"""
        try:
            # 최근 5일 기관 순매수 데이터 조회
            query = """
                SELECT trade_date, inst_net
                FROM eod_flows
                WHERE ticker = %s
                ORDER BY trade_date DESC
                LIMIT %s
            """

            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (stock_code, self.institutional_trigger_days))
                results = cursor.fetchall()

            if len(results) < self.institutional_trigger_days:
                return {"triggered": False, "reason": "데이터 부족"}

            # 순매수일 카운트
            positive_days = sum(1 for row in results if row["inst_net"] > 0)
            latest_positive = results[0]["inst_net"] > 0 if results else False

            # 트리거 조건: 5일 중 3일 이상 순매수 & 최근일도 순매수
            triggered = (positive_days >= self.institutional_trigger_threshold and latest_positive)

            return {
                "triggered": triggered,
                "positive_days": positive_days,
                "total_days": len(results),
                "latest_positive": latest_positive,
                "latest_amount": results[0]["inst_net"] if results else 0,
                "recent_data": results
            }

        except Exception as e:
            self.logger.error(f"기관 매수 트리거 체크 실패: {e}")
            return {"triggered": False, "reason": f"오류: {e}"}

    # === 실시간 프로그램 매매 처리 ===

    def start_program_flow_monitoring(self, stock_codes: List[str]):
        """실시간 프로그램 매매 모니터링 시작"""
        try:
            self.is_running = True
            
            # 각 종목별 WebSocket 구독
            for stock_code in stock_codes:
                kis_client.subscribe_program_trade_data(
                    stock_code, 
                    lambda data, ticker=stock_code: self.on_program_trade_data(ticker, data)
                )
                
                # 캐시 초기화
                self.program_cache[stock_code] = []

            self.logger.info(f"프로그램 매매 모니터링 시작: {stock_codes}")

        except Exception as e:
            self.logger.error(f"프로그램 매매 모니터링 시작 실패: {e}")

    def on_program_trade_data(self, stock_code: str, data: Dict):
        """프로그램 매매 데이터 수신 콜백"""
        try:
            # 데이터 파싱 (KIS WebSocket 형식에 따라 조정 필요)
            net_volume = data.get("net_volume", 0)
            net_value = data.get("net_value", 0)
            price = data.get("price", 0)
            total_volume = data.get("total_volume", 0)
            side = "BUY" if net_volume > 0 else "SELL"

            # 데이터베이스 저장
            asyncio.create_task(self.save_program_flow_data(
                stock_code, net_volume, net_value, side, price, total_volume
            ))

            # 캐시 업데이트
            with self.cache_lock:
                if stock_code not in self.program_cache:
                    self.program_cache[stock_code] = []
                
                self.program_cache[stock_code].append(abs(net_volume))
                
                # 캐시 크기 제한 (최근 100개만 유지)
                if len(self.program_cache[stock_code]) > 100:
                    self.program_cache[stock_code] = self.program_cache[stock_code][-100:]

            # 실시간 트리거 체크
            asyncio.create_task(self.check_program_buying_trigger(stock_code))

        except Exception as e:
            self.logger.error(f"프로그램 매매 데이터 처리 실패: {e}")

    async def save_program_flow_data(self, stock_code: str, net_volume: int, 
                                   net_value: int, side: str, price: float, total_volume: int):
        """프로그램 매매 데이터 저장"""
        try:
            query = """
                INSERT INTO program_flows (
                    ts, ticker, net_volume, net_value, side, price, total_volume
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    datetime.now(), stock_code, net_volume, net_value, 
                    side, price, total_volume
                ))
                conn.commit()

        except Exception as e:
            self.logger.error(f"프로그램 매매 데이터 저장 실패: {e}")

    async def check_program_buying_trigger(self, stock_code: str) -> Dict:
        """실시간 프로그램 매수 트리거 체크"""
        try:
            # 캐시에서 최근 데이터 조회
            with self.cache_lock:
                volumes = self.program_cache.get(stock_code, [])

            if len(volumes) < self.program_trigger_lookback:
                return {"triggered": False, "reason": "데이터 부족"}

            # 최근 30개 데이터로 분석
            recent_volumes = volumes[-self.program_trigger_lookback:]
            current_volume = volumes[-1] if volumes else 0

            # 평균과 분위수 계산
            avg_volume = np.mean(recent_volumes)
            percentile_90 = np.percentile(recent_volumes, self.program_trigger_percentile)

            # 트리거 조건: 현재 거래량이 평균의 2.5배 이상 AND 90분위수 초과
            triggered = (current_volume > avg_volume * self.program_trigger_multiplier and 
                        current_volume > percentile_90)

            if triggered:
                # 트리거 발생 시 처리
                await self.handle_program_trigger(stock_code, {
                    "current_volume": current_volume,
                    "avg_volume": avg_volume,
                    "ratio": current_volume / avg_volume if avg_volume > 0 else 0,
                    "percentile_90": percentile_90
                })

            return {
                "triggered": triggered,
                "current_volume": current_volume,
                "avg_volume": avg_volume,
                "ratio": current_volume / avg_volume if avg_volume > 0 else 0,
                "percentile_90": percentile_90
            }

        except Exception as e:
            self.logger.error(f"프로그램 매수 트리거 체크 실패: {e}")
            return {"triggered": False, "reason": f"오류: {e}"}

    # === 패턴 신호 관리 ===

    async def handle_program_trigger(self, stock_code: str, trigger_data: Dict):
        """실시간 프로그램 트리거 처리"""
        try:
            # 당일 기준으로 pattern_signals 테이블에 저장/업데이트
            query = """
                INSERT INTO pattern_signals (
                    ref_time, ticker, rt_prog_strong, prog_volume, prog_ratio, trigger_data
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    rt_prog_strong = VALUES(rt_prog_strong),
                    prog_volume = VALUES(prog_volume),
                    prog_ratio = VALUES(prog_ratio),
                    trigger_data = JSON_MERGE(COALESCE(trigger_data, '{}'), VALUES(trigger_data)),
                    updated_at = CURRENT_TIMESTAMP
            """

            trigger_json = json.dumps(trigger_data)
            current_time = datetime.now()
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    current_time, stock_code, True,
                    int(trigger_data["current_volume"]),
                    trigger_data["ratio"],
                    trigger_json
                ))
                conn.commit()

            self.logger.info(f"실시간 프로그램 트리거 저장: {stock_code}")

            # 프로그램 매매 알림 전송
            await self.send_program_alert(stock_code)

        except Exception as e:
            self.logger.error(f"프로그램 트리거 처리 실패: {e}")

    async def handle_institutional_trigger(self, stock_code: str, trigger_data: Dict):
        """일별 기관 트리거 처리"""
        try:
            # 당일 기준으로 pattern_signals 테이블에 저장/업데이트
            query = """
                INSERT INTO pattern_signals (
                    ref_time, ticker, daily_inst_strong, inst_buy_days, trigger_data
                ) VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    daily_inst_strong = VALUES(daily_inst_strong),
                    inst_buy_days = VALUES(inst_buy_days),
                    trigger_data = JSON_MERGE(COALESCE(trigger_data, '{}'), VALUES(trigger_data)),
                    updated_at = CURRENT_TIMESTAMP
            """

            trigger_json = json.dumps(trigger_data)
            current_time = datetime.now()
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    current_time, stock_code, True,
                    trigger_data["positive_days"],
                    trigger_json
                ))
                conn.commit()

            self.logger.info(f"일별 기관 트리거 저장: {stock_code}")

            # 기관 매수 알림 전송
            await self.send_institutional_alert(stock_code)

        except Exception as e:
            self.logger.error(f"기관 트리거 처리 실패: {e}")


    # === 과거 유사 사례 검색 (SQL Only) ===

    async def search_similar_cases(self, stock_code: str) -> Optional[Dict]:
        """과거 유사 사례 검색 (가장 최근 이전 신호)"""
        try:
            query = """
                WITH latest AS (
                    SELECT DATE(ref_time) as d
                    FROM pattern_signals
                    WHERE ticker = %s AND (daily_inst_strong = TRUE OR rt_prog_strong = TRUE)
                    ORDER BY ref_time DESC
                    LIMIT 1
                )
                SELECT ps.ref_time, ps.trigger_data,
                       ef.close_price, ef.trade_date
                FROM pattern_signals ps
                LEFT JOIN eod_flows ef ON ps.ticker = ef.ticker 
                    AND DATE(ps.ref_time) = ef.trade_date
                WHERE ps.ticker = %s 
                    AND (ps.daily_inst_strong = TRUE OR ps.rt_prog_strong = TRUE)
                    AND DATE(ps.ref_time) < (SELECT d FROM latest)
                ORDER BY ps.ref_time DESC
                LIMIT 1
            """

            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (stock_code, stock_code))
                result = cursor.fetchone()

            if result:
                # 5일 후 수익률 계산 (간단 구현)
                future_date = result["trade_date"] + timedelta(days=5)
                future_query = """
                    SELECT close_price FROM eod_flows
                    WHERE ticker = %s AND trade_date >= %s
                    ORDER BY trade_date ASC LIMIT 1
                """
                
                cursor.execute(future_query, (stock_code, future_date))
                future_result = cursor.fetchone()
                
                ret5d = 0.0
                if future_result and result["close_price"]:
                    ret5d = (future_result["close_price"] - result["close_price"]) / result["close_price"]

                return {
                    "ref_time": result["ref_time"],
                    "trigger_data": result["trigger_data"],
                    "close_price": result["close_price"],
                    "ret5d": ret5d
                }

            return None
        
        except Exception as e:
            self.logger.error(f"유사 사례 검색 실패: {e}")
            return None

    # === 알림 시스템 ===

    # 복합 신호 알림 전송 함수 제거 (각각 독립적으로 알림 전송)

    async def send_institutional_alert(self, stock_code: str):
        """기관 매수 알림 전송 (3일 이상 순매수)"""
        try:
            # 최근 5일간 기관 매수 일수 확인
            query = """
                SELECT COUNT(*) as inst_buy_days,
                       AVG(inst_net) as avg_inst_net,
                       MAX(close_price) as max_price,
                       MIN(close_price) as min_price
                FROM eod_flows 
                WHERE ticker = %s 
                AND trade_date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
                AND inst_net > 0
            """

            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (stock_code,))
                result = cursor.fetchone()

            if not result or result["inst_buy_days"] < 3:
                return  # 3일 미만이면 알림 발송 안함

            # 메시지 생성
            message = self.build_institutional_alert_message(stock_code, result)

            # 텔레그램 전송
            await self.telegram_bot.send_message(message)
            
            # 최근 알람 메시지 저장
            await save_latest_signal(message)

            # 알림 로그 저장
            await self.save_alert_log(stock_code, "INSTITUTIONAL", message)

            self.logger.info(f"기관 매수 알림 전송 완료: {stock_code}")

        except Exception as e:
            self.logger.error(f"기관 매수 알림 전송 실패: {e}")

    async def send_program_alert(self, stock_code: str):
        """프로그램 매매 알림 전송 (실시간 프로그램 급증)"""
        try:
            # 최근 프로그램 매매 데이터 확인
            query = """
                SELECT pf.*, 
                       AVG(ABS(pf2.net_volume)) as avg_prog_volume
                FROM program_flows pf
                LEFT JOIN (
                    SELECT net_volume 
                    FROM program_flows 
                    WHERE ticker = %s 
                    AND ts >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ) pf2 ON 1=1
                WHERE pf.ticker = %s 
                AND pf.ts >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                ORDER BY pf.ts DESC
                LIMIT 1
            """

            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (stock_code, stock_code))
                result = cursor.fetchone()

            if not result:
                return

            # 프로그램 매매 비율 계산
            recent_volume = abs(result.get("net_volume", 0))
            avg_volume = result.get("avg_prog_volume", 0)
            
            if avg_volume == 0:
                return
                
            prog_ratio = recent_volume / avg_volume

            # 2배 이상 급증했을 때만 알림
            if prog_ratio < 2.0:
                return

            # 메시지 생성
            message = self.build_program_alert_message(stock_code, result, prog_ratio)

            # 텔레그램 전송
            await self.telegram_bot.send_message(message)
            
            # 최근 알람 메시지 저장
            await save_latest_signal(message)

            # 알림 로그 저장
            await self.save_alert_log(stock_code, "PROGRAM", message)

            self.logger.info(f"프로그램 매매 알림 전송 완료: {stock_code}")

        except Exception as e:
            self.logger.error(f"프로그램 매매 알림 전송 실패: {e}")

    # 복합 신호 메시지 구성 함수 제거 (각각 독립적으로 메시지 구성)

    def build_institutional_alert_message(self, stock_code: str, result: Dict) -> str:
        """기관 매수 알림 메시지 구성"""
        try:
            inst_buy_days = result.get("inst_buy_days", 0)
            avg_inst_net = result.get("avg_inst_net", 0)
            max_price = result.get("max_price", 0)
            min_price = result.get("min_price", 0)
            
            price_change = ((max_price - min_price) / min_price * 100) if min_price > 0 else 0

            message_lines = [
                f"🏢 <b>{stock_code} 기관 순매수 신호</b>",
                f"• 최근 5일 중 {inst_buy_days}일 기관 순매수",
                f"• 평균 기관 순매수: {avg_inst_net:,.0f}주",
                f"• 기간 중 가격 변동: {price_change:+.2f}%"
            ]

            return "\n".join(message_lines)

        except Exception as e:
            self.logger.error(f"기관 매수 메시지 구성 실패: {e}")
            return f"🏢 {stock_code} 기관 순매수 신호 발생"

    def build_program_alert_message(self, stock_code: str, result: Dict, prog_ratio: float) -> str:
        """프로그램 매매 알림 메시지 구성"""
        try:
            net_volume = result.get("net_volume", 0)
            net_value = result.get("net_value", 0)
            side = "매수" if net_volume > 0 else "매도"
            ts = result.get("ts", datetime.now())

            message_lines = [
                f"⚡ <b>{stock_code} 프로그램 {side} 급증</b>",
                f"• {ts.strftime('%H:%M:%S')} 기준",
                f"• 순매수량: {abs(net_volume):,.0f}주",
                f"• 순매수금액: {abs(net_value):,.0f}원",
                f"• 30일 평균 대비 {prog_ratio:.1f}배 급증"
            ]

            return "\n".join(message_lines)

        except Exception as e:
            self.logger.error(f"프로그램 매매 메시지 구성 실패: {e}")
            return f"⚡ {stock_code} 프로그램 매매 급증"

    def build_alert_message(self, signal_data: Dict, similar_case: Dict = None) -> str:
        """기존 알림 메시지 구성 (하위 호환성)"""
        return f"🏹 {signal_data.get('ticker', 'Unknown')} 신호 발생"

    async def save_alert_log(self, stock_code: str, alert_type: str, message: str):
        """알림 로그 저장"""
        try:
            query = """
                INSERT INTO notification_logs (
                    service_name, notification_type, stock_code, message
                ) VALUES (%s, %s, %s, %s)
            """

            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, ("flow_analysis", alert_type, stock_code, message))
                conn.commit()

        except Exception as e:
            self.logger.error(f"알림 로그 저장 실패: {e}")

    # === 스케줄링 및 실행 ===

    async def daily_eod_job(self, stock_codes: List[str]):
        """일별 EOD 작업 (16:35 실행)"""
        try:
            self.logger.info("일별 EOD 작업 시작")

            for stock_code in stock_codes:
                # 1. EOD 수급 데이터 수집
                await self.collect_eod_flow_data(stock_code)
                
                # 2. 기관 매수 트리거 체크
                trigger_result = await self.check_institutional_buying_trigger(stock_code)
                
                if trigger_result.get("triggered"):
                    await self.handle_institutional_trigger(stock_code, trigger_result)

            self.logger.info("일별 EOD 작업 완료")

        except Exception as e:
            self.logger.error(f"일별 EOD 작업 실패: {e}")

    async def run_service(self):
        """수급 분석 서비스 실행"""
        try:
            self.logger.info("수급 분석 서비스 시작")

            # 데이터베이스 초기화 (필요한 경우만)
            await self.initialize_database(force_init=False)

            # 종목 정보 로드
            with open(project_root / "config" / "stocks.json", "r", encoding="utf-8") as f:
                stocks_config = json.load(f)

            stock_codes = [stock["code"] for stock in stocks_config.get("stocks", [])]

            # 실시간 모니터링 시작
            self.start_program_flow_monitoring(stock_codes)

            # 메인 루프
            while True:
                try:
                    current_time = datetime.now().time()
                    
                    # 16:35 일별 EOD 작업 실행
                    if current_time.hour == 16 and current_time.minute == 35:
                        await self.daily_eod_job(stock_codes)
                        await asyncio.sleep(58)  # 1분 대기
                    
                    # 장중 시간 체크 (실시간 모니터링은 백그라운드에서 계속 실행)
                    market_open = datetime.strptime("09:00", "%H:%M").time()
                    market_close = datetime.strptime("15:30", "%H:%M").time()
                    
                    if market_open <= current_time <= market_close:
                        # 장중: 1분 대기
                        await asyncio.sleep(60)
                    else:
                        # 장외: 10분 대기
                        await asyncio.sleep(600)

                except KeyboardInterrupt:
                    self.logger.info("서비스 중단 요청")
                    break
                except Exception as e:
                    self.logger.error(f"서비스 실행 오류: {e}")
                    await asyncio.sleep(60)

        except Exception as e:
            self.logger.error(f"수급 분석 서비스 실행 실패: {e}")
            raise

    async def get_database_connection(self):
        """데이터베이스 연결 반환"""
        try:
            # MySQL 클라이언트의 연결 풀에서 연결 가져오기
            return self.mysql_client.pool.get_connection(timeout=20)
        except Exception as e:
            self.logger.error(f"❌ 데이터베이스 연결 실패: {e}")
            return None

    async def analyze_flow_data_by_period(self, stock_codes: List[str] = None) -> Dict:
        """기간별 수급 데이터 분석 (3일, 7일, 2주, 1달)"""
        analysis_id = f"analysis_{int(time.time() * 1000)}"
        start_time = time.time()
        
        self.logger.info(f"[Flow Analysis][{analysis_id}] 수급 분석 시작")
        self.logger.info(f"[Flow Analysis][{analysis_id}] 초기화 단계:")
        
        try:
            # 1. 종목 코드 로드
            if not stock_codes:
                self.logger.info(f"[Flow Analysis][{analysis_id}] 종목 설정 파일 로드 중...")
                try:
                    with open(project_root / "config" / "stocks.json", "r", encoding="utf-8") as f:
                        stocks_config = json.load(f)
                        stock_codes = [stock["code"] for stock in stocks_config.get("stocks", [])]
                    self.logger.info(f"[Flow Analysis][{analysis_id}] 종목 설정 로드 완료: {len(stock_codes)}개")
                except Exception as e:
                    self.logger.warning(f"[Flow Analysis][{analysis_id}] 종목 설정 로드 실패:")
                    self.logger.warning(f"  - 에러: {str(e)}")
                    self.logger.warning(f"  - 기본 종목으로 대체")
                    stock_codes = ["005930", "000660", "006800"]

            if not stock_codes:
                self.logger.error(f"[Flow Analysis][{analysis_id}] 치명적 오류: 분석할 종목이 없음")
                return {"success": False, "error": "분석할 종목이 없습니다.", "analysis_id": analysis_id}

            # 2. 데이터베이스 연결 확인
            self.logger.info(f"[Flow Analysis][{analysis_id}] 데이터베이스 연결 확인...")
            if not self.mysql_client.pool:
                self.logger.error(f"[Flow Analysis][{analysis_id}] 치명적 오류: DB 연결 실패")
                return {"success": False, "error": "데이터베이스 연결 실패", "analysis_id": analysis_id}

            # 3. 분석 실행
            analysis_results = []
            periods = [
                {"name": "3일", "days": 3},
                {"name": "7일", "days": 7},
                {"name": "2주", "days": 14},
                {"name": "1달", "days": 30}
            ]
            
            self.logger.info(f"[Flow Analysis][{analysis_id}] 분석 설정:")
            self.logger.info(f"  - 대상 종목 수: {len(stock_codes)}개")
            self.logger.info(f"  - 분석 기간: {', '.join(p['name'] for p in periods)}")
            
            for idx, stock_code in enumerate(stock_codes, 1):
                stock_start_time = time.time()
                self.logger.info(f"[Flow Analysis][{analysis_id}] 종목 분석 {idx}/{len(stock_codes)}:")
                self.logger.info(f"  - 종목코드: {stock_code}")
                
                try:
                    stock_analysis = {"stock_code": stock_code, "periods": {}}
                    
                    for period in periods:
                        period_start_time = time.time()
                        self.logger.debug(f"[Flow Analysis][{analysis_id}] {stock_code} {period['name']} 분석 중...")
                        
                        # 수급 데이터 조회 쿼리
                        query = """
                        SELECT 
                            AVG(inst_net) as avg_inst_net,
                            AVG(foreign_net) as avg_foreign_net,
                            AVG(individ_net) as avg_individ_net,
                            SUM(inst_net) as total_inst_net,
                            SUM(foreign_net) as total_foreign_net,
                            SUM(individ_net) as total_individ_net,
                            COUNT(*) as data_count,
                            MAX(trade_date) as latest_date,
                            MIN(trade_date) as earliest_date
                        FROM eod_flows 
                        WHERE ticker = %s 
                        AND trade_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                        """
                        
                        result = await self.mysql_client.fetch_one_async(query, (stock_code, period["days"]))
                        period_time = time.time() - period_start_time
                        
                        if result:
                            self.logger.debug(f"[Flow Analysis][{analysis_id}] {stock_code} {period['name']} 데이터:")
                            self.logger.debug(f"  - 데이터 건수: {result['data_count']}개")
                            self.logger.debug(f"  - 조회 시간: {period_time:.2f}초")
                            
                            # 데이터 가공
                            period_data = {
                                "avg_inst_net": int(result["avg_inst_net"]) if result["avg_inst_net"] else 0,
                                "avg_foreign_net": int(result["avg_foreign_net"]) if result["avg_foreign_net"] else 0,
                                "avg_individ_net": int(result["avg_individ_net"]) if result["avg_individ_net"] else 0,
                                "total_inst_net": int(result["total_inst_net"]) if result["total_inst_net"] else 0,
                                "total_foreign_net": int(result["total_foreign_net"]) if result["total_foreign_net"] else 0,
                                "total_individ_net": int(result["total_individ_net"]) if result["total_individ_net"] else 0,
                                "data_count": result["data_count"],
                                "latest_date": result["latest_date"].isoformat() if result["latest_date"] else None,
                                "earliest_date": result["earliest_date"].isoformat() if result["earliest_date"] else None
                            }
                            
                            # 수급 방향 및 강도 분석
                            period_data.update({
                                "inst_direction": "매수" if period_data["avg_inst_net"] > 0 else "매도",
                                "foreign_direction": "매수" if period_data["avg_foreign_net"] > 0 else "매도",
                                "individ_direction": "매수" if period_data["avg_individ_net"] > 0 else "매도",
                                "inst_strength": "강" if abs(period_data["avg_inst_net"]) > 100000 else "약",
                                "foreign_strength": "강" if abs(period_data["avg_foreign_net"]) > 100000 else "약",
                                "individ_strength": "강" if abs(period_data["avg_individ_net"]) > 100000 else "약"
                            })
                            
                            stock_analysis["periods"][period["name"]] = period_data
                            
                            # 주요 변동 로깅
                            if period_data["inst_strength"] == "강" or period_data["foreign_strength"] == "강":
                                self.logger.info(f"[Flow Analysis][{analysis_id}] {stock_code} {period['name']} 주요 변동:")
                                self.logger.info(f"  - 기관: {period_data['inst_direction']}({period_data['inst_strength']}, {period_data['avg_inst_net']:,}주)")
                                self.logger.info(f"  - 외국인: {period_data['foreign_direction']}({period_data['foreign_strength']}, {period_data['avg_foreign_net']:,}주)")
                        else:
                            self.logger.warning(f"[Flow Analysis][{analysis_id}] {stock_code} {period['name']} 데이터 없음")
                            stock_analysis["periods"][period["name"]] = {"error": f"{period['name']} 데이터 없음"}
                    
                    analysis_results.append(stock_analysis)
                    stock_time = time.time() - stock_start_time
                    self.logger.info(f"[Flow Analysis][{analysis_id}] {stock_code} 분석 완료 ({stock_time:.2f}초)")
                    
                except Exception as e:
                    self.logger.error(f"[Flow Analysis][{analysis_id}] {stock_code} 분석 실패:")
                    self.logger.error(f"  - 에러 타입: {type(e).__name__}")
                    self.logger.error(f"  - 에러 메시지: {str(e)}")
                    analysis_results.append({"stock_code": stock_code, "error": str(e)})
                    continue

            # 4. 결과 정리
            analyzed_count = len([r for r in analysis_results if "error" not in r])
            total_time = time.time() - start_time
            
            self.logger.info(f"[Flow Analysis][{analysis_id}] 분석 완료:")
            self.logger.info(f"  - 성공: {analyzed_count}/{len(stock_codes)} 종목")
            self.logger.info(f"  - 총 소요시간: {total_time:.2f}초")
            self.logger.info(f"  - 평균 처리시간: {(total_time/len(stock_codes)):.2f}초/종목")
            
            # 5. 텔레그램 메시지 생성
            telegram_message = self._build_flow_analysis_telegram_message(analysis_results)
            
            return {
                "success": True,
                "data": analysis_results,
                "telegram_message": telegram_message,
                "analysis_id": analysis_id,
                "analysis_time": datetime.now().isoformat(),
                "analyzed_stocks": analyzed_count,
                "execution_time": total_time
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            self.logger.error(f"[Flow Analysis][{analysis_id}] 치명적 오류 발생:")
            self.logger.error(f"  - 에러 타입: {type(e).__name__}")
            self.logger.error(f"  - 에러 메시지: {str(e)}")
            self.logger.error(f"  - 실행 시간: {total_time:.2f}초")
            self.logger.error("  - 스택 트레이스:")
            import traceback
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    self.logger.error(f"    {line}")
            
            return {
                "success": False,
                "error": str(e),
                "analysis_id": analysis_id,
                "execution_time": total_time
            }

    def _build_flow_analysis_telegram_message(self, analysis_results: List[Dict]) -> str:
        """수급 분석 결과를 텔레그램 메시지로 변환"""
        try:
            message = "💰 <b>수급 분석 결과</b>\n\n"
            
            for result in analysis_results:
                if "error" in result:
                    message += f"❌ <b>{result['stock_code']}</b>: {result['error']}\n\n"
                    continue
                
                message += f"📊 <b>{result['stock_code']}</b>\n"
                
                for period_name, period_data in result["periods"].items():
                    if "error" in period_data:
                        message += f"  • <b>{period_name}</b>: {period_data['error']}\n"
                        continue
                    
                    # 방향에 따른 이모지 선택
                    inst_emoji = "🔴" if period_data['inst_direction'] == "매도" else "🟢"
                    foreign_emoji = "🔴" if period_data['foreign_direction'] == "매도" else "🟢"
                    individ_emoji = "🔴" if period_data['individ_direction'] == "매도" else "🟢"
                    
                    message += f"  • <b>{period_name} 평균</b>:\n"
                    message += f"    {inst_emoji} <b>기관</b>: {period_data['inst_direction']} ({period_data['avg_inst_net']:,}주)\n"
                    message += f"    {foreign_emoji} <b>외국인</b>: {period_data['foreign_direction']} ({period_data['avg_foreign_net']:,}주)\n"
                    message += f"    {individ_emoji} <b>개인</b>: {period_data['individ_direction']} ({period_data['avg_individ_net']:,}주)\n"
                
                message += "\n"
            
            message += f"⏰ <b>분석 시간</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            return message
            
        except Exception as e:
            logger.error(f"❌ 텔레그램 메시지 생성 실패: {e}")
            return f"💰 <b>수급 분석 완료</b>\n\n⏰ <b>분석 시간</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# === FastAPI 엔드포인트 ===

# 서비스 인스턴스와 최근 알람 메시지 저장
flow_service_instance = None
latest_signal_message = None  # 최근 알람 메시지 저장

def get_flow_service():
    """수급 분석 서비스 인스턴스 반환 (싱글톤 패턴)"""
    global flow_service_instance
    if flow_service_instance is None:
        flow_service_instance = FlowAnalysisService()
    return flow_service_instance

@app.post("/set-user/{user_id}")
async def set_user_id_endpoint(user_id):
    """사용자 ID 설정 엔드포인트"""
    try:
        flow_service = get_flow_service()
        await flow_service.set_user_id(user_id)
        return {
            "success": True,
            "message": f"사용자 ID 설정 완료: {user_id}",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"❌ 사용자 ID 설정 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 ID 설정에 실패했습니다")

@app.get("/user-config/{user_id}")
async def get_user_config_endpoint(user_id):
    """사용자 설정 조회 엔드포인트"""
    try:
        flow_service = get_flow_service()
        await flow_service.set_user_id(user_id)
        
        # 사용자 설정 조회
        user_config = await flow_service.user_config_manager.get_user_config(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "config": {
                "stocks": user_config.get("stocks", [])
            }
        }
    except Exception as e:
        logger.error(f"❌ 사용자 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 설정 조회에 실패했습니다")

# 독립적 스케줄링을 위한 상태 관리
websocket_running = False
eod_done_today = False
last_eod_date = None

def get_flow_service():
    """자금흐름 서비스 인스턴스 반환"""
    global flow_service_instance
    if flow_service_instance is None:
        flow_service_instance = FlowAnalysisService()
    return flow_service_instance

async def save_latest_signal(message: str):
    """최근 알람 메시지 저장"""
    global latest_signal_message
    latest_signal_message = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "service": "flow_analysis"
    }

def is_market_hours() -> bool:
    """장중 시간 확인 (09:00-15:30, 평일만)"""
    now = datetime.now()
    
    # 주말 체크
    if now.weekday() >= 5:  # 5=토요일, 6=일요일
        return False
    
    # 장시간 체크
    current_time = now.time()
    market_open = datetime.strptime("09:00", "%H:%M").time()
    market_close = datetime.strptime("15:30", "%H:%M").time()
    
    return market_open <= current_time <= market_close

def should_execute_eod() -> Tuple[bool, str]:
    """EOD 처리 실행 여부 판단 (18:00)"""
    global eod_done_today, last_eod_date
    
    now = datetime.now()
    current_date = now.date()
    
    # 오늘 이미 EOD 처리를 했는지 확인
    if last_eod_date == current_date and eod_done_today:
        return False, f"오늘 EOD 처리 완료 ({last_eod_date})"
    
    # 18:00 시간 체크 (18:00-18:59 사이만 실행)
    current_time = now.time()
    eod_start = datetime.strptime("18:00", "%H:%M").time()
    eod_end = datetime.strptime("18:59", "%H:%M").time()
    
    if eod_start <= current_time <= eod_end:
        return True, f"EOD 시간 (18:00-18:59) - 현재: {current_time.strftime('%H:%M')}"
    else:
        return False, f"EOD 시간 아님 - 현재: {current_time.strftime('%H:%M')} (18:00-18:59에 실행)"

async def manage_websocket_lifecycle() -> Dict:
    """웹소켓 생명주기 관리"""
    global websocket_running

    try:
        is_market_time = is_market_hours()

        if is_market_time and not websocket_running:
            # 장중이고 웹소켓이 실행되지 않은 경우 → 시작
            logger.info("🚀 장중 시간 - 자금흐름 웹소켓 연결 시작")

            # 웹소켓 연결 시작
            flow_service = get_flow_service()

            # 종목 정보 로드
            with open(project_root / "config" / "stocks.json", "r", encoding="utf-8") as f:
                stocks_config = json.load(f)
                stock_codes = [stock["code"] for stock in stocks_config["stocks"]]

            # 프로그램 매매 모니터링 시작
            flow_service.start_program_flow_monitoring(stock_codes)

            websocket_running = True

            return {
                "action": "websocket_started", 
                "message": f"장중 자금흐름 웹소켓 연결 시작 - {len(stock_codes)}개 종목 모니터링"
            }

        elif not is_market_time and websocket_running:
            # 장외이고 웹소켓이 실행 중인 경우 → 종료
            logger.info("🛑 장외 시간 - 자금흐름 웹소켓 연결 종료")

            flow_service = get_flow_service()
            flow_service.is_running = False

            websocket_running = False

            return {
                "action": "websocket_stopped",
                "message": "장외 자금흐름 웹소켓 연결 종료"
            }
        else:
            # 상태 변화 없음
            status = "실행 중" if websocket_running else "정지"
            time_status = "장중" if is_market_time else "장외"

            return {
                "action": "no_change",
                "message": f"{time_status} - 자금흐름 웹소켓 {status} 상태 유지"
            }

    except Exception as e:
        logger.error(f"❌ 자금흐름 웹소켓 생명주기 관리 실패: {e}")
        return {
            "action": "error",
            "message": f"웹소켓 관리 오류: {str(e)}"
        }

async def execute_eod_processing() -> Dict:
    """EOD 처리 실행"""
    global eod_done_today, last_eod_date

    try:
        logger.info("📊 자금흐름 EOD 처리 실행 시작")

        flow_service = get_flow_service()

        # 종목 정보 로드
            # 종목 정보 로드
        try:
            with open(project_root / "config" / "stocks.json", "r", encoding="utf-8") as f:
                stocks_config = json.load(f)
                stock_codes = [stock["code"] for stock in stocks_config.get("stocks", [])]

            if not stock_codes:
                raise ValueError("⚠️ 종목 리스트가 비어 있음")

        except Exception as e:
            logger.warning(f"⚠️ 종목 설정 불러오기 실패 또는 비어 있음: {e} → 기본 종목으로 대체")
            stock_codes = ["006800"]

        processed_stocks = []
        triggered_stocks = []

        # 모든 종목에 대해 EOD 처리 실행
        for stock_code in stock_codes:
            try:
                logger.info(f"💰 {stock_code} EOD 수급 데이터 수집 시작")

                # 1. EOD 수급 데이터 수집
                success = await flow_service.collect_eod_flow_data(stock_code)

                if success:
                    # 2. 기관 매수 트리거 체크
                    trigger_result = await flow_service.check_institutional_buying_trigger(stock_code)

                    if trigger_result.get("triggered"):
                        await flow_service.handle_institutional_trigger(stock_code, trigger_result)
                        triggered_stocks.append(stock_code)
                        logger.info(f"🎯 {stock_code} 기관 매수 트리거 발생")

                processed_stocks.append(stock_code)

            except Exception as e:
                logger.error(f"❌ {stock_code} EOD 처리 실패: {e}")
                continue

        # EOD 처리 완료 플래그 설정
        eod_done_today = True
        last_eod_date = datetime.now().date()

        result = {
            "success": True,
            "processed_stocks": len(processed_stocks),
            "triggered_stocks": len(triggered_stocks),
            "execution_time": datetime.now().isoformat(),
            "details": {
                "processed": processed_stocks,
                "triggered": triggered_stocks
            }
        }

        logger.info(f"✅ EOD 처리 완료: {len(processed_stocks)}개 종목, {len(triggered_stocks)}개 트리거")
        return result

    except Exception as e:
        logger.error(f"❌ EOD 처리 실행 실패: {e}")
        return {"success": False, "error": str(e)}

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/signal")
async def get_latest_signal():
    """최근 알람 메시지 조회"""
    global latest_signal_message
    if latest_signal_message:
        return latest_signal_message
    else:
        return {
            "message": "아직 알람이 발생하지 않았습니다.",
            "timestamp": datetime.now().isoformat(),
            "service": "flow_analysis"
        }

@app.post("/execute")
async def execute_flow_analysis_endpoint(request: Request):
    """플로우 분석 실행 - 기간별 수급 데이터 분석"""
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}"
    
    logger.info(f"[Flow Analysis][{request_id}] API 호출 시작")
    logger.info(f"[Flow Analysis][{request_id}] 요청 정보:")
    logger.info(f"  - 엔드포인트: /execute")
    logger.info(f"  - 메소드: POST")
    logger.info(f"  - 클라이언트 IP: {request.client.host}")
    logger.info(f"  - User-Agent: {request.headers.get('user-agent', 'Unknown')}")
    
    try:
        # Header에서 user_id 추출 (문자열로 처리)
        user_id = request.headers.get("X-User-ID", "1")
        logger.info(f"[Flow Analysis][{request_id}] 사용자 ID: {user_id}")
        
        # 서비스 인스턴스의 user_id 동적 업데이트
        service = get_flow_service()
        if service.current_user_id != user_id:
            await service.set_user_id(user_id)
            logger.info(f"[Flow Analysis][{request_id}] 사용자 컨텍스트 변경: {user_id}")
        
        # 기간별 수급 분석 실행
        logger.info(f"[Flow Analysis][{request_id}] 기간별 수급 분석 시작")
        result = await service.analyze_flow_data_by_period()
        
        # 응답 로깅
        execution_time = time.time() - start_time
        success = result.get('success', False)
        analyzed_stocks = result.get('analyzed_stocks', 0)
        
        logger.info(f"[Flow Analysis][{request_id}] 분석 완료:")
        logger.info(f"  - 성공 여부: {'성공' if success else '실패'}")
        logger.info(f"  - 분석된 종목 수: {analyzed_stocks}")
        logger.info(f"  - 실행 시간: {execution_time:.2f}초")
        
        if not success:
            logger.warning(f"[Flow Analysis][{request_id}] 분석 실패 상세:")
            logger.warning(f"  - 에러 메시지: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[Flow Analysis][{request_id}] 치명적 오류 발생:")
        logger.error(f"  - 에러 타입: {type(e).__name__}")
        logger.error(f"  - 에러 메시지: {str(e)}")
        logger.error(f"  - 실행 시간: {execution_time:.2f}초")
        logger.error(f"  - 스택 트레이스:")
        import traceback
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                logger.error(f"    {line}")
        
        return {
            "success": False,
            "error": str(e),
            "request_id": request_id,
            "execution_time": execution_time
        }

@app.post("/check-schedule")
async def check_schedule():
    """오케스트레이터 체크 신호 수신 - 독립적으로 실행 시간 판단"""
    try:
        results = {}
        executed_tasks = []

        # 1. 웹소켓 생명주기 관리 (항상 체크)
        websocket_result = await manage_websocket_lifecycle()
        results["websocket"] = websocket_result

        if websocket_result["action"] != "no_change":
            executed_tasks.append("웹소켓 관리")

        # 2. EOD 처리 실행 여부 판단
        should_eod, eod_reason = should_execute_eod()

        if should_eod:
            # EOD 처리 실행
            eod_result = await execute_eod_processing()
            results["eod"] = eod_result
            executed_tasks.append("EOD 처리")

            if eod_result["success"]:
                message = f"EOD 처리 완료 - {eod_reason}"
            else:
                message = f"EOD 처리 실패 - {eod_result.get('error', 'Unknown')}"
        else:
            results["eod"] = {"skipped": True, "reason": eod_reason}

        # 실행된 작업 요약
        if executed_tasks:
            main_message = f"실행된 작업: {', '.join(executed_tasks)}"
            if "message" in locals():
                main_message += f" | {message}"

            return {
                "executed": True,
                "message": main_message,
                "details": results
            }
        else:
            return {
                "executed": False,
                "message": f"웹소켓: {websocket_result['message']}, EOD: {eod_reason}",
                "details": results
            }

    except Exception as e:
        logger.error(f"❌ 스케줄 체크 실패: {e}")
        return {
            "executed": False,
            "message": f"스케줄 체크 오류: {str(e)}"
        }

@app.post("/start-websocket")
async def start_websocket():
    """웹소켓 강제 시작"""
    try:
        result = await manage_websocket_lifecycle()
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/stop-websocket") 
async def stop_websocket():
    """웹소켓 강제 종료"""
    try:
        global websocket_running
        flow_service = get_flow_service()
        flow_service.is_running = False
        websocket_running = False
        return {"success": True, "message": "자금흐름 웹소켓 연결 종료"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/force-eod")
async def force_eod():
    """EOD 처리 강제 실행"""
    try:
        result = await execute_eod_processing()
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

    # === 사용자별 개인화 기능 ===
    
    async def initialize_user_personalization(self):
        """사용자 개인화 설정 초기화"""
        try:
            self.user_config_loader = await get_config_loader()
            self.logger.info("✅ 사용자 개인화 로더 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 사용자 개인화 로더 초기화 실패: {e}")
            self.user_config_loader = None

    async def get_personalized_config(self, user_id: str) -> Dict[str, Any]:
        """사용자별 개인화 설정 조회"""
        try:
            if not self.user_config_loader:
                self.logger.warning("⚠️ 사용자 설정 로더가 초기화되지 않음 - 기본값 사용")
                return self._get_default_config()
            
            # 캐시에서 먼저 확인
            if user_id in self.personalized_configs:
                return self.personalized_configs[user_id]
            
            # API를 통해 사용자 설정 로드
            config = await self.user_config_loader.load_user_config(user_id)
            if config:
                # 수급 분석 서비스에 특화된 설정 추출
                personalized_config = {
                    "user_id": user_id,
                    "stocks": [stock["stock_code"] for stock in config.get("stocks", [])],
                    "model_type": config.get("model_type", "hyperclova"),
                    "active_service": config.get("active_services", {}).get("flow_service", 0) == 1
                }
                
                # 캐시에 저장
                self.personalized_configs[user_id] = personalized_config
                self.logger.info(f"✅ 사용자 개인화 설정 로드 완료: {user_id}")
                return personalized_config
            else:
                self.logger.warning(f"⚠️ 사용자 설정을 찾을 수 없음: {user_id} - 기본값 사용")
                return self._get_default_config()
                
        except Exception as e:
            self.logger.error(f"❌ 사용자 개인화 설정 로드 실패: {user_id} - {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "user_id": "default",
            "stocks": ["005930", "000660"],  # 기본 종목: 삼성전자, SK하이닉스
            "model_type": "hyperclova",
            "active_service": True
        }

    async def should_analyze_for_user(self, user_id: str, stock_code: str) -> bool:
        """특정 사용자에 대해 해당 종목을 분석해야 하는지 확인"""
        try:
            config = await self.get_personalized_config(user_id)
            
            # 서비스가 비활성화된 경우
            if not config.get("active_service", True):
                return False
            
            # 사용자가 선택한 종목에 포함되지 않은 경우
            user_stocks = config.get("stocks", [])
            if stock_code not in user_stocks:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 사용자별 분석 필요성 확인 실패: {user_id}, {stock_code} - {e}")
            return True  # 오류 시 기본적으로 분석 진행

    async def get_user_analysis_model(self, user_id: str) -> str:
        """사용자가 선택한 AI 모델 반환"""
        try:
            config = await self.get_personalized_config(user_id)
            return config.get("model_type", "hyperclova")
        except Exception as e:
            self.logger.error(f"❌ 사용자 AI 모델 조회 실패: {user_id} - {e}")
            return "hyperclova"

    def clear_user_cache(self, user_id: Optional[str] = None):
        """사용자 설정 캐시 클리어"""
        if user_id:
            self.personalized_configs.pop(user_id, None)
            if self.user_config_loader:
                self.user_config_loader.clear_cache(user_id)
            self.logger.debug(f"🧹 사용자 설정 캐시 클리어: {user_id}")
        else:
            self.personalized_configs.clear()
            if self.user_config_loader:
                self.user_config_loader.clear_cache()
            self.logger.debug("🧹 모든 사용자 설정 캐시 클리어")

# === 메인 실행 ===

async def main():
    """메인 함수"""
    print("""
    🚀 수급 분석 서비스 시작
    ========================
    
    기능:
    - 실시간 프로그램 매매 데이터 수집
    - 일별 기관/외국인/개인 수급 데이터 수집  
    - 복합 트리거 패턴 감지
    - 과거 유사 사례 검색 및 알림
    
    포트: 8010 (API 서버)
    """)

    try:
        service = FlowAnalysisService()
        await service.run_service()

    except KeyboardInterrupt:
        print("\n수급 분석 서비스가 중단되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--service":
        # 서비스 모드 (실제 분석 작업 실행)
        #asyncio.run(main())
        asyncio.run(execute_eod_processing())
    else:
        # API 서버 모드 (기본값)
        print("🚀 수급 분석 API 서버 시작 (포트: 8010)")
        uvicorn.run(app, host="0.0.0.0", port=8010)