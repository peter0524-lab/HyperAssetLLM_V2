"""
미래에셋증권 10년간 주가 데이터 분석 스크립트
- 과거 10년간의 주가 데이터에 대해 8가지 기술적 지표 분석
- 분석 결과를 실제 과거 날짜와 시간으로 DB에 저장
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys
import pandas as pd
import numpy as np
import json
import aiohttp
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.apis.kis_api import KISAPIClient
from shared.database.mysql_client import MySQLClient
from config.env_local import get_env_var

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class StockDataCollector:
    """주식 데이터 수집기"""
    
    def __init__(self):
        """초기화"""
        self.app_key = get_env_var("KIS_APP_KEY", "")
        self.app_secret = get_env_var("KIS_APP_SECRET", "")
        self.access_token = None
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
    async def _get_access_token(self):
        """접근 토큰 발급"""
        if self.access_token:
            return
            
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {
            "content-type": "application/json"
        }
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                self.access_token = result.get("access_token")
                
    async def get_daily_price(self, stock_code: str, start_date: str, end_date: str):
        """일별 주가 조회 (FHKST03010100 - 국내주식기간별시세(일/주/월/년))"""
        await self._get_access_token()
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST03010100",
            "custtype": "P"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    result = await response.json()
                    
                    if "output2" not in result:
                        return []
                        
                    daily_data = []
                    for item in result["output2"]:
                        daily_data.append({
                            "date": item.get("stck_bsop_date", ""),
                            "open": float(item.get("stck_oprc", 0)),
                            "high": float(item.get("stck_hgpr", 0)),
                            "low": float(item.get("stck_lwpr", 0)),
                            "close": float(item.get("stck_clpr", 0)),
                            "volume": int(item.get("acml_vol", 0))
                        })
                    
                    return daily_data
                    
        except Exception as e:
            logger.error(f"일별 주가 조회 실패: {e}")
            return []

class TechnicalAnalyzer:
    """기술적 분석 클래스"""
    
    def __init__(self):
        self.mysql_client = MySQLClient()
    
    async def initialize_database(self):
        """차트 분석 테이블 생성"""
        try:
            query = """
            CREATE TABLE IF NOT EXISTS chart_analysis_results (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                date DATE NOT NULL,              
                time TIME NOT NULL,              
                close_price FLOAT DEFAULT NULL,  
                volume BIGINT DEFAULT NULL,      
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
            await self.mysql_client.execute_query_async(query, fetch=False)
            logger.info("차트 분석 테이블 생성 완료")
        except Exception as e:
            logger.error(f"차트 분석 테이블 생성 실패: {e}")
            raise

    def calculate_indicators(self, df):
        """기술적 지표 계산"""
        # 이동평균선
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        # 볼린저 밴드
        df['bb_middle'] = df['ma20']
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # 거래량 이동평균
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        
        return df.fillna(method='ffill').fillna(method='bfill').fillna(0)

    def check_conditions(self, df, i):
        """모든 조건 체크"""
        current = df.iloc[i]
        prev = df.iloc[i-1] if i > 0 else current
        
        conditions = {
            "golden_cross": {
                "condition": False,
                "details": ""
            },
            "dead_cross": {
                "condition": False,
                "details": ""
            },
            "bollinger_touch": {
                "condition": False,
                "details": ""
            },
            "ma20_touch": {
                "condition": False,
                "details": ""
            },
            "rsi_condition": {
                "condition": False,
                "details": ""
            },
            "volume_surge": {
                "condition": False,
                "details": ""
            },
            "macd_golden_cross": {
                "condition": False,
                "details": ""
            },
            "support_resistance_break": {
                "condition": False,
                "details": ""
            }
        }
        
        # 골든크로스 (5일선이 20일선 상향돌파)
        if prev['ma5'] <= prev['ma20'] and current['ma5'] > current['ma20']:
            conditions["golden_cross"] = {
                "condition": True,
                "details": f"5일선({current['ma5']:.2f})이 20일선({current['ma20']:.2f})을 상향돌파"
            }
        
        # 데드크로스 (5일선이 20일선 하향돌파)
        if prev['ma5'] >= prev['ma20'] and current['ma5'] < current['ma20']:
            conditions["dead_cross"] = {
                "condition": True,
                "details": f"5일선({current['ma5']:.2f})이 20일선({current['ma20']:.2f})을 하향돌파"
            }
        
        # 볼린저 밴드 터치
        touch_upper = abs(current['close'] - current['bb_upper']) / current['bb_upper'] < 0.001
        touch_lower = abs(current['close'] - current['bb_lower']) / current['bb_lower'] < 0.001
        if touch_upper or touch_lower:
            conditions["bollinger_touch"] = {
                "condition": True,
                "details": f"{'상단' if touch_upper else '하단'} 밴드 터치"
            }
        
        # 20일선 터치
        if abs(current['close'] - current['ma20']) / current['ma20'] < 0.001:
            conditions["ma20_touch"] = {
                "condition": True,
                "details": f"20일선({current['ma20']:.2f}) 터치"
            }
        
        # RSI 과매수/과매도
        if current['rsi'] >= 70:
            conditions["rsi_condition"] = {
                "condition": True,
                "details": f"RSI 과매수({current['rsi']:.2f})"
            }
        elif current['rsi'] <= 30:
            conditions["rsi_condition"] = {
                "condition": True,
                "details": f"RSI 과매도({current['rsi']:.2f})"
            }
        
        # 거래량 급증 (5일 평균 대비 3배)
        if current['volume'] > current['volume_ma5'] * 3:
            conditions["volume_surge"] = {
                "condition": True,
                "details": f"거래량({current['volume']:.0f}) > 5일평균({current['volume_ma5']:.0f}) × 3"
            }
        
        # MACD 골든크로스
        if prev['macd'] <= prev['signal'] and current['macd'] > current['signal']:
            conditions["macd_golden_cross"] = {
                "condition": True,
                "details": f"MACD({current['macd']:.2f}) > 시그널({current['signal']:.2f})"
            }
        
        # 20일 최고가/최저가 돌파
        high_20d = df['high'].rolling(window=20).max().iloc[i]
        low_20d = df['low'].rolling(window=20).min().iloc[i]
        if current['close'] > high_20d:
            conditions["support_resistance_break"] = {
                "condition": True,
                "details": f"20일 최고가({high_20d:.2f}) 상향돌파"
            }
        elif current['close'] < low_20d:
            conditions["support_resistance_break"] = {
                "condition": True,
                "details": f"20일 최저가({low_20d:.2f}) 하향돌파"
            }
        
        return conditions

    async def save_conditions(self, stock_code: str, date: str, time: str, price: float, 
                            volume: int, conditions: dict):
        """조건 만족 결과를 DB에 저장"""
        try:
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
            
            # JSON으로 변환
            details_json = json.dumps(conditions, ensure_ascii=False)
            
            params = (
                stock_code,
                date,
                time,
                price,
                volume,
                conditions["golden_cross"]["condition"],
                conditions["dead_cross"]["condition"],
                conditions["bollinger_touch"]["condition"],
                conditions["ma20_touch"]["condition"],
                conditions["rsi_condition"]["condition"],
                conditions["volume_surge"]["condition"],
                conditions["macd_golden_cross"]["condition"],
                conditions["support_resistance_break"]["condition"],
                details_json  # JSON 문자열로 저장
            )
            
            await self.mysql_client.execute_query_async(query, params, fetch=False)
            logger.info(f"조건 만족 결과 저장 완료: {date}")
            
        except Exception as e:
            logger.error(f"조건 만족 결과 저장 실패: {e}")

async def get_historical_data(stock_code):
    """10년치 데이터를 3개월 단위로 수집"""
    collector = StockDataCollector()
    all_data = []
    end_date = datetime.now()
    
    # 10년치 데이터를 3개월 단위로 수집
    for i in range(40):  # 10년 = 40분기
        start_date = end_date - timedelta(days=90)
        
        # 날짜 형식 변환
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        logger.info(f"데이터 수집 중: {start_str} ~ {end_str}")
        
        # 해당 기간의 데이터 수집
        data = await collector.get_daily_price(stock_code, start_str, end_str)
        if data:
            all_data.extend(data)
            
        # 다음 구간 준비
        end_date = start_date - timedelta(days=1)
        
        # API 호출 간 딜레이
        await asyncio.sleep(0.5)
    
    return all_data

async def analyze_mirae_asset():
    """미래에셋증권 10년치 주가 분석"""
    try:
        # 서비스 초기화
        analyzer = TechnicalAnalyzer()
        
        # 미래에셋증권 종목코드
        stock_code = "006800"
        
        # DB 테이블 초기화
        await analyzer.initialize_database()
        
        # 10년치 데이터 수집 (3개월 단위로 나눠서)
        historical_data = await get_historical_data(stock_code)
        
        if not historical_data:
            logger.error("주가 데이터 수집 실패")
            return
            
        logger.info(f"주가 데이터 수집 완료: {len(historical_data)}일")
        
        # 데이터프레임 변환
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')  # 날짜순 정렬
        df = df.drop_duplicates(subset=['date'])  # 중복 날짜 제거
        
        logger.info(f"분석 기간: {df['date'].min()} ~ {df['date'].max()}")
        
        # 숫자형 변환
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 기술적 지표 계산
        df = analyzer.calculate_indicators(df)
        
        # 각 날짜별로 조건 체크
        for i in range(len(df)):
            if i < 26:  # 최소 26일의 데이터 필요 (MACD 계산에 26일 필요)
                continue
            
            # 현재 날짜의 데이터
            current_row = df.iloc[i]
            
            # 조건 체크
            conditions = analyzer.check_conditions(df, i)
            
            # 조건 만족 시 DB 저장
            if any(cond["condition"] for cond in conditions.values()):
                await analyzer.save_conditions(
                    stock_code=stock_code,
                    date=current_row['date'].strftime('%Y-%m-%d'),
                    time=current_row['date'].strftime('%H:%M:%S'),
                    price=float(current_row['close']),
                    volume=int(current_row['volume']),
                    conditions=conditions
                )
        
        logger.info("분석 완료")
        
        # 결과 요약 출력
        query = """
        SELECT 
            DATE(date) as date,
            COUNT(*) as total_signals,
            SUM(golden_cross) as golden_cross,
            SUM(dead_cross) as dead_cross,
            SUM(bollinger_touch) as bollinger_touch,
            SUM(ma20_touch) as ma20_touch,
            SUM(rsi_condition) as rsi_condition,
            SUM(volume_surge) as volume_surge,
            SUM(macd_golden_cross) as macd_golden_cross,
            SUM(support_resistance_break) as support_resistance_break
        FROM chart_analysis_results
        WHERE stock_code = %s
        GROUP BY DATE(date)
        ORDER BY date
        """
        
        results = await analyzer.mysql_client.execute_query_async(query, (stock_code,))
        if results:
            logger.info("\n=== 분석 결과 요약 ===")
            logger.info(f"총 분석 기간: {len(results)}일")
            
            total_signals = sum(r['total_signals'] for r in results)
            logger.info(f"총 시그널 발생 횟수: {total_signals}회")
            
            # 조건별 발생 횟수
            condition_counts = {
                'golden_cross': sum(r['golden_cross'] for r in results),
                'dead_cross': sum(r['dead_cross'] for r in results),
                'bollinger_touch': sum(r['bollinger_touch'] for r in results),
                'ma20_touch': sum(r['ma20_touch'] for r in results),
                'rsi_condition': sum(r['rsi_condition'] for r in results),
                'volume_surge': sum(r['volume_surge'] for r in results),
                'macd_golden_cross': sum(r['macd_golden_cross'] for r in results),
                'support_resistance_break': sum(r['support_resistance_break'] for r in results)
            }
            
            logger.info("\n조건별 발생 횟수:")
            for condition, count in condition_counts.items():
                logger.info(f"{condition}: {count}회")
        
    except Exception as e:
        logger.error(f"분석 중 오류 발생: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(analyze_mirae_asset()) 