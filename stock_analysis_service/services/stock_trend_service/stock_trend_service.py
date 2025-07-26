"""
주가 추이 분석 및 알림 서비스
pykrx를 사용하여 주가 데이터를 조회하고 텔레그램 알림을 전송
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import traceback
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import numpy as np

# pykrx 라이브러리 임포트
try:
    from pykrx import stock
except ImportError:
    print("pykrx 라이브러리가 설치되지 않았습니다. pip install pykrx 를 실행하세요.")
    sys.exit(1)

# 프로젝트 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.env_local import get_config
from shared.apis.telegram_api import TelegramBotClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_trend_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StockTrendService:
    """주가 추이 분석 및 알림 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        self.config = get_config()
        self.telegram_client = TelegramBotClient()
        
        # 기본 설정
        self.analysis_days = 5  # 분석 기간 (5일)
        self.market_timezone = 'Asia/Seoul'
        
        logger.info("주가 추이 분석 서비스 초기화 완료")
    
    def get_business_days(self, days: int = 5) -> List[str]:
        """
        최근 영업일 리스트 반환
        
        Args:
            days: 조회할 영업일 수
            
        Returns:
            List[str]: 영업일 리스트 (YYYYMMDD 형식)
        """
        try:
            # 현재 날짜에서 시작하여 영업일 찾기
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)  # 여유분 확보
            
            # 영업일 리스트 조회
            business_days = stock.get_previous_business_days(
                year=end_date.year,
                month=end_date.month,
                prev_count=days
            )
            
            # 최근 5일 반환
            return business_days[-days:]
            
        except Exception as e:
            logger.error(f"영업일 조회 실패: {e}")
            # 대안: 직접 계산
            business_days = []
            current_date = datetime.now()
            
            while len(business_days) < days:
                # 주말 제외 (토요일: 5, 일요일: 6)
                if current_date.weekday() < 5:
                    business_days.append(current_date.strftime('%Y%m%d'))
                current_date = current_date - timedelta(days=1)
            
            return list(reversed(business_days))
    
    def get_stock_ohlcv_data(self, stock_code: str, days: int = 5) -> Optional[pd.DataFrame]:
        """
        종목의 OHLCV 데이터 조회
        
        Args:
            stock_code: 종목 코드
            days: 조회 기간 (일)
            
        Returns:
            pd.DataFrame: OHLCV 데이터 또는 None
        """
        try:
            # 영업일 리스트 조회
            business_days = self.get_business_days(days)
            
            if not business_days:
                logger.error("영업일 조회 실패")
                return None
            
            start_date = business_days[0]
            end_date = business_days[-1]
            
            logger.info(f"OHLCV 데이터 조회: {stock_code} ({start_date} ~ {end_date})")
            
            # OHLCV 데이터 조회
            df = stock.get_market_ohlcv(start_date, end_date, stock_code)
            
            if df.empty:
                logger.warning(f"OHLCV 데이터가 없습니다: {stock_code}")
                return None
            
            # 데이터 정리
            df = df.sort_index()  # 날짜 순으로 정렬
            
            # 등락률 계산
            df['등락률'] = df['등락률'].fillna(0.0)
            
            # 거래대금이 있는 경우에만 변환
            if '거래대금' in df.columns:
                df['거래대금_억원'] = df['거래대금'] / 100000000
            else:
                # 거래대금 = 거래량 * 평균가(시가+고가+저가+종가)/4 로 추정
                df['평균가'] = (df['시가'] + df['고가'] + df['저가'] + df['종가']) / 4
                df['거래대금'] = df['거래량'] * df['평균가']
                df['거래대금_억원'] = df['거래대금'] / 100000000
            
            # 거래량을 만주 단위로 변환
            df['거래량_만주'] = df['거래량'] / 10000
            
            logger.info(f"OHLCV 데이터 조회 완료: {len(df)}일")
            return df
            
        except Exception as e:
            logger.error(f"OHLCV 데이터 조회 실패: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def get_stock_name(self, stock_code: str) -> str:
        """
        종목명 조회
        
        Args:
            stock_code: 종목 코드
            
        Returns:
            str: 종목명
        """
        try:
            stock_name = stock.get_market_ticker_name(stock_code)
            return stock_name if stock_name else stock_code
        except Exception as e:
            logger.error(f"종목명 조회 실패: {e}")
            return stock_code
    
    def analyze_stock_trend(self, stock_code: str, days: int = 5) -> Optional[Dict]:
        """
        주가 추이 분석
        
        Args:
            stock_code: 종목 코드
            days: 분석 기간 (일)
            
        Returns:
            Dict: 분석 결과 또는 None
        """
        try:
            # 종목명 조회
            stock_name = self.get_stock_name(stock_code)
            
            # OHLCV 데이터 조회
            df = self.get_stock_ohlcv_data(stock_code, days)
            
            if df is None or df.empty:
                logger.error(f"주가 데이터 조회 실패: {stock_code}")
                return None
            
            # index가 datetime인지 확인 후 변환
            # Index의 strftime 오류 방지: list로 변환 후 datetime 객체로 처리
            idx_list = list(df.index)
            start_date = idx_list[0]
            end_date = idx_list[-1]
            if isinstance(start_date, (np.datetime64, pd.Timestamp)):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, (np.datetime64, pd.Timestamp)):
                end_date = pd.to_datetime(end_date)
            analysis = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'analysis_period': days,
                'start_date': start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date),
                'end_date': end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date),
                'current_price': int(df.iloc[-1]['종가']),
                'previous_price': int(df.iloc[-2]['종가']) if len(df) > 1 else int(df.iloc[-1]['시가']),
                'daily_data': [],
                'summary': {}
            }
            
            # 일별 데이터 정리
            for date, row in df.iterrows():
                date_val = date
                # strftime은 datetime류에서만 사용
                if isinstance(date_val, (pd.Timestamp, np.datetime64)):
                    date_val = pd.to_datetime(date_val)
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)
                daily_info = {
                    'date': date_str,
                    'open': int(row['시가']),
                    'high': int(row['고가']),
                    'low': int(row['저가']),
                    'close': int(row['종가']),
                    'volume': int(row['거래량']),
                    'volume_man': float(round(float(row['거래량_만주']), 1)) if bool(pd.notnull(row['거래량_만주'])) else 0.0,
                    'trading_value': int(row['거래대금']),
                    'trading_value_eok': float(round(float(row['거래대금_억원']), 1)) if bool(pd.notnull(row['거래대금_억원'])) else 0.0,
                    'change_rate': float(round(float(row['등락률']), 2)) if bool(pd.notnull(row['등락률'])) else 0.0
                }
                analysis['daily_data'].append(daily_info)
            
            # 요약 통계 계산
            total_change = ((analysis['current_price'] - analysis['previous_price']) / analysis['previous_price']) * 100 if analysis['previous_price'] != 0 else 0.0
            avg_volume = float(df['거래량_만주'].mean()) if '거래량_만주' in df.columns else 0.0
            avg_trading_value = float(df['거래대금_억원'].mean()) if '거래대금_억원' in df.columns else 0.0
            max_change = float(df['등락률'].max()) if '등락률' in df.columns else 0.0
            min_change = float(df['등락률'].min()) if '등락률' in df.columns else 0.0
            volatility = float(df['등락률'].std()) if '등락률' in df.columns else 0.0
            
            analysis['summary'] = {
                'total_change_rate': round(total_change, 2),
                'avg_volume_man': round(avg_volume, 1),
                'avg_trading_value_eok': round(avg_trading_value, 1),
                'max_daily_change': round(max_change, 2),
                'min_daily_change': round(min_change, 2),
                'volatility': round(volatility, 2)
            }
            
            logger.info(f"주가 추이 분석 완료: {stock_name} ({stock_code})")
            return analysis
            
        except Exception as e:
            logger.error(f"주가 추이 분석 실패: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def format_trend_message(self, analysis: Dict) -> str:
        """
        텔레그램 알림 메시지 포맷팅
        
        Args:
            analysis: 주가 분석 결과
            
        Returns:
            str: 포맷팅된 메시지
        """
        try:
            stock_name = analysis['stock_name']
            stock_code = analysis['stock_code']
            current_price = analysis['current_price']
            summary = analysis['summary']
            
            # 이모지 선택
            trend_emoji = "📈" if summary['total_change_rate'] > 0 else "📉" if summary['total_change_rate'] < 0 else "➡️"
            
            # 메시지 생성
            message = f"""📊 <b>{stock_name}({stock_code})</b> 5일 주가 추이 분석

💰 <b>현재가</b>: {current_price:,}원
{trend_emoji} <b>기간 수익률</b>: {summary['total_change_rate']:+.2f}%
📈 <b>최고 등락률</b>: {summary['max_daily_change']:+.2f}%
📉 <b>최저 등락률</b>: {summary['min_daily_change']:+.2f}%
🎯 <b>변동성</b>: {summary['volatility']:.2f}%

📊 <b>거래 현황</b>
💎 <b>평균 거래량</b>: {summary['avg_volume_man']:,.1f}만주
💰 <b>평균 거래대금</b>: {summary['avg_trading_value_eok']:,.1f}억원

📅 <b>일별 상세 내역</b>"""
            
            # 일별 데이터 추가
            for i, daily in enumerate(analysis['daily_data']):
                date_str = daily['date']
                close_price = daily['close']
                change_rate = daily['change_rate']
                volume_man = daily['volume_man']
                trading_value_eok = daily['trading_value_eok']
                
                change_emoji = "📈" if change_rate > 0 else "📉" if change_rate < 0 else "➡️"
                
                message += f"""

<b>{date_str}</b>
└ 종가: {close_price:,}원 ({change_emoji} {change_rate:+.2f}%)
└ 거래량: {volume_man:,.1f}만주 | 거래대금: {trading_value_eok:,.1f}억원"""
            
            message += f"""

📈 <b>분석 기간</b>: {analysis['start_date']} ~ {analysis['end_date']}
🕐 <b>분석 시각</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

�� 투자에 참고하시기 바랍니다!"""
            
            return message
            
        except Exception as e:
            logger.error(f"메시지 포맷팅 실패: {e}")
            return f"메시지 생성 중 오류가 발생했습니다: {str(e)}"
    
    def send_trend_alert(self, stock_code: str, days: int = 5) -> bool:
        """
        주가 추이 알림 전송
        
        Args:
            stock_code: 종목 코드
            days: 분석 기간 (일)
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            logger.info(f"주가 추이 알림 전송 시작: {stock_code}")
            
            # 주가 추이 분석
            analysis = self.analyze_stock_trend(stock_code, days)
            
            if not analysis:
                logger.error(f"주가 분석 실패: {stock_code}")
                return False
            
            # 메시지 생성
            message = self.format_trend_message(analysis)
            
            # 텔레그램 전송
            success = self.telegram_client.send_message(message)
            
            if success:
                logger.info(f"주가 추이 알림 전송 완료: {analysis['stock_name']} ({stock_code})")
            else:
                logger.error(f"주가 추이 알림 전송 실패: {stock_code}")
            
            return success
            
        except Exception as e:
            logger.error(f"주가 추이 알림 전송 중 오류: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def send_multiple_trend_alerts(self, stock_codes: List[str], days: int = 5) -> Dict[str, bool]:
        """
        여러 종목의 주가 추이 알림 전송
        
        Args:
            stock_codes: 종목 코드 리스트
            days: 분석 기간 (일)
            
        Returns:
            Dict[str, bool]: 종목별 전송 성공 여부
        """
        results = {}
        
        for stock_code in stock_codes:
            try:
                logger.info(f"주가 추이 알림 전송 중: {stock_code}")
                success = self.send_trend_alert(stock_code, days)
                results[stock_code] = success
                
                # 연속 전송 시 간격 조정
                if len(stock_codes) > 1:
                    import time
                    time.sleep(2)  # 2초 대기
                    
            except Exception as e:
                logger.error(f"주가 추이 알림 전송 실패: {stock_code} - {e}")
                results[stock_code] = False
        
        # 결과 요약
        success_count = sum(1 for success in results.values() if success)
        total_count = len(stock_codes)
        
        logger.info(f"주가 추이 알림 전송 완료: {success_count}/{total_count} 성공")
        
        return results
    
    def get_popular_stocks(self, market: str = "KOSPI", count: int = 10) -> List[str]:
        """
        인기 종목 리스트 조회
        
        Args:
            market: 시장 (KOSPI, KOSDAQ)
            count: 조회할 종목 수
            
        Returns:
            List[str]: 종목 코드 리스트
        """
        try:
            # 시가총액 상위 종목 조회
            today = datetime.now().strftime('%Y%m%d')
            df = stock.get_market_cap(today, market=market)
            
            if df.empty:
                logger.warning(f"시가총액 데이터 조회 실패: {market}")
                # 기본 종목 리스트
                if market == "KOSPI":
                    return ["005930", "000660", "035420", "068270", "207940"]  # 삼성전자, SK하이닉스, 네이버, 셀트리온, 삼성바이오로직스
                else:
                    return ["091990", "240810", "263750", "196170", "328130"]  # 셀트리온헬스케어, 원익IPS, 펄어비스, 알테오젠, 루닛
            
            # 시가총액 상위 종목 선택
            top_stocks = df.nlargest(count, '시가총액')
            return top_stocks.index.tolist()
            
        except Exception as e:
            logger.error(f"인기 종목 조회 실패: {e}")
            # 기본 종목 리스트
            return ["005930", "000660", "035420", "068270", "207940"]
    
    def health_check(self) -> Dict:
        """
        서비스 상태 확인
        
        Returns:
            Dict: 상태 정보
        """
        try:
            # 텔레그램 클라이언트 상태 확인
            telegram_status = self.telegram_client.health_check()
            
            # pykrx 테스트 (삼성전자 현재가 조회)
            test_stock = "005930"
            test_name = self.get_stock_name(test_stock)
            pykrx_status = "healthy" if test_name != test_stock else "unhealthy"
            
            return {
                "status": "healthy" if (telegram_status.get("status") == "healthy" and pykrx_status == "healthy") else "unhealthy",
                "telegram_status": telegram_status,
                "pykrx_status": pykrx_status,
                "analysis_days": self.analysis_days,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"서비스 상태 확인 실패: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 