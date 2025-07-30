"""
미래에셋 수급 데이터 3개월치 채우기 스크립트
- pykrx API를 사용하여 미래에셋(006800)의 수급 데이터 수집
- eod_flows, program_flows, pattern_signals 테이블에 데이터 저장
- 프로그램 매매 데이터는 시뮬레이션으로 생성
"""

import asyncio
import json
import logging
import os
import sys
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import numpy as np
import pymysql.cursors

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.apis.pykrx_api import PyKRXAPIClient
from config.env_local import get_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class MiraeFlowDataPopulator:
    """미래에셋 수급 데이터 채우기 클래스"""

    def __init__(self):
        """초기화"""
        self.config = get_config()
        self.mysql_client = get_mysql_client()
        self.pykrx_client = PyKRXAPIClient()
        self.stock_code = "006800"  # 미래에셋증권
        self.stock_name = "미래에셋증권"
        
        logger.info(f"미래에셋 수급 데이터 채우기 시작: {self.stock_code}")

    def reset_mysql_connection(self):
        """MySQL 연결 풀 재설정"""
        try:
            # 기존 연결 풀 정리
            if hasattr(self.mysql_client, 'pool'):
                self.mysql_client.pool.close()
            
            # 새로운 연결 풀 생성
            self.mysql_client = get_mysql_client()
            logger.info("MySQL 연결 풀 재설정 완료")
        except Exception as e:
            logger.error(f"MySQL 연결 풀 재설정 실패: {e}")

    async def initialize_database(self):
        """데이터베이스 초기화"""
        try:
            # flow_analysis_schema.sql 실행
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
                
                logger.info("수급 분석 데이터베이스 초기화 완료")
            else:
                logger.warning("스키마 파일이 없습니다")

        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    async def get_trading_dates(self, days: int = 90) -> List[str]:
        """거래일 목록 조회"""
        try:
            # 3개월 전부터 현재까지의 거래일 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 30)  # 휴장일 고려하여 여유분 추가
            
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")
            
            # pykrx를 사용하여 거래일 목록 조회
            from pykrx import stock
            
            # KOSPI 전체 종목의 거래일 조회 (미래에셋 포함)
            trading_dates = stock.get_market_ohlcv_by_date(
                start_date_str, end_date_str, self.stock_code
            )
            
            # 거래일 목록 추출 (최신순)
            date_list = []
            for date in trading_dates.index:
                if hasattr(date, 'strftime'):
                    date_str = date.strftime("%Y-%m-%d")
                else:
                    date_str = str(date)
                    if len(date_str) == 8:  # YYYYMMDD 형식인 경우
                        date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                
                date_list.append(date_str)
            
            # 최신순으로 정렬하고 요청한 일수만큼만 반환
            date_list = sorted(date_list, reverse=True)[:days]
            
            logger.info(f"거래일 {len(date_list)}개 조회 완료")
            return date_list

        except Exception as e:
            logger.error(f"거래일 조회 실패: {e}")
            return []

    async def collect_eod_flow_data(self, target_date: str) -> Optional[Dict]:
        """특정 날짜의 EOD 수급 데이터 수집"""
        try:
            # pykrx API로 수급 데이터 조회
            flow_data = self.pykrx_client.get_eod_flow_data(self.stock_code, target_date)
            
            if flow_data.get("status") != "success":
                logger.warning(f"EOD 데이터 조회 실패: {target_date} - {flow_data.get('message')}")
                return None

            data = flow_data["data"]
            
            return {
                "trade_date": target_date,
                "ticker": self.stock_code,
                "inst_net": data["inst_net"],
                "foreign_net": data["foreign_net"],
                "individual_net": data["individual_net"],
                "total_value": data["total_value"],
                "close_price": data["close_price"],
                "volume": data["volume"]
            }

        except Exception as e:
            logger.error(f"EOD 데이터 수집 실패: {target_date} - {e}")
            return None

    async def save_eod_flow_data(self, flow_data: Dict):
        """EOD 수급 데이터 저장"""
        try:
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
                    flow_data["trade_date"],
                    flow_data["ticker"],
                    flow_data["inst_net"],
                    flow_data["foreign_net"],
                    flow_data["individual_net"],
                    flow_data["total_value"],
                    flow_data["close_price"],
                    flow_data["volume"]
                ))
                conn.commit()

            logger.info(f"EOD 데이터 저장 완료: {flow_data['trade_date']}")

        except Exception as e:
            logger.error(f"EOD 데이터 저장 실패: {flow_data['trade_date']} - {e}")

    async def generate_program_flow_data(self, trade_date: str, base_volume: int, close_price: float) -> List[Dict]:
        """프로그램 매매 데이터 시뮬레이션 생성"""
        try:
            # 해당 날짜의 장 시간 (09:00-15:30)
            market_hours = []
            current_time = datetime.strptime(f"{trade_date} 09:00:00", "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(f"{trade_date} 15:30:00", "%Y-%m-%d %H:%M:%S")
            
            while current_time <= end_time:
                market_hours.append(current_time)
                current_time += timedelta(minutes=5)  # 5분 간격
            
            # 프로그램 매매 데이터 생성
            program_data = []
            
            for ts in market_hours:
                # 랜덤한 프로그램 매매량 생성 (기본 거래량의 1-10% 범위)
                volume_ratio = random.uniform(0.01, 0.10)
                net_volume = int(base_volume * volume_ratio * random.choice([-1, 1]))  # 매수/매도 랜덤
                
                # 가격 변동 (종가 대비 ±3% 범위)
                price_change = random.uniform(-0.03, 0.03)
                price = close_price * (1 + price_change)
                
                # 매매 방향 결정
                side = "BUY" if net_volume > 0 else "SELL"
                net_value = abs(net_volume) * price
                
                program_data.append({
                    "ts": ts,
                    "ticker": self.stock_code,
                    "net_volume": net_volume,
                    "net_value": int(net_value),
                    "side": side,
                    "price": round(price, 2),
                    "total_volume": base_volume
                })
            
            return program_data

        except Exception as e:
            logger.error(f"프로그램 매매 데이터 생성 실패: {trade_date} - {e}")
            return []

    async def save_program_flow_data(self, program_data: List[Dict]):
        """프로그램 매매 데이터 저장"""
        try:
            query = """
                INSERT INTO program_flows (
                    ts, ticker, net_volume, net_value, side, price, total_volume
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    net_volume = VALUES(net_volume),
                    net_value = VALUES(net_value),
                    side = VALUES(side),
                    price = VALUES(price),
                    total_volume = VALUES(total_volume)
            """

            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                for data in program_data:
                    cursor.execute(query, (
                        data["ts"],
                        data["ticker"],
                        data["net_volume"],
                        data["net_value"],
                        data["side"],
                        data["price"],
                        data["total_volume"]
                    ))
                conn.commit()

            logger.info(f"프로그램 매매 데이터 저장 완료: {len(program_data)}개")

        except Exception as e:
            logger.error(f"프로그램 매매 데이터 저장 실패: {e}")

    async def generate_pattern_signals(self, trade_date: str, eod_data: Dict, program_data: List[Dict]):
        """패턴 신호 생성 및 저장"""
        try:
            # 1. 기관 매수 신호 체크 (최근 5일 중 3일 이상 기관 순매수)
            inst_buy_days = await self.check_institutional_buy_days(trade_date)
            daily_inst_strong = inst_buy_days >= 3
            
            # 2. 프로그램 매매 신호 체크 (30일 평균 대비 2.5배 이상)
            prog_volume = sum(abs(p["net_volume"]) for p in program_data)
            prog_ratio = await self.calculate_program_ratio(trade_date, prog_volume)
            rt_prog_strong = prog_ratio >= 2.5
            
            # 3. 복합 신호 (둘 다 만족)
            composite_strong = daily_inst_strong and rt_prog_strong
            
            # 4. 트리거 데이터 생성
            trigger_data = {
                "inst_buy_days": inst_buy_days,
                "prog_volume": prog_volume,
                "prog_ratio": prog_ratio,
                "close_price": eod_data["close_price"],
                "volume": eod_data["volume"]
            }
            
            # 5. 패턴 신호 저장
            await self.save_pattern_signal(
                trade_date, daily_inst_strong, rt_prog_strong, 
                composite_strong, inst_buy_days, prog_volume, 
                prog_ratio, trigger_data
            )
            
            logger.info(f"패턴 신호 생성 완료: {trade_date} - 기관:{daily_inst_strong}, 프로그램:{rt_prog_strong}, 복합:{composite_strong}")

        except Exception as e:
            logger.error(f"패턴 신호 생성 실패: {trade_date} - {e}")

    async def check_institutional_buy_days(self, target_date: str) -> int:
        """최근 5일 중 기관 순매수일 수 계산"""
        try:
            # 최근 5일 데이터 조회
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("""
                    SELECT trade_date, inst_net 
                    FROM eod_flows 
                    WHERE ticker = %s AND trade_date <= %s
                    ORDER BY trade_date DESC 
                    LIMIT 5
                """, (self.stock_code, target_date))
                
                results = cursor.fetchall()
                
                # 기관 순매수일 수 계산
                positive_days = sum(1 for row in results if row["inst_net"] > 0)
                return positive_days
                
        except Exception as e:
            logger.error(f"기관 매수일 수 계산 실패: {e}")
            return 0

    async def calculate_program_ratio(self, target_date: str, current_volume: int) -> float:
        """프로그램 매매 비율 계산 (30일 평균 대비)"""
        try:
            # 30일 평균 프로그램 매매량 계산
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("""
                    SELECT AVG(total_volume) as avg_volume
                    FROM program_flows 
                    WHERE ticker = %s AND ts < %s
                    AND ts >= DATE_SUB(%s, INTERVAL 30 DAY)
                """, (self.stock_code, f"{target_date} 00:00:00", target_date))
                
                result = cursor.fetchone()
                avg_volume = result["avg_volume"] if result["avg_volume"] else 1000000
                
                # 비율 계산
                ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                return round(ratio, 2)
                
        except Exception as e:
            logger.error(f"프로그램 매매 비율 계산 실패: {e}")
            return 1.0

    async def save_pattern_signal(self, trade_date: str, daily_inst_strong: bool, 
                                rt_prog_strong: bool, composite_strong: bool,
                                inst_buy_days: int, prog_volume: int, 
                                prog_ratio: float, trigger_data: Dict):
        """패턴 신호 저장"""
        try:
            query = """
                INSERT INTO pattern_signals (
                    ref_time, ticker, daily_inst_strong, rt_prog_strong,
                    inst_buy_days, prog_volume, prog_ratio, trigger_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    daily_inst_strong = VALUES(daily_inst_strong),
                    rt_prog_strong = VALUES(rt_prog_strong),
                    inst_buy_days = VALUES(inst_buy_days),
                    prog_volume = VALUES(prog_volume),
                    prog_ratio = VALUES(prog_ratio),
                    trigger_data = VALUES(trigger_data),
                    updated_at = CURRENT_TIMESTAMP
            """

            ref_time = datetime.strptime(f"{trade_date} 15:30:00", "%Y-%m-%d %H:%M:%S")
            
            # Decimal 타입을 float로 변환
            if isinstance(prog_ratio, (int, float)):
                prog_ratio = float(prog_ratio)
            else:
                prog_ratio = 1.0
            
            # trigger_data의 Decimal 값들을 float로 변환
            cleaned_trigger_data = {}
            for key, value in trigger_data.items():
                if hasattr(value, '__float__'):
                    cleaned_trigger_data[key] = float(value)
                else:
                    cleaned_trigger_data[key] = value
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    ref_time,
                    self.stock_code,
                    daily_inst_strong,
                    rt_prog_strong,
                    inst_buy_days,
                    prog_volume,
                    prog_ratio,
                    json.dumps(cleaned_trigger_data, ensure_ascii=False, default=str)
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"패턴 신호 저장 실패: {e}")

    async def populate_flow_data(self, days: int = 90):
        """수급 데이터 채우기 메인 함수"""
        try:
            logger.info(f"미래에셋 수급 데이터 {days}일 채우기 시작")
            
            # 1. 데이터베이스 초기화
            await self.initialize_database()
            
            # 2. 거래일 목록 조회
            trading_dates = await self.get_trading_dates(days)
            if not trading_dates:
                logger.error("거래일 목록을 가져올 수 없습니다")
                return
            
            # 3. 데이터 수집 및 저장
            eod_success_count = 0
            eod_fail_count = 0
            program_success_count = 0
            pattern_success_count = 0
            
            for trade_date in trading_dates:
                try:
                    # EOD 데이터 수집
                    flow_data = await self.collect_eod_flow_data(trade_date)
                    
                    if flow_data:
                        # EOD 데이터 저장
                        try:
                            await self.save_eod_flow_data(flow_data)
                            eod_success_count += 1
                        except Exception as e:
                            if "연결 풀이 닫혔습니다" in str(e):
                                self.reset_mysql_connection()
                                await self.save_eod_flow_data(flow_data)
                                eod_success_count += 1
                            else:
                                raise e
                        
                        # 프로그램 매매 데이터 생성 및 저장
                        base_volume = flow_data.get("volume", 1000000)
                        close_price = flow_data.get("close_price", 5000)
                        program_data = await self.generate_program_flow_data(trade_date, base_volume, close_price)
                        
                        if program_data:
                            try:
                                await self.save_program_flow_data(program_data)
                                program_success_count += 1
                            except Exception as e:
                                if "연결 풀이 닫혔습니다" in str(e):
                                    self.reset_mysql_connection()
                                    await self.save_program_flow_data(program_data)
                                    program_success_count += 1
                                else:
                                    raise e
                            
                            # 패턴 신호 생성 및 저장
                            try:
                                await self.generate_pattern_signals(trade_date, flow_data, program_data)
                                pattern_success_count += 1
                            except Exception as e:
                                if "연결 풀이 닫혔습니다" in str(e):
                                    self.reset_mysql_connection()
                                    await self.generate_pattern_signals(trade_date, flow_data, program_data)
                                    pattern_success_count += 1
                                else:
                                    raise e
                        
                        logger.info(f"✅ {trade_date} 데이터 처리 완료")
                    else:
                        eod_fail_count += 1
                        logger.warning(f"❌ {trade_date} 데이터 수집 실패")
                    
                    # API 호출 제한 고려하여 잠시 대기
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    eod_fail_count += 1
                    logger.error(f"❌ {trade_date} 처리 실패: {e}")
                    continue
            
            # 4. 결과 요약
            logger.info("=" * 50)
            logger.info("📊 미래에셋 수급 데이터 채우기 완료")
            logger.info(f"📅 처리 기간: {days}일")
            logger.info(f"✅ EOD 성공: {eod_success_count}일")
            logger.info(f"❌ EOD 실패: {eod_fail_count}일")
            logger.info(f"⚡ 프로그램 데이터: {program_success_count}일")
            logger.info(f"🎯 패턴 신호: {pattern_success_count}일")
            logger.info(f"📈 성공률: {eod_success_count/(eod_success_count+eod_fail_count)*100:.1f}%")
            logger.info("=" * 50)
            
            # 5. 데이터 검증
            await self.verify_data_integrity()
            
        except Exception as e:
            logger.error(f"수급 데이터 채우기 실패: {e}")
            raise

    async def verify_data_integrity(self):
        """데이터 무결성 검증"""
        try:
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
                # EOD 데이터 개수 확인
                cursor.execute("""
                    SELECT COUNT(*) as count, 
                           MIN(trade_date) as min_date, 
                           MAX(trade_date) as max_date
                    FROM eod_flows 
                    WHERE ticker = %s
                """, (self.stock_code,))
                eod_result = cursor.fetchone()
                
                # 프로그램 매매 데이터 개수 확인
                cursor.execute("""
                    SELECT COUNT(*) as count,
                           MIN(ts) as min_ts,
                           MAX(ts) as max_ts
                    FROM program_flows 
                    WHERE ticker = %s
                """, (self.stock_code,))
                prog_result = cursor.fetchone()
                
                # 패턴 신호 데이터 개수 확인
                cursor.execute("""
                    SELECT COUNT(*) as count,
                           MIN(ref_time) as min_time,
                           MAX(ref_time) as max_time
                    FROM pattern_signals 
                    WHERE ticker = %s
                """, (self.stock_code,))
                pattern_result = cursor.fetchone()
                
                logger.info("=" * 30)
                logger.info("🔍 데이터 무결성 검증 결과")
                logger.info(f"📊 EOD 데이터: {eod_result['count']}개")
                logger.info(f"📅 EOD 기간: {eod_result['min_date']} ~ {eod_result['max_date']}")
                logger.info(f"⚡ 프로그램 데이터: {prog_result['count']}개")
                logger.info(f"⏰ 프로그램 기간: {prog_result['min_ts']} ~ {prog_result['max_ts']}")
                logger.info(f"🎯 패턴 신호: {pattern_result['count']}개")
                logger.info(f"📈 패턴 기간: {pattern_result['min_time']} ~ {pattern_result['max_time']}")
                logger.info("=" * 30)
                
        except Exception as e:
            logger.error(f"데이터 무결성 검증 실패: {e}")

async def main():
    """메인 함수"""
    print("""
    🚀 미래에셋 수급 데이터 채우기
    ================================
    
    기능:
    - 미래에셋(006800) 3개월치 수급 데이터 수집
    - EOD 데이터: pykrx API 사용
    - 프로그램 매매 데이터: 시뮬레이션 생성
    - 패턴 신호: 기관+프로그램 복합 신호 생성
    - 데이터베이스 저장 및 무결성 검증
    
    기간: 3개월 (90일)
    테이블: eod_flows, program_flows, pattern_signals
    """)

    try:
        populator = MiraeFlowDataPopulator()
        await populator.populate_flow_data(days=90)  # 3개월
        
        print("\n✅ 미래에셋 수급 데이터 채우기 완료!")
        
    except KeyboardInterrupt:
        print("\n❌ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 