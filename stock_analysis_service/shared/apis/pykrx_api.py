"""
pykrx API 클라이언트 모듈
일별 기관/외국인/개인 수급 데이터 조회 기능 제공
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    logging.warning("pykrx 라이브러리가 설치되지 않았습니다. 수급 데이터 조회 기능이 제한됩니다.")

# 로깅 설정
logger = logging.getLogger(__name__)


class PyKRXAPIClient:
    """pykrx API 클라이언트 클래스"""

    def __init__(self):
        """PyKRX API 클라이언트 초기화"""
        if not PYKRX_AVAILABLE:
            logger.error("pykrx 라이브러리를 설치해주세요: pip install pykrx")
            raise ImportError("pykrx 라이브러리가 필요합니다")
        
        self.logger = logger

    def get_eod_flow_data(self, stock_code: str, target_date: str = None) -> Dict:
        """
        특정 종목의 일별 수급 데이터 조회 (기관/외국인/개인)
        
        Args:
            stock_code: 종목코드 (6자리)
            target_date: 조회일자 (YYYY-MM-DD, None이면 최근 거래일)
            
        Returns:
            Dict: 수급 데이터
        """
        try:
            if not target_date:
                # 최근 거래일 조회
                target_date = self._get_latest_trading_date()
            else:
                # 날짜 형식 변환 (YYYY-MM-DD -> YYYYMMDD)
                target_date = target_date.replace("-", "")
            
            # 기관 매매 동향 조회
            institutional_data = stock.get_market_trading_value_by_investor(
                target_date, target_date, stock_code
            )
            
            if institutional_data.empty:
                return {
                    "status": "error",
                    "message": "데이터 없음",
                    "stock_code": stock_code,
                    "date": target_date
                }
            
            # 데이터 추출 (단위: 원)
            row = institutional_data.iloc[0]
            columns = institutional_data.columns.tolist()
            
            # 디버깅을 위한 컬럼명 출력
            self.logger.info(f"Available columns: {columns}")
            self.logger.info(f"Row data: {row.to_dict()}")
            
            # 기관 데이터 추출
            inst_net = 0
            foreign_net = 0
            individual_net = 0
            
            # 실제 컬럼명에 맞춰 데이터 추출
            for col in columns:
                col_lower = col.lower()
                value = int(row[col]) if pd.notna(row[col]) else 0
                
                if '기관' in col or 'institutional' in col_lower:
                    inst_net += value
                elif '외국인' in col or 'foreign' in col_lower:
                    foreign_net += value
                elif '개인' in col or 'individual' in col_lower:
                    individual_net += value
            
            # 만약 위 방법으로 데이터를 찾지 못했다면, 다른 방법 시도
            if inst_net == 0 and foreign_net == 0 and individual_net == 0:
                # 컬럼명을 더 구체적으로 찾기
                for col in columns:
                    col_lower = col.lower()
                    value = int(row[col]) if pd.notna(row[col]) else 0
                    
                    # 기관 관련 컬럼
                    if any(keyword in col_lower for keyword in ['기관', 'institutional', '기관투자자']):
                        inst_net += value
                    # 외국인 관련 컬럼
                    elif any(keyword in col_lower for keyword in ['외국인', 'foreign', '외국인투자자']):
                        foreign_net += value
                    # 개인 관련 컬럼
                    elif any(keyword in col_lower for keyword in ['개인', 'individual', '개인투자자']):
                        individual_net += value
            
            # 여전히 데이터를 찾지 못했다면, 직접 컬럼 인덱스로 접근
            if inst_net == 0 and foreign_net == 0 and individual_net == 0:
                try:
                    # 일반적인 pykrx 컬럼 순서: 기관, 외국인, 개인
                    if len(columns) >= 3:
                        inst_net = int(row.iloc[0]) if pd.notna(row.iloc[0]) else 0
                        foreign_net = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0
                        individual_net = int(row.iloc[2]) if pd.notna(row.iloc[2]) else 0
                except Exception as e:
                    self.logger.warning(f"컬럼 인덱스 접근 실패: {e}")
            
            # 총 거래대금 조회
            total_value = 0
            close_price = 0
            volume = 0
            
            try:
                ohlcv = stock.get_market_ohlcv_by_date(target_date, target_date, stock_code)
                if not ohlcv.empty:
                    ohlcv_row = ohlcv.iloc[0]
                    ohlcv_columns = ohlcv.columns.tolist()
                    
                    # 거래대금 컬럼 찾기
                    for col in ohlcv_columns:
                        if '거래대금' in col or 'trading_value' in col.lower():
                            total_value = int(ohlcv_row[col]) if pd.notna(ohlcv_row[col]) else 0
                        elif '종가' in col or 'close' in col.lower():
                            close_price = float(ohlcv_row[col]) if pd.notna(ohlcv_row[col]) else 0
                        elif '거래량' in col or 'volume' in col.lower():
                            volume = int(ohlcv_row[col]) if pd.notna(ohlcv_row[col]) else 0
                    
                    # 만약 찾지 못했다면 인덱스로 접근
                    if total_value == 0 and close_price == 0 and volume == 0:
                        if len(ohlcv_columns) >= 4:  # OHLCV 순서
                            close_price = float(ohlcv_row.iloc[3]) if pd.notna(ohlcv_row.iloc[3]) else 0  # 종가
                            volume = int(ohlcv_row.iloc[4]) if pd.notna(ohlcv_row.iloc[4]) else 0  # 거래량
                            total_value = close_price * volume  # 거래대금 계산
                            
                self.logger.info(f"OHLCV 데이터: close_price={close_price}, volume={volume}, total_value={total_value}")
                
            except Exception as e:
                self.logger.warning(f"OHLCV 데이터 조회 실패: {e}")
            
            # 결과 로깅
            self.logger.info(f"수급 데이터: inst_net={inst_net}, foreign_net={foreign_net}, individual_net={individual_net}")
            
            return {
                "status": "success",
                "stock_code": stock_code,
                "date": target_date,
                "data": {
                    "inst_net": inst_net,
                    "foreign_net": foreign_net,
                    "individual_net": individual_net,
                    "total_value": total_value,
                    "close_price": close_price,
                    "volume": volume
                }
            }
            
        except Exception as e:
            self.logger.error(f"EOD 수급 데이터 조회 실패: {e}")
            return {
                "status": "error",
                "message": str(e),
                "stock_code": stock_code,
                "date": target_date if target_date else "unknown"
            }

    def get_eod_flow_history(self, stock_code: str, days: int = 30) -> Dict:
        """
        특정 종목의 수급 데이터 이력 조회 (최근 N일)
        
        Args:
            stock_code: 종목코드 (6자리)
            days: 조회 일수
            
        Returns:
            Dict: 수급 데이터 이력
        """
        try:
            # 날짜 범위 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # 휴장일 고려하여 여유분 추가
            
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")
            
            # 기관 매매 동향 조회
            institutional_data = stock.get_market_trading_value_by_investor(
                start_date_str, end_date_str, stock_code
            )
            
            if institutional_data.empty:
                return {
                    "status": "error",
                    "message": "데이터 없음",
                    "stock_code": stock_code,
                    "period": days
                }
            
            # OHLCV 데이터 조회
            ohlcv_data = stock.get_market_ohlcv_by_date(
                start_date_str, end_date_str, stock_code
            )
            
            # 데이터 처리
            results = []
            columns = institutional_data.columns.tolist()
            
            for date_idx in institutional_data.index:
                row = institutional_data.loc[date_idx]
                
                # 기관 데이터
                inst_net = 0
                for col in columns:
                    if '기관' in col and '순매수' in col:
                        inst_net += int(row[col]) if pd.notna(row[col]) else 0
                
                # 외국인 데이터
                foreign_net = 0
                for col in columns:
                    if '외국인' in col and '순매수' in col:
                        foreign_net += int(row[col]) if pd.notna(row[col]) else 0
                
                # 개인 데이터
                individual_net = 0
                for col in columns:
                    if '개인' in col and '순매수' in col:
                        individual_net += int(row[col]) if pd.notna(row[col]) else 0
                
                # OHLCV 데이터 매칭
                if date_idx in ohlcv_data.index:
                    ohlcv_row = ohlcv_data.loc[date_idx]
                    close_price = float(ohlcv_row['종가']) if '종가' in ohlcv_data.columns else 0
                    volume = int(ohlcv_row['거래량']) if '거래량' in ohlcv_data.columns else 0
                    total_value = int(ohlcv_row['거래대금']) if '거래대금' in ohlcv_data.columns else 0
                else:
                    close_price = 0
                    volume = 0
                    total_value = 0
                
                # 날짜 포맷 처리 (pandas index가 datetime 객체가 아닐 수 있음)
                if hasattr(date_idx, 'strftime'):
                    date_str = date_idx.strftime("%Y-%m-%d")
                else:
                    # 문자열인 경우 그대로 사용하거나 변환
                    date_str = str(date_idx)
                    if len(date_str) == 8:  # YYYYMMDD 형식인 경우
                        date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                
                results.append({
                    "date": date_str,
                    "inst_net": inst_net,
                    "foreign_net": foreign_net,
                    "individual_net": individual_net,
                    "total_value": total_value,
                    "close_price": close_price,
                    "volume": volume
                })
            
            # 최신순으로 정렬하고 요청한 일수만큼만 반환
            results = sorted(results, key=lambda x: x["date"], reverse=True)[:days]
            
            return {
                "status": "success",
                "stock_code": stock_code,
                "period": days,
                "data": results
            }
            
        except Exception as e:
            logger.error(f"EOD 수급 이력 조회 실패: {e}")
            return {
                "status": "error",
                "message": str(e),
                "stock_code": stock_code,
                "period": days
            }

    def _get_latest_trading_date(self) -> str:
        """최근 거래일 조회"""
        try:
            # 현재 날짜부터 역순으로 최대 10일간 거래일 찾기
            for i in range(10):
                check_date = datetime.now() - timedelta(days=i)
                date_str = check_date.strftime("%Y%m%d")
                
                # 주말 제외
                if check_date.weekday() >= 5:  # 토요일(5), 일요일(6)
                    continue
                
                # 거래 데이터 확인
                try:
                    test_data = stock.get_market_ohlcv_by_date(date_str, date_str, "005930")  # 삼성전자로 테스트
                    if not test_data.empty:
                        return date_str
                except:
                    continue
            
            # 기본값: 어제
            return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            
        except Exception as e:
            logger.error(f"최근 거래일 조회 실패: {e}")
            return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    def get_market_trading_summary(self, target_date: str = None) -> Dict:
        """
        전체 시장 투자주체별 매매 동향 조회
        
        Args:
            target_date: 조회일자 (YYYY-MM-DD, None이면 최근 거래일)
            
        Returns:
            Dict: 시장 전체 매매 동향
        """
        try:
            if not target_date:
                target_date = self._get_latest_trading_date()
            else:
                target_date = target_date.replace("-", "")
            
            # 전체 시장 투자주체별 매매동향
            market_data = stock.get_market_trading_value_by_investor(target_date, target_date)
            
            if market_data.empty:
                return {
                    "status": "error",
                    "message": "시장 데이터 없음",
                    "date": target_date
                }
            
            # 데이터 집계
            row = market_data.iloc[0]
            columns = market_data.columns.tolist()
            
            # 기관 순매수대금
            inst_total = 0
            for col in columns:
                if '기관' in col and '순매수' in col:
                    inst_total += int(row[col]) if pd.notna(row[col]) else 0
            
            # 외국인 순매수대금  
            foreign_total = 0
            for col in columns:
                if '외국인' in col and '순매수' in col:
                    foreign_total += int(row[col]) if pd.notna(row[col]) else 0
            
            # 개인 순매수대금
            individual_total = 0
            for col in columns:
                if '개인' in col and '순매수' in col:
                    individual_total += int(row[col]) if pd.notna(row[col]) else 0
            
            return {
                "status": "success",
                "date": target_date,
                "data": {
                    "institutional_net": inst_total,
                    "foreign_net": foreign_total,
                    "individual_net": individual_total,
                    "total_net": inst_total + foreign_total + individual_total
                }
            }
            
        except Exception as e:
            logger.error(f"시장 매매 동향 조회 실패: {e}")
            return {
                "status": "error",
                "message": str(e),
                "date": target_date if target_date else "unknown"
            }


# 전역 PyKRX API 클라이언트 인스턴스
if PYKRX_AVAILABLE:
    pykrx_client = PyKRXAPIClient()
else:
    pykrx_client = None 