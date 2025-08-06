# type: ignore
"""
차트 분석 서비스 (Chart Service)
- KIS API를 통한 차트 데이터 수집
- 실시간 데이터 처리
- 8개 조건식 모니터링
- 조건 만족 시 DB 저장
"""
import os
import asyncio
import json
import logging
import pandas as pd

# 전역 로거 설정
logger = logging.getLogger(__name__)
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Union, Tuple, Any, cast, List
from pathlib import Path
import sys
import websockets
from collections import deque
from colorama import Fore, Style
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client, cleanup_mysql_client # get_mysql_client 임포트 방식 변경
from shared.apis.kis_api import KISAPIClient
from shared.apis.telegram_api import TelegramBotClient
from shared.user_config.user_config_manager import UserConfigManager
from shared.llm.hyperclova_client import HyperCLOVAClient
from shared.service_config.user_config_loader import get_config_loader
from config.env_local import get_config
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

# FastAPI 앱 초기화
app = FastAPI(title="Chart Service", description="차트 분석 서비스")

class ChartAnalysisService:
    """차트 분석 서비스 클래스"""

    def __init__(self):
        # 로깅 설정
        logging.basicConfig(
            level=logging.DEBUG,  # INFO -> DEBUG로 변경
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # 설정 로드
        self.config = get_config()
        self.logger.info(f"설정 로드: {self.config}")

        # 클라이언트 초기화
        self.mysql_client = get_mysql_client("mysql") # 메인 DB 클라이언트
        self.mysql2_client = get_mysql_client("mysql2") # 보조 DB 클라이언트 (HyperAsset2)
        self.kis_client = KISAPIClient()
        self.user_config_manager = UserConfigManager()
        self.llm_client = HyperCLOVAClient()  # 기본 LLM 클라이언트

        # 사용자 설정
        self.current_user_id = os.environ.get('HYPERASSET_USER_ID', "1")  # 🔥 환경변수에서 사용자 ID 읽기
        self.stocks_config = {}  # 사용자별 종목 설정
        self.current_model_type = "hyperclova"  # 기본 모델
        
        # 사용자별 개인화 설정 로더
        self.user_config_loader = None  # 비동기로 초기화됨
        self.personalized_configs = {}  # 사용자별 개인화 설정 캐시

        # 차트 데이터 저장소 (종목코드별)
        self.chart_data: Dict[str, pd.DataFrame] = {}
        
        # 실시간 데이터 큐 (최근 100개 데이터 유지)
        self.realtime_queue: Dict[str, deque] = {}
        
        # 웹소켓 연결 상태
        self.ws_connections: Dict[str, websockets.WebSocketClientProtocol] = {}

        # 조건 체크 상태
        self.last_conditions: Dict[str, Dict] = {}

        # 실시간 데이터 구독 여부
        self.is_subscribed: Dict[str, bool] = {}

        # 스케줄링 관련
        self.is_market_hours = False
        self.is_running = False
        self.websocket_tasks = []

        # 신호 저장 (텔레그램과 API 동시 제공용)
        self.latest_signals = []  # 최근 신호들 저장
        self.signal_lock = asyncio.Lock()  # 신호 동기화용

        self.last_token_time = None
        self.token_refresh_interval = 45 * 60  # 45분마다 토큰 갱신
        self.reconnect_attempts = 3
        self.reconnect_delay = 5  # 재연결 시도 간격(초)

        # 사용자 설정 로드
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
            
            stocks_result = await self.db_client.execute_query_async(
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
            
            # 사용자 기본 설정도 가져오기 (모델 타입 등)
            try:
                user_config = await self.user_config_manager.get_user_config(self.current_user_id)
                self.current_model_type = user_config.get("model_type", "hyperclova")
            except:
                self.logger.warning("⚠️ 사용자 모델 설정 로드 실패, 기본값 사용")
                self.current_model_type = "hyperclova"
            
            # LLM 클라이언트 업데이트
            await self._update_llm_client()
            
            self.logger.info(f"✅ 사용자 종목 설정 로드 완료: {len(self.stocks_config)}개 종목, 모델: {self.current_model_type}")
            
        except Exception as e:
            self.logger.error(f"❌ 사용자 설정 로드 실패 (기본값 유지): {e}")
            # 실패시 빈 종목 설정 (기본 종목 제거)
            self.stocks_config = {}
            self.current_model_type = "hyperclova"
    
    async def _update_llm_client(self):
        """LLM 클라이언트 업데이트"""
        try:
            if self.current_model_type == "hyperclova":
                self.llm_client = HyperCLOVAClient()
            # 추후 다른 모델 추가 가능
            # elif self.current_model_type == "openai":
            #     self.llm_client = OpenAIClient()
            # elif self.current_model_type == "gemini":
            #     self.llm_client = GeminiClient()
            
            self.logger.info(f"✅ LLM 클라이언트 업데이트 완료: {self.current_model_type}")
        except Exception as e:
            self.logger.error(f"❌ LLM 클라이언트 업데이트 실패: {e}")
    
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

    def _check_market_hours(self) -> Tuple[bool, str]:
        """장시간 체크 (한국시간 기준)"""
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()  # 0=월요일, 6=일요일
        
        # 장시간: 08:00-15:30 (한국시간)
        market_open = datetime.strptime("08:00", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        
        # 장후 시간: 18:00 이후
        after_market = datetime.strptime("18:00", "%H:%M").time()
        
        # 주말 체크 (토요일=5, 일요일=6)
        is_weekend = current_weekday >= 5
        
        if is_weekend:
            return False, "weekend"
        elif market_open <= current_time <= market_close:
            return True, "market_hours"
        elif current_time >= after_market:
            return False, "after_market"
        else:
            return False, "pre_market"

    def _convert_numpy_types(self, obj):
        """NumPy 타입을 Python 기본 타입으로 변환"""
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif hasattr(obj, 'item'):  # NumPy 타입
            return obj.item()
        return obj

    async def initialize_database(self):
        """차트 분석 테이블 생성"""
        try:
            query = """
            CREATE TABLE IF NOT EXISTS chart_analysis_results (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                date DATE NOT NULL,              -- 분석 날짜
                time TIME NOT NULL,              -- 분석 시간
                close_price FLOAT DEFAULT NULL,  -- 저장 당시 주가
                volume BIGINT DEFAULT NULL,      -- 저장 당시 거래량
                -- 조건 만족 여부
                golden_cross BOOLEAN DEFAULT FALSE,
                dead_cross BOOLEAN DEFAULT FALSE,
                bollinger_touch BOOLEAN DEFAULT FALSE,
                ma20_touch BOOLEAN DEFAULT FALSE,
                rsi_condition BOOLEAN DEFAULT FALSE,
                volume_surge BOOLEAN DEFAULT FALSE,
                macd_golden_cross BOOLEAN DEFAULT FALSE,
                support_resistance_break BOOLEAN DEFAULT FALSE,
                details JSON,
                INDEX idx_stock_date (stock_code, date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            # chart_analysis_results 테이블은 mysql2_client를 사용
            await self.mysql2_client.execute_query_async(query)
            self.logger.info("차트 분석 테이블 생성 완료")
        except Exception as e:
            self.logger.error(f"차트 분석 테이블 생성 실패: {e}")
            raise

    async def initialize_stock_data(self, stock_code: str) -> None:
        """종목별 초기 데이터 설정"""
        # 큐 초기화
        self.realtime_queue[stock_code] = deque(maxlen=100)
        
        # 과거 데이터 로드
        historical_df = await self.fetch_historical_data(stock_code)
        if not historical_df.empty:
            self.chart_data[stock_code] = historical_df
            self.logger.info(f"초기 데이터 설정 완료: {stock_code}")
        else:
            self.logger.error(f"초기 데이터 설정 실패: {stock_code}")

    async def start_monitoring(self, stocks_config: List[str]):
        """모니터링 시작"""
        try:
            tasks = []
            
            # 각 종목별 초기화 및 모니터링 시작
            for stock_code in stocks_config:
                # 초기 데이터 설정
                await self.initialize_stock_data(stock_code)
                
                # 웹소켓 연결 및 실시간 데이터 구독
                task = asyncio.create_task(self.connect_websocket(stock_code))
                tasks.append(task)
                
                self.logger.info(f"종목 모니터링 시작: {stock_code}")

            # 모든 웹소켓 연결 대기
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                self.logger.info("모니터링 작업 취소됨")
            except Exception as e:
                self.logger.error(f"모니터링 중 오류 발생: {e}")

        except Exception as e:
            self.logger.error(f"모니터링 시작 실패: {e}")
            raise

    async def process_realtime_data(self, stock_code: str, data: Union[str, Dict]) -> None:
        """실시간 데이터 처리"""
        try:
            # 데이터 파싱
            if isinstance(data, str):
                # 파이프(|)로 구분된 문자열 파싱
                parts = data.split("|")
                if len(parts) < 4:
                    self.logger.warning(f"잘못된 데이터 형식: {data}")
                    return

                # 데이터 필드 추출
                # 0|H0STCNT0|001|006800^100642^21600^5^-350^-1.59^21575.01^21550^21850^21350^21650^21600^5^829777^...
                fields = parts[3].split("^")
                if len(fields) < 12:
                    self.logger.warning(f"잘못된 필드 개수: {fields}")
                    return

                processed_data = {
                    "date": datetime.now().strftime("%Y%m%d"),
                    "time": fields[1],  # 시간
                    "open": float(fields[7]),  # 시가
                    "high": float(fields[8]),  # 고가
                    "low": float(fields[9]),   # 저가
                    "close": float(fields[4]), # 현재가
                    "volume": float(fields[12]), # 거래량
                }
            elif isinstance(data, dict):
                if "body" not in data or "output" not in data["body"]:
                    self.logger.warning(f"잘못된 데이터 형식: {data}")
                    return

                output = data["body"]["output"]
                processed_data = {
                    "date": datetime.now().strftime("%Y%m%d"),
                    "time": datetime.now().strftime("%H%M%S"),
                    "open": float(output.get("open", 0)),
                    "high": float(output.get("high", 0)),
                    "low": float(output.get("low", 0)),
                    "close": float(output.get("close", 0)),
                    "volume": float(output.get("cvolume", 0)),
                }
            else:
                self.logger.warning(f"지원하지 않는 데이터 형식: {type(data)}")
                return
            
            # 큐에 데이터 추가
            self.realtime_queue[stock_code].append(processed_data)

            # DataFrame 업데이트
            if stock_code in self.chart_data:
                # 새로운 데이터를 DataFrame에 추가
                new_row = pd.DataFrame([processed_data])
                self.chart_data[stock_code] = pd.concat([self.chart_data[stock_code], new_row])
                
                # 기술적 지표 재계산
                self.chart_data[stock_code] = await self.calculate_technical_indicators(self.chart_data[stock_code])

                # 조건 체크
                conditions = await self.check_all_conditions(stock_code, self.chart_data[stock_code])

                # 조건 만족 시 DB 저장 및 실시간 알림
                if conditions and any(result.get("condition", False) for name, result in conditions.get("conditions", {}).items() if isinstance(result, dict)):
                    await self.save_condition_results(conditions)
                    self.logger.info(f"조건 만족 결과 저장 완료: {stock_code}")
                    
                    # 실시간 텔레그램 알림 전송
                    satisfied_conditions = []
                    for name, result in conditions.get("conditions", {}).items():
                        if isinstance(result, dict) and result.get("condition", False):
                            satisfied_conditions.append({
                                "name": name,
                                "details": result.get("details", "조건 만족")
                            })
                    
                    if satisfied_conditions:
                        notification_data = {
                            "stock_code": stock_code,
                            "satisfied_conditions": satisfied_conditions,
                            "current_price": conditions["close_price"],
                            "current_volume": conditions["volume"],
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "time": datetime.now().strftime("%H:%M:%S")
                        }
                        
                        # 즉시 텔레그램 알림 전송
                        await self.send_condition_notification(notification_data)
                        self.logger.info(f"실시간 텔레그램 알림 전송 완료: {stock_code}")

        except Exception as e:
            self.logger.error(f"실시간 데이터 처리 실패: {e}")

    async def fetch_historical_data(self, stock_code: str, period: int = 100) -> pd.DataFrame:
        """과거 차트 데이터 수집"""
        try:
            # 일봉 데이터 조회 - KIS API에서 직접 리스트 형태로 반환받음
            daily_data = await self.kis_client.get_daily_chart(stock_code, period)
            
            if not daily_data:
                self.logger.warning(f"과거 데이터 없음: {stock_code}")
                return pd.DataFrame()

            # DataFrame으로 변환
            df = pd.DataFrame(daily_data)
            self.logger.info(f"KIS API 원본 데이터 수: {len(df)}건")
            
            # 필요한 컬럼이 있는지 확인
            if df.empty or 'date' not in df.columns:
                self.logger.warning(f"올바르지 않은 데이터 형식: {stock_code}")
                return pd.DataFrame()
            
            # 날짜 데이터 처리
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df = df.sort_values("date")
            self.logger.info(f"날짜 처리 후 데이터 수: {len(df)}건")

            # 필요한 컬럼 타입 변환
            price_columns = ["open", "high", "low", "close"]
            for col in price_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            if "volume" in df.columns:
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

            # 결측값 처리 전후 로그
            self.logger.info(f"결측값 처리 전 데이터 수: {len(df)}건")
            df = df.dropna()
            self.logger.info(f"결측값 처리 후 데이터 수: {len(df)}건")

            # 기술적 지표 계산 없이 바로 반환 (문제 해결을 위해)
            # df = await self.calculate_technical_indicators(df)

            self.logger.info(f"과거 데이터 수집 완료: {stock_code}, {len(df)}일")
            return df

        except Exception as e:
            self.logger.error(f"과거 데이터 수집 실패: {e}")
            return pd.DataFrame()

    async def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        try:
            # 데이터 복사
            df = df.copy()

            # 이동평균선 (5일, 20일)
            df["ma5"] = df["close"].rolling(window=5, min_periods=1).mean()
            df["ma20"] = df["close"].rolling(window=20, min_periods=1).mean()

            # 볼린저 밴드
            df["bb_middle"] = df["close"].rolling(window=20, min_periods=1).mean()
            df["bb_std"] = df["close"].rolling(window=20, min_periods=1).std()
            df["bb_upper"] = df["bb_middle"] + 2 * df["bb_std"]
            df["bb_lower"] = df["bb_middle"] - 2 * df["bb_std"]

            # RSI
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            rs = gain / loss
            df["rsi"] = 100 - (100 / (1 + rs))

            # MACD
            exp1 = df["close"].ewm(span=12, adjust=False).mean()
            exp2 = df["close"].ewm(span=26, adjust=False).mean()
            df["macd"] = exp1 - exp2
            df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
            df["macd_hist"] = df["macd"] - df["macd_signal"]

            # 결측값 처리
            df = df.fillna(method="bfill").fillna(method="ffill")

            # NumPy 타입을 Python 기본 타입으로 변환
            for col in df.columns:
                if df[col].dtype in ["int32", "int64", "float32", "float64"]:
                    df[col] = df[col].astype(float)

            return df

        except Exception as e:
            self.logger.error(f"기술적 지표 계산 실패: {e}")
            return df

    async def check_all_conditions(
        self, 
        stock_code: str, 
        df: Optional[pd.DataFrame] = None, 
        current_price: Optional[float] = None,
        current_volume: Optional[int] = None
    ) -> Dict:
        """모든 조건식 체크"""
        try:
            if df is None:
                if stock_code not in self.chart_data:
                    return {}
                df = self.chart_data[stock_code]

            # 현재가/거래량이 주어진 경우 마지막 행 업데이트
            if current_price is not None or current_volume is not None:
                df = df.copy()
                if current_price is not None:
                    df.iloc[-1, df.columns.get_loc("close")] = current_price
                if current_volume is not None:
                    df.iloc[-1, df.columns.get_loc("volume")] = current_volume

            # 기술적 지표 계산
            df = await self.calculate_technical_indicators(df)

            # 각 조건 체크
            conditions = {}
            for name, check_func in [
                ("golden_cross", self.check_golden_cross),
                ("dead_cross", self.check_dead_cross),
                ("bollinger_touch", self.check_bollinger_touch),
                ("ma20_touch", self.check_ma20_touch),
                ("rsi_condition", self.check_rsi_conditions),
                ("volume_surge", self.check_volume_surge),
                ("macd_golden_cross", self.check_macd_golden_cross),
                ("support_resistance_break", self.check_support_resistance_break)
            ]:
                try:
                    result = await check_func(df)
                    conditions[name] = result if result is not None else {"condition": False}
                except Exception as e:
                    self.logger.error(f"{name} 체크 실패: {e}")
                    conditions[name] = {"condition": False}

            # 현재 시간과 가격 정보 추가
            now = datetime.now()
            result = {
                "stock_code": stock_code,
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "close_price": float(current_price if current_price is not None else df.iloc[-1]["close"]),
                "volume": int(current_volume if current_volume is not None else df.iloc[-1]["volume"]),
                "conditions": conditions
            }

            # 조건 만족 여부 확인 및 알림 전송
            satisfied_conditions = []
            for name, condition in conditions.items():
                if condition.get("condition", False):
                    # 최근 발동일 확인
                    last_date = await self.get_latest_condition_date(stock_code, name)
                    
                    # 오늘 이전에 발동했거나 처음 발동하는 경우
                    if not last_date or last_date < now.strftime("%Y-%m-%d"):
                        satisfied_conditions.append({
                            "name": name,
                            "details": condition.get("details", "조건 만족")
                        })

            # 만족한 조건이 있으면 알림 전송
            if satisfied_conditions:
                await self.send_condition_notification({
                    "stock_code": stock_code,
                    "satisfied_conditions": satisfied_conditions,
                    "current_price": result["close_price"],
                    "current_volume": result["volume"],
                    "date": result["date"],
                    "time": result["time"]
                })

            # NumPy 타입을 Python 기본 타입으로 변환
            return self._convert_numpy_types(result)

        except Exception as e:
            self.logger.error(f"조건식 체크 실패: {e}")
            return {}

    async def save_condition_results(self, results: Dict) -> None:
        """조건 만족 결과를 DB에 저장"""
        try:
            if not results:
                return

            # NumPy 타입을 Python 기본 타입으로 변환
            results = self._convert_numpy_types(results)
            stock_code = results["stock_code"]
            current_time = datetime.now()
            
            # 조건 결과 저장
            query = """
                INSERT INTO chart_analysis_results (
                stock_code, date, time, close_price, volume,
                golden_cross, dead_cross, bollinger_touch, ma20_touch,
                rsi_condition, volume_surge, macd_golden_cross,
                support_resistance_break, details
                ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
            """

            # 조건 결과 변환
            conditions = results.get("conditions", {})
            details = {
                "close_price": results["close_price"],
                "volume": results["volume"],
                "conditions": {
                    name: {
                        "satisfied": cond.get("condition", False),
                        "details": cond.get("details", "")
                    } for name, cond in conditions.items()
                }
            }

            params = (
                stock_code,
                current_time.date(),
                current_time.time(),
                results["close_price"],
                results["volume"],
                conditions.get("golden_cross", {}).get("condition", False),
                conditions.get("dead_cross", {}).get("condition", False),
                conditions.get("bollinger_touch", {}).get("condition", False),
                conditions.get("ma20_touch", {}).get("condition", False),
                conditions.get("rsi_condition", {}).get("condition", False),
                conditions.get("volume_surge", {}).get("condition", False),
                conditions.get("macd_golden_cross", {}).get("condition", False),
                conditions.get("support_resistance_break", {}).get("condition", False),
                json.dumps(details, ensure_ascii=False)
            )

            # chart_analysis_results 테이블은 mysql2_client를 사용
            await self.mysql2_client.execute_query_async(query, params)
            self.logger.info(f"조건 만족 결과 저장 완료: {stock_code}")

        except Exception as e:
            self.logger.error(f"조건 만족 결과 저장 실패: {e}")
            raise

    async def _save_signal_for_api(self, signal_data: Dict):
        """API용 신호 저장 (텔레그램과 동시 제공)"""
        try:
            async with self.signal_lock:
                # 최근 100개 신호만 유지
                if len(self.latest_signals) >= 100:
                    self.latest_signals.pop(0)
                
                # 신호에 타임스탬프 추가
                signal_data["api_timestamp"] = datetime.now().isoformat()
                self.latest_signals.append(signal_data)
                
                self.logger.info(f"📡 API용 신호 저장 완료: {signal_data['stock_code']}")
        except Exception as e:
            self.logger.error(f"❌ API용 신호 저장 실패: {e}")

    async def _generate_llm_analysis(self, conditions_data: Dict) -> str:
        """LLM을 사용한 차트 분석 코멘트 생성"""
        try:
            stock_code = conditions_data["stock_code"]
            satisfied_conditions = conditions_data.get("satisfied_conditions", [])
            current_price = conditions_data.get("current_price", 0)
            
            # LLM 프롬프트 생성
            prompt = f"""
다음 차트 분석 결과를 바탕으로 투자자를 위한 간단하고 명확한 분석 코멘트를 작성해주세요.

종목: {stock_code}
현재가: {current_price:,}원
발생 신호: {', '.join([cond['name'] for cond in satisfied_conditions])}

조건별 상세:
"""
            for cond in satisfied_conditions:
                prompt += f"- {cond['name']}: {cond['details']}\n"

            prompt += """
다음 형식으로 답변해주세요:
1. 핵심 분석 (1-2줄)
2. 투자 시사점 (1-2줄)
3. 주의사항 (1줄)

전문적이지만 이해하기 쉽게 작성해주세요.
"""

            # LLM 호출
            response = await self.llm_client.generate_text_async(prompt)
            return response.strip() if response else "AI 분석을 생성할 수 없습니다."
            
        except Exception as e:
            self.logger.error(f"❌ LLM 분석 생성 실패: {e}")
            return "AI 분석을 생성하는 중 오류가 발생했습니다."

    async def check_golden_cross(self, df: pd.DataFrame) -> Dict:
        """골든크로스 체크 (5일선이 20일선 상향돌파)"""
        try:
            if len(df) < 20:
                return {"condition": False}

            # 이동평균 계산
            ma5 = df["close"].rolling(window=5).mean()
            ma20 = df["close"].rolling(window=20).mean()

            # 골든크로스 조건: 5일선이 20일선을 상향돌파
            cross_today = ma5.iloc[-1] > ma20.iloc[-1]
            cross_yesterday = ma5.iloc[-2] <= ma20.iloc[-2]

            if cross_today and cross_yesterday:
                result = {
                    "condition": True,
                    "details": f"5일선({float(ma5.iloc[-1]):,.0f})이 20일선({float(ma20.iloc[-1]):,.0f})을 상향돌파"
                }
                return self._convert_numpy_types(result)

            return {"condition": False}
        except Exception as e:
            self.logger.error(f"골든크로스 체크 실패: {e}")
            return {"condition": False}

    async def check_dead_cross(self, df: pd.DataFrame) -> Dict:
        """데드크로스 체크 (5일선이 20일선 하향돌파)"""
        try:
            if len(df) < 20:
                return {"condition": False}

            # 이동평균 계산
            ma5 = df["close"].rolling(window=5).mean()
            ma20 = df["close"].rolling(window=20).mean()

            # 데드크로스 조건: 5일선이 20일선을 하향돌파
            cross_today = ma5.iloc[-1] < ma20.iloc[-1]
            cross_yesterday = ma5.iloc[-2] >= ma20.iloc[-2]

            if cross_today and cross_yesterday:
                result = {
                    "condition": True,
                    "details": f"5일선({float(ma5.iloc[-1]):,.0f})이 20일선({float(ma20.iloc[-1]):,.0f})을 하향돌파"
                }
                return self._convert_numpy_types(result)

            return {"condition": False}
        except Exception as e:
            self.logger.error(f"데드크로스 체크 실패: {e}")
            return {"condition": False}

    async def check_bollinger_touch(self, df: pd.DataFrame) -> Dict:
        """볼린저 밴드 터치 체크"""
        try:
            if len(df) < 20:
                return {"condition": False}

            # 볼린저 밴드 계산
            ma20 = df["close"].rolling(window=20).mean()
            std20 = df["close"].rolling(window=20).std()
            upper = ma20 + 2 * std20
            lower = ma20 - 2 * std20

            # 현재가
            current_price = df["close"].iloc[-1]

            # 상단 또는 하단 터치 여부
            touch_upper = abs(current_price - upper.iloc[-1]) / upper.iloc[-1] < 0.01
            touch_lower = abs(current_price - lower.iloc[-1]) / lower.iloc[-1] < 0.01

            if touch_upper or touch_lower:
                band = "상단" if touch_upper else "하단"
                price = upper.iloc[-1] if touch_upper else lower.iloc[-1]
                result = {
                    "condition": True,
                    "details": f"볼린저밴드 {band}({float(price):,.0f})에 터치"
                }
                return self._convert_numpy_types(result)

            return {"condition": False}
        except Exception as e:
            self.logger.error(f"볼린저밴드 체크 실패: {e}")
            return {"condition": False}

    async def check_ma20_touch(self, df: pd.DataFrame) -> Dict:
        """20일선 터치 체크"""
        try:
            if len(df) < 20:
                return {"condition": False}

            # 20일 이동평균선
            ma20 = df["close"].rolling(window=20).mean()

            # 현재가
            current_price = df["close"].iloc[-1]

            # 터치 여부 (1% 이내)
            touch = abs(current_price - ma20.iloc[-1]) / ma20.iloc[-1] < 0.01

            if touch:
                result = {
                    "condition": True,
                    "details": f"20일선({float(ma20.iloc[-1]):,.0f})에 터치"
                }
                return self._convert_numpy_types(result)

            return {"condition": False}
        except Exception as e:
            self.logger.error(f"20일선 터치 체크 실패: {e}")
            return {"condition": False}

    async def check_rsi_conditions(self, df: pd.DataFrame) -> Dict:
        """RSI 과매수/과매도 체크"""
        try:
            if len(df) < 14:
                return {"condition": False}

            # RSI 계산
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # 현재 RSI
            current_rsi = rsi.iloc[-1]

            # 과매수/과매도 조건
            if current_rsi >= 70:  # 과매수
                result = {
                    "condition": True,
                    "details": f"RSI 과매수({float(current_rsi):.1f})"
                }
                return self._convert_numpy_types(result)
            elif current_rsi <= 30:  # 과매도
                result = {
                    "condition": True,
                    "details": f"RSI 과매도({float(current_rsi):.1f})"
                }
                return self._convert_numpy_types(result)

            return {"condition": False}
        except Exception as e:
            self.logger.error(f"RSI 체크 실패: {e}")
            return {"condition": False}

    async def check_volume_surge(self, df: pd.DataFrame) -> Dict:
        """거래량 급증 체크"""
        try:
            if len(df) < 20:
                return {"condition": False}

            # 20일 평균 거래량
            avg_volume = df["volume"].rolling(window=20).mean()

            # 현재 거래량
            current_volume = df["volume"].iloc[-1]

            # 거래량 급증 조건 (300% 이상)
            if current_volume > avg_volume.iloc[-1] * 3:
                result = {
                    "condition": True,
                    "details": f"거래량({int(current_volume):,}"
                }
                return self._convert_numpy_types(result)

            return {"condition": False}
        except Exception as e:
            self.logger.error(f"거래량 급증 체크 실패: {e}")
            return {"condition": False}

    async def check_macd_golden_cross(self, df: pd.DataFrame) -> Dict:
        """MACD 골든크로스 체크"""
        try:
            if len(df) < 26:
                return {"condition": False}

            # MACD 계산
            exp1 = df["close"].ewm(span=12, adjust=False).mean()
            exp2 = df["close"].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()

            # MACD 골든크로스 조건
            cross_today = macd.iloc[-1] > signal.iloc[-1]
            cross_yesterday = macd.iloc[-2] <= signal.iloc[-2]

            if cross_today and cross_yesterday:
                result = {
                    "condition": True,
                    "details": f"MACD({float(macd.iloc[-1]):,.0f})가 시그널({float(signal.iloc[-1]):,.0f})을 상향돌파"
                }
                return self._convert_numpy_types(result)

            return {"condition": False}
        except Exception as e:
            self.logger.error(f"MACD 골든크로스 체크 실패: {e}")
            return {"condition": False}

    async def check_support_resistance_break(self, df: pd.DataFrame) -> Dict:
        """지지/저항선 돌파 체크"""
        try:
            if len(df) < 20:
                return {"condition": False}

            # 20일 고가/저가
            high_20d = df["high"].rolling(window=20).max()
            low_20d = df["low"].rolling(window=20).min()

            # 현재가
            current_price = df["close"].iloc[-1]

            # 돌파 조건 (2% 이상)
            break_up = current_price > high_20d.iloc[-2] * 1.02  # 전일 고점 대비
            break_down = current_price < low_20d.iloc[-2] * 0.98  # 전일 저점 대비

            if break_up:
                result = {
                    "condition": True,
                    "details": f"저항선({float(high_20d.iloc[-2]):,.0f}) 상향돌파"
                }
                return self._convert_numpy_types(result)
            elif break_down:
                result = {
                    "condition": True,
                    "details": f"지지선({float(low_20d.iloc[-2]):,.0f}) 하향돌파"
                }
                return self._convert_numpy_types(result)

            return {"condition": False}
        except Exception as e:
            self.logger.error(f"지지/저항선 돌파 체크 실패: {e}")
            return {"condition": False}

    async def stop_monitoring(self):
        """서비스 종료"""
        try:
            # 모든 종목의 구독 해제
            for stock_code in list(self.is_subscribed.keys()):
                self.is_subscribed[stock_code] = False
            
            self.logger.info("서비스가 정상적으로 종료되었습니다.")

        except Exception as e:
            self.logger.error(f"서비스 종료 중 오류 발생: {e}")
            raise

    async def run_service(self):
        """스마트 스케줄링이 적용된 차트 분석 서비스 실행"""
        try:
            self.logger.info("🚀 Chart Service 시작 (스마트 스케줄링 적용)")
            self.is_running = True
            
            while self.is_running:
                try:
                    # 현재 시장 상태 확인
                    is_market, market_status = self._check_market_hours()
                    self.is_market_hours = is_market
                    
                    self.logger.info(f"📊 시장 상태: {market_status} (장중: {is_market})")
                    
                    if market_status == "market_hours":
                        # 장중: 실시간 웹소켓 + 5분마다 조건 체크
                        await self._run_market_hours_mode()
                        
                    elif market_status == "after_market":
                        # 장후: 1회 분석 후 대기
                        await self._run_after_market_mode()
                        
                    elif market_status == "weekend":
                        # 주말: 1일 1회 분석
                        await self._run_weekend_mode()
                        
                    else:  # pre_market
                        # 장전: 1시간 대기
                        self.logger.info("🌅 장전 시간 - 1시간 대기")
                        await asyncio.sleep(3600)

                except KeyboardInterrupt:
                    self.logger.info("⏹️ 서비스 중단 요청")
                    break
                except Exception as e:
                    self.logger.error(f"❌ 서비스 실행 오류: {e}")
                    await asyncio.sleep(60)  # 1분 대기 후 재시도

        except Exception as e:
            self.logger.error(f"❌ 차트 분석 서비스 실행 실패: {e}")
            raise
        finally:
            self.is_running = False
            await self.stop_monitoring()
            # 모든 MySQL 클라이언트 정리
            await self.mysql_client.close()
            await self.mysql2_client.close()

    async def _run_market_hours_mode(self):
        """장중 모드: 실시간 웹소켓 + 5분마다 조건 체크"""
        try:
            self.logger.info("📈 장중 모드 시작 - 실시간 모니터링")
            
            # 웹소켓 연결 시작 (백그라운드)
            if not self.websocket_tasks:
                for stock_code in self.stocks_config.keys():
                    task = asyncio.create_task(self.connect_websocket(stock_code))
                    self.websocket_tasks.append(task)
                    self.logger.info(f"🔗 웹소켓 연결 시작: {stock_code}")
            
            # 5분마다 조건 체크
            for _ in range(12):  # 5분 * 12 = 1시간
                await self._check_all_stocks_conditions()
                
                # 시장 시간 재확인
                is_market, _ = self._check_market_hours()
                if not is_market:
                    self.logger.info("📊 장시간 종료 감지 - 웹소켓 중단")
                    await self._stop_websockets()
                    break
                    
                await asyncio.sleep(300)  # 5분 대기
                
        except Exception as e:
            self.logger.error(f"❌ 장중 모드 실행 오류: {e}")
            await self._stop_websockets()

    async def _run_after_market_mode(self):
        """장후 모드: 1회 분석 후 대기"""
        try:
            self.logger.info("🌆 장후 모드 - 1회 분석 실행")
            
            # 웹소켓 중단
            await self._stop_websockets()
            
            # 1회 분석 실행
            await self._check_all_stocks_conditions()
            
            # 다음날 장전까지 대기 (약 14시간)
            self.logger.info("😴 장후 분석 완료 - 다음날까지 대기")
            await asyncio.sleep(14 * 3600)  # 14시간 대기
            
        except Exception as e:
            self.logger.error(f"❌ 장후 모드 실행 오류: {e}")

    async def _run_weekend_mode(self):
        """주말 모드: 1일 1회 분석"""
        try:
            self.logger.info("🏖️ 주말 모드 - 1일 1회 분석")
            
            # 웹소켓 중단
            await self._stop_websockets()
            
            # 1회 분석 실행
            await self._check_all_stocks_conditions()
            
            # 24시간 대기
            self.logger.info("😴 주말 분석 완료 - 24시간 대기")
            await asyncio.sleep(24 * 3600)
            
        except Exception as e:
            self.logger.error(f"❌ 주말 모드 실행 오류: {e}")

    async def _check_all_stocks_conditions(self):
        """모든 종목의 조건 체크"""
        try:
            try:
                stock_items = self.stocks_config.items()
                if not stock_items:
                    raise ValueError("stocks_config가 비어있음")
            except Exception as e:
                self.logger.warning(f"⚠️ 종목 설정 불러오기 실패 또는 비어있음: {e} → 기본 종목으로 대체")
                stock_items = [("006800", {})
                
                
            self.logger.info(f"🔍 전체 종목 조건 체크 시작: {len(stock_items)}개 종목")
            
            for stock_code, stock_info in stock_items:
                if not stock_info.get("enabled", True):
                    continue
                
                try:
                    # 1. 과거 데이터 수집
                    df = await self.fetch_historical_data(stock_code)
                    if df.empty:
                        self.logger.warning(f"📊 차트 데이터 없음: {stock_code}")
                        continue

                    # 2. 기술적 지표 계산
                    df = await self.calculate_technical_indicators(df)

                    # 3. 조건 체크
                    conditions = await self.check_all_conditions(stock_code, df)
                    if not conditions:
                        continue

                    # 4. 조건 만족 시 처리
                    satisfied_conditions = []
                    for name, result in conditions.get("conditions", {}).items():
                        if result.get("condition", False):
                            # 최근 발동일 확인
                            last_date = await self.get_latest_condition_date(stock_code, name)
                            
                            # 오늘 이전에 발동했거나 처음 발동하는 경우
                            if not last_date or last_date < datetime.now().strftime("%Y-%m-%d"):
                                satisfied_conditions.append({
                                    "name": name,
                                    "details": result.get("details", "조건 만족")
                                })

                    if satisfied_conditions:
                        # 5. DB 저장
                        await self.save_condition_results(conditions)
                        
                        # 6. 신호 데이터 준비
                        signal_data = {
                            "stock_code": stock_code,
                            "stock_name": stock_info.get("name", stock_code),
                            "satisfied_conditions": satisfied_conditions,
                            "current_price": conditions.get("close_price"),
                            "current_volume": conditions.get("volume"),
                            "date": conditions.get("date"),
                            "time": conditions.get("time")
                        }
                        
                        # 7. LLM 분석 추가
                        llm_analysis = await self._generate_llm_analysis(signal_data)
                        signal_data["llm_analysis"] = llm_analysis
                        
                        # 8. API용 신호 저장 (텔레그램과 동시 제공)
                        await self._save_signal_for_api(signal_data)
                        
                        # 9. 텔레그램 알림 전송
                        await self.send_condition_notification(signal_data)
                        
                        self.logger.info(f"🎯 신호 발생 처리 완료: {stock_code}")

                except Exception as e:
                    self.logger.error(f"❌ {stock_code} 처리 중 오류: {e}")
                    continue
                    
            self.logger.info("✅ 전체 종목 조건 체크 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 전체 종목 조건 체크 실패: {e}")

    async def _stop_websockets(self):
        """모든 웹소켓 연결 중단"""
        try:
            if self.websocket_tasks:
                for task in self.websocket_tasks:
                    task.cancel()
                    
                # 모든 태스크 완료 대기
                await asyncio.gather(*self.websocket_tasks, return_exceptions=True)
                self.websocket_tasks.clear()
                
                self.logger.info("🔌 모든 웹소켓 연결 중단 완료")
        except Exception as e:
            self.logger.error(f"❌ 웹소켓 중단 오류: {e}")

    async def get_latest_condition_date(self, stock_code: str, condition_name: str) -> Optional[str]:
        """특정 조건을 만족한 가장 최근 날짜 조회 (영업일 기준 5일 이내 제외)"""
        try:
            self.logger.info(f"최근 조건 만족 날짜 조회: {stock_code}, {condition_name}")
            
            # 영업일 기준 5일 이전 날짜 계산 (KIS API로부터)
            df = await self.fetch_historical_data(stock_code, period=20)  # 여유있게 20일 조회
            if df.empty:
                self.logger.error("KIS API에서 과거 데이터를 가져올 수 없습니다.")
                return None
                
            # 날짜 정렬 (최신순)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)
            
            # 영업일 기준 5일째 이후 날짜 계산
            if len(df) > 5:
                cutoff_date = df.iloc[5]['date']  # 오늘부터 5번째 영업일
                cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
                self.logger.info(f"영업일 기준 5일 이후 cutoff 날짜: {cutoff_date_str}")
            else:
                # 데이터가 부족하면 일주일 전으로 설정
                cutoff_date = datetime.now() - timedelta(days=7)
                cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
                self.logger.info(f"데이터 부족으로 7일 전 cutoff 날짜 사용: {cutoff_date_str}")
            
            query = f"""
            SELECT date 
            FROM chart_analysis_results 
            WHERE stock_code = %s 
            AND {condition_name} = 1
            AND date < %s
            ORDER BY date DESC, time DESC 
            LIMIT 1
            """
            
            self.logger.info(f"SQL 쿼리: {query}")
            self.logger.info(f"매개변수: stock_code={stock_code}, cutoff_date={cutoff_date_str}")
            # chart_analysis_results 테이블은 mysql2_client를 사용
            result = await self.mysql2_client.execute_query_async(query, (stock_code, cutoff_date_str), fetch=True)
            
            self.logger.info(f"쿼리 결과: {result}")
            if result and len(result) > 0:
                date = result[0]['date']
                self.logger.info(f"최근 만족 날짜: {date}")
                return date.strftime("%Y-%m-%d")
            
            self.logger.info("영업일 5일 이전의 최근 만족 날짜 없음")
            return None
            
        except Exception as e:
            self.logger.error(f"최근 조건 만족 날짜 조회 실패: {e}")
            return None

    async def get_historical_prices(self, stock_code: str, from_date: str, days: int = 5) -> List[Dict]:
        """특정 날짜로부터 이후 영업일 N일간의 가격 정보 조회 (KIS API)"""
        try:
            self.logger.info(f"과거 가격 정보 조회: {stock_code}, {from_date}, 영업일 {days}일")
            
            # 날짜 형식 변환 및 데이터 범위 확인
            from_date_dt = pd.to_datetime(from_date)
            current_date = datetime.now()
            days_diff = (current_date - from_date_dt).days
            
            # 먼저 확장된 API로 더 긴 기간 데이터 시도
            self.logger.info(f"참조날짜로부터 {days_diff}일 경과, 확장된 API로 시도")
            
            # 시작일과 종료일 계산
            start_date = (from_date_dt - timedelta(days=30)).strftime('%Y%m%d')
            end_date = datetime.now().strftime('%Y%m%d')
            
            # 새로운 확장된 API 사용
            extended_data = await self.kis_client.get_daily_chart_extended(
                stock_code, 
                start_date=start_date,
                end_date=end_date,
                period=1000
            )
            
            if extended_data:
                # pandas DataFrame으로 변환
                df = pd.DataFrame(extended_data)
                df['date'] = pd.to_datetime(df['date'])
                self.logger.info(f"확장된 API로 {len(extended_data)}일 데이터 조회 성공")
            else:
                # 기본 API로 fallback
                self.logger.info("확장 API 실패, 기본 API로 시도")
                period = max(100, days_diff + 10)  # 최소 100일, 또는 필요한 만큼
                df = await self.fetch_historical_data(stock_code, period=period)
                if df.empty:
                    self.logger.error("KIS API에서 과거 데이터를 가져올 수 없습니다.")
                    return []
                df['date'] = pd.to_datetime(df['date'])
            
            # 참조날짜가 데이터 범위에 있는지 확인
            min_date = df['date'].min()
            max_date = df['date'].max()
            self.logger.info(f"KIS API 데이터 범위: {min_date.strftime('%Y-%m-%d')} ~ {max_date.strftime('%Y-%m-%d')}")
            
            if from_date_dt < min_date:
                self.logger.warning(f"참조날짜 {from_date}가 KIS API 범위({min_date.strftime('%Y-%m-%d')}) 밖입니다.")
                # 사용 가능한 가장 이른 날짜부터 5일간 데이터 반환
                from_date_dt = min_date
                self.logger.info(f"대신 사용 가능한 가장 이른 날짜 {from_date_dt.strftime('%Y-%m-%d')} 사용")

            # 기준일(from_date) 다음날부터의 데이터만 필터링 (영업일 기준)
            after_date_df = df[df['date'] > from_date_dt].copy()
            
            # 날짜 순으로 정렬
            after_date_df = after_date_df.sort_values('date')
            
            # 영업일 기준 N일만 선택 (실제 거래가 있는 날짜만)
            result_df = after_date_df.head(days)

            # 결과 변환 및 수익률 계산
            results = []
            if not result_df.empty:
                first_price = result_df.iloc[0]['close'] if len(result_df) > 0 else None
                
                for _, row in result_df.iterrows():
                    change_rate = None
                    if first_price and first_price > 0:
                        change_rate = ((row['close'] - first_price) / first_price) * 100
                    
                    results.append({
                        "date": row['date'].strftime("%m/%d"),
                        "close": float(row['close']),
                        "change_rate": change_rate
                    })

            self.logger.info(f"KIS API에서 조회된 영업일 데이터: {len(results)}건")
            return results

        except Exception as e:
            self.logger.error(f"과거 가격 정보 조회 실패: {e}")
            return []

    async def send_condition_notification(self, results: Dict) -> None:
        """조건 만족 시 알림 전송 (사용자별 설정 확인)"""
        try:
            # 종목 코드로 최근 만족 날짜 조회
            satisfied_conditions = results.get("satisfied_conditions", [])
            if not satisfied_conditions:
                return

            stock_code = results["stock_code"]
            
            # 각 만족한 조건에 대해 과거 데이터 조회
            for condition in satisfied_conditions:
                condition_name = condition["name"]
                
                # 과거 같은 조건을 만족한 가장 최근 날짜(A) 찾기
                last_condition_date = await self.get_latest_condition_date(stock_code, condition_name)
                
                if last_condition_date:
                    # A 날짜로부터 5일간의 주가 데이터 조회
                    five_day_prices = await self.get_historical_prices(stock_code, last_condition_date, 5)
                    condition["five_day_prices"] = five_day_prices
                    condition["reference_date"] = last_condition_date
                    self.logger.info(f"과거 참조 날짜: {last_condition_date}, 5일 데이터: {len(five_day_prices)}건")
                else:
                    condition["five_day_prices"] = []
                    condition["reference_date"] = None
                    self.logger.info(f"과거 참조 데이터 없음: {condition_name}")

            # 알림 메시지 생성
            message = await self._format_notification_message(results)

            # 🆕 사용자별 알림 전송 (설정 확인)
            await self._send_user_notifications(results, message)
            
            # 🆕 채널 알림 전송 (기존 방식 유지)
            await self._send_channel_notification(message)
            
            # 최근 알람 메시지 저장
            await save_latest_signal(message)

        except Exception as e:
            self.logger.error(f"알림 전송 실패: {e}")
            raise
    
    async def _send_user_notifications(self, results: Dict, message: str):
        """사용자별 알림 전송 (설정 확인 + 종목 필터링)"""
        try:
            # UserConfigLoader import
            from shared.service_config.user_config_loader import UserConfigLoader
            
            config_loader = UserConfigLoader()
            stock_code = results.get("stock_code", "")
            
            # 모든 활성 사용자 조회 (현재는 테스트용으로 고정 사용자)
            # TODO: 실제로는 데이터베이스에서 활성 사용자 목록을 조회해야 함
            test_users = ["1"]  # 테스트용 사용자 ID
            
            for user_id in test_users:
                try:
                    # 🆕 사용자가 이 종목에 관심이 있는지 확인
                    is_interested = await config_loader.is_user_interested_in_stock(user_id, stock_code)
                    if not is_interested:
                        self.logger.debug(f"⚠️ 사용자가 종목에 관심 없음: {user_id} - {stock_code}")
                        continue
                    
                    # 사용자별 알림 설정 조회
                    notification_settings = await config_loader.get_user_notification_settings(user_id)
                    
                    # 차트 알림이 활성화되어 있고, 전체 알림이 활성화된 경우만 전송
                    if (notification_settings.get("enabled", True) and 
                        notification_settings.get("chart_alerts", True)):
                        
                        # 사용자별 텔레그램 설정 조회
                        telegram_config = await config_loader.get_user_telegram_config(user_id)
                        if telegram_config and telegram_config.get("enabled", True):
                            # 개별 사용자에게 알림 전송
                            await self._send_user_notification(user_id, message, telegram_config)
                            self.logger.info(f"✅ 사용자 차트 알림 전송 완료: {user_id} - {stock_code}")
                        else:
                            self.logger.debug(f"⚠️ 사용자 텔레그램 비활성화: {user_id}")
                    else:
                        self.logger.debug(f"⚠️ 사용자 차트 알림 비활성화: {user_id}")
                        
                except Exception as user_error:
                    self.logger.error(f"❌ 사용자 차트 알림 전송 실패: {user_id} - {user_error}")
                    
        except Exception as e:
            self.logger.error(f"❌ 사용자별 차트 알림 전송 실패: {e}")
    
    async def _send_user_notification(self, user_id: str, message: str, telegram_config: Dict):
        """개별 사용자에게 알림 전송"""
        try:
            # 사용자별 채팅 ID 사용
            chat_id = telegram_config.get("chat_id")
            if chat_id:
                # 텔레그램 봇으로 개별 사용자에게 전송
                from shared.apis.telegram_api import TelegramBotClient
                telegram_bot = TelegramBotClient()
                telegram_bot.send_message(message, str(chat_id))
                self.logger.info(f"✅ 개별 사용자 차트 알림 전송 완료: {user_id} -> {chat_id}")
            else:
                self.logger.warning(f"⚠️ 사용자 채팅 ID 없음: {user_id}")
                
        except Exception as e:
            self.logger.error(f"❌ 개별 사용자 차트 알림 전송 실패: {user_id} - {e}")
    
    async def _send_channel_notification(self, message: str):
        """채널 알림 전송 (기존 방식)"""
        try:
            from shared.apis.telegram_api import TelegramBotClient
            telegram_bot = TelegramBotClient()
            await telegram_bot.send_message_async(message)
            self.logger.info("✅ 채널 차트 알림 전송 완료")
        except Exception as e:
            self.logger.error(f"❌ 채널 차트 알림 전송 실패: {e}")

    async def restore_subscriptions(self, stock_code: str):
        """연결 종료 전 구독 정보 복구"""
        if stock_code not in self.realtime_queue:
            return
            
        subscribe_msg = {
            "header": {"tr_id": "H0STCNT0"},
            "body": {
                "input": {
                    "tr_key": stock_code
                }
            }
        }
        if self.ws_connections.get(stock_code) and not self.ws_connections[stock_code].closed:
            await self.ws_connections[stock_code].send(json.dumps(subscribe_msg))
            self.logger.info(f"종목 {stock_code} 구독 복구 완료")
        else:
            self.logger.warning(f"종목 {stock_code} 웹소켓 연결이 닫혀 있어 구독 복구를 건너뛰었습니다.")

    async def connect_websocket(self, stock_code: str) -> None:
        """웹소켓 연결 및 실시간 데이터 구독"""
        retry_count = 0
        max_retries = 10
        base_delay = 1  # 초기 대기 시간 (초)
        
        while True:  # 무한 루프로 변경
            websocket = None
            try:
                # 토큰 발급 또는 갱신이 필요한 경우
                if not self.last_token_time or \
                   (time.time() - self.last_token_time) > self.token_refresh_interval:
                    self.kis_client._get_approval_key()
                    self.last_token_time = time.time()
                    self.logger.info("웹소켓 승인키 갱신 완료")

                # 실제 웹소켓 URL 사용
                uri = self.kis_client.ws_url + "/tryitout/H0STCNT0"
                
                # 새로운 연결 생성
                websocket = await websockets.connect(uri)
                
                # 초기 연결 메시지 전송
                connect_msg = {
                    "header": {
                        "approval_key": self.kis_client.approval_key,
                        "custtype": "P",
                        "tr_type": "1"
                    },
                    "body": {
                        "input": {
                            "tr_id": "H0STCNT0",
                            "tr_key": stock_code
                        }
                    }
                }
                
                await websocket.send(json.dumps(connect_msg))
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # 응답 체크: rt_cd가 0이고 msg1이 SUBSCRIBE SUCCESS인 경우 성공
                if not response_data or \
                   response_data.get("body", {}).get("rt_cd") != "0" or \
                   "SUBSCRIBE SUCCESS" not in response_data.get("body", {}).get("msg1", ""):
                    raise Exception(f"웹소켓 연결 실패: {response_data}")
                
                self.logger.info(f"웹소켓 연결 성공: {response_data.get('body', {}).get('msg1')}")
                self.is_subscribed[stock_code] = True
                retry_count = 0  # 연결 성공 시 재시도 카운트 초기화
                
                # 메시지 수신 루프
                while True:
                    message = await websocket.recv()
                    await self.process_realtime_data(stock_code, message)
                    
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning(f"웹소켓 연결 종료: {stock_code}")
            except asyncio.CancelledError:
                self.logger.info(f"웹소켓 연결 작업 취소: {stock_code}")
                return  # 작업 취소 시 완전히 종료
            except Exception as e:
                self.logger.error(f"웹소켓 연결 오류: {e}")
            finally:
                self.is_subscribed[stock_code] = False
                if websocket:
                    try:
                        await websocket.close()
                    except:
                        pass
                
                # 재연결 시도 전 지수 백오프 적용
                if retry_count < max_retries:
                    delay = min(300, base_delay * (2 ** retry_count))  # 최대 5분까지 대기
                    self.logger.info(f"{stock_code} 재연결 시도 {retry_count + 1}/{max_retries} - {delay}초 후 시도")
                    retry_count += 1
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"{stock_code} 최대 재시도 횟수 초과. 1분 후 재시도 카운트 초기화")
                    retry_count = 0
                    await asyncio.sleep(60)

    async def _format_notification_message(self, results: Dict) -> str:
        """알림 메시지 포맷팅 (LLM 분석 포함)"""
        stock_code = results["stock_code"]
        conditions = results["satisfied_conditions"]
        current_price = results["current_price"]
        current_volume = results["current_volume"]
        date = results["date"]
        time = results["time"]
        llm_analysis = results.get("llm_analysis", "")
        
        # 종목 정보 조회 (또는 제공된 이름 사용)
        stock_name = results.get("stock_name")
        if not stock_name:
            try:
                # stock_info 테이블은 mysql_client를 사용
                stock_info = await self.mysql_client.execute_query_async(
                    "SELECT company_name FROM stock_info WHERE stock_code = %s",
                    (stock_code,),
                    fetch=True
                )
                stock_name = stock_info[0]["company_name"] if stock_info else stock_code
            except:
                stock_name = stock_code

        # 🚨 헤더 부분
        message = f"🚨 <b>{stock_name}</b> 매매신호 발동! 🚨\n"
        message += f"━━━━━━━━━━━━━━━━━━━\n"
        message += f"📋 종목: <code>{stock_name}({stock_code})</code>\n"
        message += f"⏰ 시간: <code>{date} {time}</code>\n\n"
        
        # 💰 현재 상황
        message += f"💰 <b>현재 상황</b>\n"
        message += f"├ 현재가: <b>{current_price:,}원</b>\n"
        message += f"└ 거래량: <b>{current_volume:,}주</b>\n\n"
        
        # ⚡ 발생 신호
        message += f"⚡ <b>발생 신호</b>\n"
        for i, condition in enumerate(conditions):
            name = condition["name"]
            details = condition["details"]
            
            # 조건명 한글화 및 이모지 추가
            condition_info = {
                "golden_cross": ("🌟 골든크로스", "📈"),
                "dead_cross": ("💀 데드크로스", "📉"),
                "bollinger_touch": ("🎯 볼린저밴드", "🎪"),
                "ma20_touch": ("📏 20일선 터치", "📊"),
                "rsi_condition": ("⚡ RSI 신호", "🔥"),
                "volume_surge": ("🌊 거래량 급증", "💥"),
                "macd_golden_cross": ("✨ MACD 골든크로스", "🚀"),
                "support_resistance_break": ("🔓 돌파 신호", "💪")
            }
            
            kor_name, emoji = condition_info.get(name, (name, "📊"))
            is_last = i == len(conditions) - 1
            
            message += f"{'' if is_last else ''} {emoji} <b>{kor_name}</b>\n"
            message += f"{'' if is_last else ''}  💬 {details}\n"
            
            # 과거 사례 5일 주가 표시
            five_day_prices = condition.get("five_day_prices", [])
            reference_date = condition.get("reference_date")
            
            if reference_date and five_day_prices:
                message += f"{'' if is_last else ''}  📅 <b>과거 참조</b>: <code>{reference_date}</code>\n"
                message += f"{'' if is_last else ''}  📈 <b>이후 5일 주가</b>:\n"
                
                for j, price_data in enumerate(five_day_prices):
                    date_str = price_data["date"]
                    close_price = price_data["close"]
                    
                    # 날짜 포맷팅 (MM-DD 형식으로)
                    try:
                        formatted_date = date_str[5:].replace('-', '/')  # YYYY-MM-DD -> MM/DD
                    except:
                        formatted_date = date_str
                    
                    inner_prefix = "└" if j == len(five_day_prices) - 1 else "├"
                    message += f"{'' if is_last else ''}     {inner_prefix} <code>{formatted_date}</code>: <b>{close_price:,}원</b>\n"
                
                # 📊 수익률 계산
                if len(five_day_prices) >= 2:
                    first_price = five_day_prices[0]["close"]
                    last_price = five_day_prices[-1]["close"]
                    return_rate = ((last_price - first_price) / first_price) * 100
                    
                    if return_rate > 0:
                        message += f"{'' if is_last else ''}  📊 <b>5일 수익률</b>: <code>+{return_rate:.2f}%</code> 🔥⬆️\n"
                    elif return_rate < 0:
                        message += f"{'' if is_last else ''}  📊 <b>5일 수익률</b>: <code>{return_rate:.2f}%</code> 🧊⬇️\n"
                    else:
                        message += f"{'' if is_last else ''}  📊 <b>5일 수익률</b>: <code>{return_rate:.2f}%</code> ➡️\n"
            else:
                message += f"{'' if is_last else ''}  🔍 <i>과거 참조 데이터 없음</i>\n"
            
            if not is_last:
                message += f"│\n"

        # 🤖 AI 분석 추가
        if llm_analysis:
            message += f"\n🤖 <b>AI 분석 ({self.current_model_type.upper()})</b>\n"
            message += f"┌─────────────────────\n"
            for line in llm_analysis.split('\n'):
                if line.strip():
                    message += f"│ {line.strip()}\n"
            message += f"└─────────────────────\n"

        # 🎯 마무리 멘트
        message += f"\n━━━━━━━━━━━━━━━━━━━\n"
        message += f"🎯 <i>투자 기회를 놓치지 마세요!</i>\n"
        message += f"💪 <i>오늘도 성투하세요! 📈</i>"
        
        return message

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
                # 차트 서비스에 특화된 설정 추출
                personalized_config = {
                    "user_id": user_id,
                    "stocks": [stock["stock_code"] for stock in config.get("stocks", [])],
                    "model_type": config.get("model_type", "hyperclova"),
                    "active_service": config.get("active_services", {}).get("chart_service", 0) == 1
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


# ==================== 싱글톤 서비스 인스턴스 ====================
_chart_service_instance = None

def get_chart_service() -> ChartAnalysisService:
    """차트 서비스 싱글톤 인스턴스 반환"""
    global _chart_service_instance
    if _chart_service_instance is None:
        _chart_service_instance = ChartAnalysisService()
    return _chart_service_instance


# ==================== FastAPI 엔드포인트 ====================

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 - 서비스 초기화 없이 단순 상태만 반환"""
    return {
        "status": "healthy", 
        "service": "Chart Service", 
        "timestamp": datetime.now().isoformat(),
        "message": "Chart Service API server is running"
    }

@app.get("/signal")
async def get_latest_signals():
    """최근 차트 신호 조회 (텔레그램과 동일한 내용)"""
    try:
        chart_service = get_chart_service()
        
        async with chart_service.signal_lock:
            signals = chart_service.latest_signals.copy()
        
        return {
            "success": True,
            "message": "최근 차트 신호 조회 완료",
            "data": {
                "signals": signals,
                "total_count": len(signals),
                "user_id": chart_service.current_user_id,
                "model_type": chart_service.current_model_type,
                "market_hours": chart_service.is_market_hours
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"신호 조회 실패: {str(e)}")

@app.post("/set-user/{user_id}")
async def set_user_context(user_id):
    """사용자 컨텍스트 설정"""
    try:
        chart_service = get_chart_service()
        await chart_service.set_user_id(user_id)
        
        return {
            "success": True,
            "message": f"사용자 컨텍스트 설정 완료: {user_id}",
            "data": {
                "user_id": user_id,
                "stocks_count": len(chart_service.stocks_config),
                "model_type": chart_service.current_model_type,
                "stocks": list(chart_service.stocks_config.keys())
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용자 컨텍스트 설정 실패: {str(e)}")

@app.get("/user-config/{user_id}")
async def get_user_config(user_id):
    """사용자 설정 조회"""
    try:
        chart_service = get_chart_service()
        
        # 요청된 사용자 ID와 현재 설정된 사용자 ID가 다르면 업데이트
        if chart_service.current_user_id != user_id:
            await chart_service.set_user_id(user_id)
        
        return {
            "success": True,
            "message": "사용자 설정 조회 완료",
            "data": {
                "user_id": chart_service.current_user_id,
                "model_type": chart_service.current_model_type,
                "stocks_config": chart_service.stocks_config,
                "stocks_count": len(chart_service.stocks_config),
                "market_hours": chart_service.is_market_hours,
                "service_running": chart_service.is_running
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용자 설정 조회 실패: {str(e)}")

@app.post("/analyze/{stock_code}")
async def analyze_stock(stock_code: str):
    """특정 종목 즉시 분석"""
    try:
        chart_service = get_chart_service()
        
        # 종목이 사용자 설정에 있는지 확인
        if stock_code not in chart_service.stocks_config:
            raise HTTPException(status_code=404, detail=f"종목 {stock_code}이 사용자 설정에 없습니다")
        
        # 차트 데이터 수집
        df = await chart_service.fetch_historical_data(stock_code)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"종목 {stock_code}의 차트 데이터를 찾을 수 없습니다")
        
        # 기술적 지표 계산
        df = await chart_service.calculate_technical_indicators(df)
        
        # 조건 체크
        conditions = await chart_service.check_all_conditions(stock_code, df)
        
        return {
            "success": True,
            "message": f"종목 {stock_code} 분석 완료",
            "data": {
                "stock_code": stock_code,
                "stock_name": chart_service.stocks_config[stock_code].get("name", stock_code),
                "analysis_result": conditions,
                "user_id": chart_service.current_user_id,
                "model_type": chart_service.current_model_type
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"종목 분석 실패: {str(e)}")

# === 스케줄링 관련 변수 ===
last_execution_time = None



# 서비스 인스턴스 생성 (지연 초기화)
disclosure_service = None
latest_signal_message = None  # 최근 알람 메시지 저장



async def save_latest_signal(message: str):
    """최근 알람 메시지 저장"""
    global latest_signal_message
    latest_signal_message = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "service": "disclosure"
    }
    
def should_execute_now() -> Tuple[bool, str]:
    """현재 실행할 시간인지 판단 (차트 서비스 전용 로직)"""
    global last_execution_time
    
    now = datetime.now()
    
    # 첫 실행인 경우
    if last_execution_time is None:
        return True, "첫 실행"
    
    # 마지막 실행으로부터 경과 시간 계산
    time_diff = (now - last_execution_time).total_seconds()
    
    # 시장 상태별 실행 간격 확인
    is_market, market_status = get_chart_service()._check_market_hours()
    
    if market_status == "market_hours":
        # 장중: 5분 간격
        required_interval = 300  # 5분 = 300초
        interval_name = "장중 5분 간격"
    elif market_status == "after_market":
        # 장후: 1시간 간격 (1회 분석 후)
        required_interval = 3600  # 1시간 = 3600초
        interval_name = "장후 1시간 간격"
    elif market_status == "weekend":
        # 주말: 24시간 간격
        required_interval = 24 * 3600  # 24시간
        interval_name = "주말 24시간 간격"
    else:  # pre_market
        # 장전: 1시간 간격
        required_interval = 3600  # 1시간
        interval_name = "장전 1시간 간격"
    
    if time_diff >= required_interval:
        return True, f"{interval_name} - 마지막 실행: {last_execution_time.strftime('%H:%M')}"
    else:
        remaining = int(required_interval - time_diff)
        return False, f"{interval_name} - {remaining}초 후 실행 가능}"

async def execute_chart_analysis() -> Dict:
    """차트 분석 실행 (오케스트레이터 호출용)"""
    global last_execution_time
    global latest_signal_message
    
    try:
        logger.info("🚀 오케스트레이터 신호로 차트 분석 실행 시작")
        
        chart_service = get_chart_service()
        
        # 현재 시장 상태 확인
        is_market, market_status = chart_service._check_market_hours()
        
        if market_status == "market_hours":
            # 장중: 전체 종목 조건 체크
            await chart_service._check_all_stocks_conditions()
            
        elif market_status == "after_market":
            # 장후: 1회 분석 실행
            await chart_service._check_all_stocks_conditions()
            
        elif market_status == "weekend":
            # 주말: 1회 분석 실행
            await chart_service._check_all_stocks_conditions()
            
        else:  # pre_market
            # 장전: 기본 분석 실행
            await chart_service._check_all_stocks_conditions()
        
        # 실행 시간 업데이트
        last_execution_time = datetime.now()
        
        result = {
            "success": True,
            "market_status": market_status,
            "stocks_analyzed": len(chart_service.stocks_config),
            "execution_time": last_execution_time.isoformat(),
            "telegram_message": latest_signal_message.get("message") if latest_signal_message else None # Add this line
        }
        
        logger.info(f"✅ 차트 분석 완료: {market_status} 모드, {len(chart_service.stocks_config)}개 종목")
        return result
        
    except Exception as e:
        logger.error(f"❌ 차트 분석 실행 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/execute")
async def execute_chart_analysis_endpoint(request: Request):
    """차트 분석 실행 - 사용자별 동적 처리"""
    try:
        # Header에서 user_id 추출 (문자열로 처리)
        user_id = request.headers.get("X-User-ID", "1")
        
        # 서비스 인스턴스의 user_id 동적 업데이트
        chart_service = get_chart_service()
        if chart_service.current_user_id != user_id:
            await chart_service.set_user_id(user_id)
            logger.info(f"🔄 사용자 컨텍스트 변경: {user_id}")
        
        # 차트 분석 실행
        result = await execute_chart_analysis()
        return result
        
    except Exception as e:
        logger.error(f"❌ 차트 분석 실행 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/check-schedule")
async def check_schedule():
    """오케스트레이터 체크 신호 수신 - 독립적으로 실행 시간 판단"""
    try:
        should_run, reason = should_execute_now()
        
        if should_run:
            # 실행 조건 만족 시 차트 분석 실행
            result = await execute_chart_analysis()
            
            if result["success"]:
                return {
                    "executed": True,
                    "message": f"차트 분석 실행 완료 - {reason}",
                    "details": result
                }
            else:
                return {
                    "executed": False,
                    "message": f"차트 분석 실행 실패 - {result.get('error', 'Unknown')}",
                    "reason": reason
                }
        else:
            return {
                "executed": False,
                "message": reason,
                "next_execution": "시장 상태별 간격"
            }
        
    except Exception as e:
        logger.error(f"❌ 스케줄 체크 실패: {e}")
        return {
            "executed": False,
            "message": f"스케줄 체크 오류: {str(e)}"
        }

async def main():
    """메인 실행 함수 (분석 서비스)"""
    try:
        # 차트 분석 서비스 실행
        chart_service = ChartAnalysisService()
        await chart_service.run_service()

    except KeyboardInterrupt:
        print("서비스 중단")
    except Exception as e:
        print(f"서비스 실행 실패: {e}")


def run_fastapi():
    """FastAPI 서버 실행"""
    uvicorn.run(app, host="0.0.0.0", port=8003)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Chart Analysis Service")
    parser.add_argument("--mode", choices=["service", "api"], default="api", 
                       help="실행 모드: service(분석 서비스) 또는 api(FastAPI 서버)")
    args = parser.parse_args()
    
    try:
        if args.mode == "service":
            # 분석 서비스 모드
            asyncio.run(main())
        else:
            # FastAPI 서버 모드
            run_fastapi()
    finally:
        # 프로그램 종료 시 모든 MySQL 클라이언트 정리
        cleanup_mysql_client()
