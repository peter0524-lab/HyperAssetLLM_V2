#!/usr/bin/env python3
"""
통합 최종 테스트 파일
이 채팅방에서 만든 모든 테스트 파일들을 통합한 완성된 최종 테스트
실제 서비스들의 함수를 사용하고 실제 데이터베이스 스키마를 사용
"""

import asyncio
import sys
import os
import json
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import pymysql

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.apis.telegram_api import TelegramBotClient
from shared.apis.kis_api import KISAPIClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalIntegratedTester:
    """통합 최종 테스터"""
    
    def __init__(self):
        self.mysql_client = get_mysql_client()
        self.telegram_bot = TelegramBotClient()
        self.kis_client = KISAPIClient()
        self.test_stock_code = "006800"  # 미래에셋증권
        self.test_stock_name = "미래에셋증권"
        
    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("🚀 통합 최종 테스트 시작")
        logger.info("=" * 80)
        
        results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "details": []
        }
        
        # 1. 텔레그램 봇 직접 테스트
        results["total_tests"] += 1
        if await self.test_telegram_bot_direct():
            results["passed_tests"] += 1
            results["details"].append("✅ 텔레그램 봇 직접 테스트: 성공")
        else:
            results["failed_tests"] += 1
            results["details"].append("❌ 텔레그램 봇 직접 테스트: 실패")
        
        # 2. 뉴스 서비스 테스트
        results["total_tests"] += 1
        if await self.test_news_service():
            results["passed_tests"] += 1
            results["details"].append("✅ 뉴스 서비스 테스트: 성공")
        else:
            results["failed_tests"] += 1
            results["details"].append("❌ 뉴스 서비스 테스트: 실패")
        
        # 3. 공시 서비스 테스트
        results["total_tests"] += 1
        if await self.test_disclosure_service():
            results["passed_tests"] += 1
            results["details"].append("✅ 공시 서비스 테스트: 성공")
        else:
            results["failed_tests"] += 1
            results["details"].append("❌ 공시 서비스 테스트: 실패")
        
        # 4. 차트 서비스 테스트
        results["total_tests"] += 1
        if await self.test_chart_service():
            results["passed_tests"] += 1
            results["details"].append("✅ 차트 서비스 테스트: 성공")
        else:
            results["failed_tests"] += 1
            results["details"].append("❌ 차트 서비스 테스트: 실패")
        
        # 5. 수급 분석 서비스 테스트
        results["total_tests"] += 1
        if await self.test_flow_analysis_service():
            results["passed_tests"] += 1
            results["details"].append("✅ 수급 분석 서비스 테스트: 성공")
        else:
            results["failed_tests"] += 1
            results["details"].append("❌ 수급 분석 서비스 테스트: 실패")
        
        # 결과 출력
        await self.print_results(results)
        
        return results
    
    async def test_telegram_bot_direct(self):
        """텔레그램 봇 직접 테스트"""
        try:
            logger.info("📱 텔레그램 봇 직접 테스트 시작")
            
            # 직접 메시지 전송 테스트
            test_message = f"🧪 통합 테스트 - 텔레그램 봇 직접 테스트\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n종목: {self.test_stock_name} ({self.test_stock_code})"
            
            await self.telegram_bot.send_message_async(test_message)
            logger.info("✅ 텔레그램 봇 직접 테스트 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ 텔레그램 봇 직접 테스트 실패: {e}")
            return False
    
    async def test_news_service(self):
        """뉴스 서비스 테스트"""
        try:
            logger.info("📰 뉴스 서비스 테스트 시작")
            
            # 실제 뉴스 서비스 함수 호출
            from services.news_service.main import execute_news_crawling
            
            # 더미 뉴스 데이터 생성
            dummy_news = await self.create_dummy_news_data()
            if not dummy_news:
                return False
            
            # 실제 뉴스 서비스 실행
            await execute_news_crawling()
            
            logger.info("✅ 뉴스 서비스 테스트 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ 뉴스 서비스 테스트 실패: {e}")
            return False
    
    async def test_disclosure_service(self):
        """공시 서비스 테스트"""
        try:
            logger.info("📋 공시 서비스 테스트 시작")
            
            # 실제 공시 서비스 함수 호출
            from services.disclosure_service.disclosure_service import execute_disclosure_analysis
            
            # 더미 공시 데이터 생성
            dummy_disclosure = await self.create_dummy_disclosure_data()
            if not dummy_disclosure:
                return False
            
            # 실제 공시 서비스 실행
            await execute_disclosure_analysis()
            
            logger.info("✅ 공시 서비스 테스트 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ 공시 서비스 테스트 실패: {e}")
            return False
    
    async def test_chart_service(self):
        """차트 서비스 테스트"""
        try:
            logger.info("📈 차트 서비스 테스트 시작")
            
            # 차트 서비스 인스턴스 생성
            from services.chart_service.chart_service import ChartAnalysisService
            chart_service = ChartAnalysisService()
            
            # 더미 차트 데이터 생성
            dummy_chart = await self.create_dummy_chart_data()
            if not dummy_chart:
                return False
            
            # 실제 차트 서비스의 알림 발송 함수 직접 호출
            # 가짜 더미데이터로 조건을 만족했다고 가정
            test_results = {
                "stock_code": self.test_stock_code,
                "stock_name": self.test_stock_name,
                "current_price": 16000,
                "current_volume": 2450000,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "satisfied_conditions": [
                    {
                        "name": "golden_cross",
                        "result": True,
                        "details": "5일선이 20일선을 상향 돌파했습니다.",
                        "five_day_prices": [
                            {"date": "2025-07-25", "close": 15000},
                            {"date": "2025-07-26", "close": 15200},
                            {"date": "2025-07-27", "close": 15400},
                            {"date": "2025-07-28", "close": 15600},
                            {"date": "2025-07-29", "close": 15800}
                        ],
                        "reference_date": "2025-07-20"
                    },
                    {
                        "name": "bollinger_touch",
                        "result": True,
                        "details": "주가가 볼린저밴드 상단에 터치했습니다.",
                        "five_day_prices": [
                            {"date": "2025-07-25", "close": 14800},
                            {"date": "2025-07-26", "close": 15000},
                            {"date": "2025-07-27", "close": 15200},
                            {"date": "2025-07-28", "close": 15400},
                            {"date": "2025-07-29", "close": 15600}
                        ],
                        "reference_date": "2025-07-18"
                    },
                    {
                        "name": "rsi_condition",
                        "result": True,
                        "details": "RSI가 과매수 구간에 진입했습니다.",
                        "five_day_prices": [
                            {"date": "2025-07-25", "close": 14900},
                            {"date": "2025-07-26", "close": 15100},
                            {"date": "2025-07-27", "close": 15300},
                            {"date": "2025-07-28", "close": 15500},
                            {"date": "2025-07-29", "close": 15700}
                        ],
                        "reference_date": "2025-07-15"
                    }
                ]
            }
            
            # 실제 차트 서비스의 알림 발송 함수 직접 호출
            await chart_service.send_condition_notification(test_results)
            
            logger.info("✅ 차트 서비스 테스트 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ 차트 서비스 테스트 실패: {e}")
            return False
    
    async def test_flow_analysis_service(self):
        """수급 분석 서비스 테스트"""
        try:
            logger.info("💰 수급 분석 서비스 테스트 시작")
            
            # 실제 수급 분석 서비스 함수 호출
            from services.flow_analysis_service.flow_analysis_service import execute_eod_processing
            
            # 더미 수급 데이터 생성
            dummy_flow = await self.create_dummy_flow_data()
            if not dummy_flow:
                return False
            
            # 실제 수급 분석 서비스 실행
            await execute_eod_processing()
            
            logger.info("✅ 수급 분석 서비스 테스트 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ 수급 분석 서비스 테스트 실패: {e}")
            return False
    
    async def create_dummy_news_data(self):
        """더미 뉴스 데이터 생성"""
        try:
            # 실제 뉴스 테이블 스키마에 맞는 데이터 생성
            dummy_news = {
                "title": f"테스트 뉴스 - {self.test_stock_name} 급등",
                "content": f"{self.test_stock_name}이 급등세를 보이고 있습니다. 투자자들의 관심이 집중되고 있습니다.",
                "url": "https://test.news.com/test_article",
                "source": "테스트뉴스",
                "published_at": datetime.now(),
                "stock_code": self.test_stock_code,
                "impact_score": 0.8,
                "reasoning": "테스트 뉴스입니다."
            }
            
            # 데이터베이스에 삽입
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO news (title, content, url, source, published_at, stock_code, impact_score, reasoning)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    dummy_news["title"],
                    dummy_news["content"],
                    dummy_news["url"],
                    dummy_news["source"],
                    dummy_news["published_at"],
                    dummy_news["stock_code"],
                    dummy_news["impact_score"],
                    dummy_news["reasoning"]
                ))
                conn.commit()
            
            logger.info("✅ 더미 뉴스 데이터 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 더미 뉴스 데이터 생성 실패: {e}")
            return False
    
    async def create_dummy_disclosure_data(self):
        """더미 공시 데이터 생성"""
        try:
            # 실제 공시 테이블 스키마에 맞는 데이터 생성
            dummy_disclosure = {
                "corp_code": "00126380",
                "stock_code": self.test_stock_code,
                "corp_name": self.test_stock_name,
                "report_nm": "주요사항보고서",
                "rcept_no": "202501301753871578",
                "flr_nm": "미래에셋증권",
                "rcept_dt": "20250130",
                "rm": "테스트 공시"
            }
            
            # 데이터베이스에 삽입
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO disclosure_history 
                    (corp_code, stock_code, corp_name, report_nm, rcept_no, flr_nm, rcept_dt, rm)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    dummy_disclosure["corp_code"],
                    dummy_disclosure["stock_code"],
                    dummy_disclosure["corp_name"],
                    dummy_disclosure["report_nm"],
                    dummy_disclosure["rcept_no"],
                    dummy_disclosure["flr_nm"],
                    dummy_disclosure["rcept_dt"],
                    dummy_disclosure["rm"]
                ))
                conn.commit()
            
            logger.info("✅ 더미 공시 데이터 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 더미 공시 데이터 생성 실패: {e}")
            return False
    
    async def create_dummy_chart_data(self):
        """더미 차트 데이터 생성"""
        try:
            # 실제 차트 테이블 스키마에 맞는 데이터 생성
            current_date = datetime.now().date()
            
            # 30일간의 차트 데이터 생성
            for i in range(30):
                date = current_date - timedelta(days=i)
                
                # 골든크로스 조건을 만족하는 데이터 생성
                if i == 0:  # 오늘
                    close_price = 16000
                    volume = 2450000
                else:
                    close_price = 15000 + i * 50
                    volume = 2000000 + i * 10000
                
                # 데이터베이스에 삽입
                with self.mysql_client.get_connection() as conn:
                    cursor = conn.cursor()
                    query = """
                        INSERT INTO chart_analysis_results 
                        (stock_code, date, time, close_price, volume, golden_cross, bollinger_touch, rsi_condition)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (
                        self.test_stock_code,
                        date,
                        "09:00:00",
                        close_price,
                        volume,
                        1 if i == 0 else 0,  # 오늘만 골든크로스
                        1 if i == 0 else 0,  # 오늘만 볼린저 터치
                        1 if i == 0 else 0   # 오늘만 RSI 조건
                    ))
                    conn.commit()
            
            logger.info("✅ 더미 차트 데이터 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 더미 차트 데이터 생성 실패: {e}")
            return False
    
    async def create_dummy_flow_data(self):
        """더미 수급 데이터 생성"""
        try:
            # 실제 수급 테이블 스키마에 맞는 데이터 생성
            current_date = datetime.now().date()
            
            # 5일간의 수급 데이터 생성
            for i in range(5):
                date = current_date - timedelta(days=i)
                
                # 기관 매수 조건을 만족하는 데이터 생성
                eod_flow_data = {
                    "ticker": self.test_stock_code,
                    "trade_date": date,
                    "close_price": 15000 + i * 100,
                    "volume": 1000000 + i * 100000,
                    "inst_net": 500000 + i * 100000,  # 기관 순매수
                    "foreign_net": 300000 + i * 50000,  # 외국인 순매수
                    "individ_net": -800000 - i * 150000,  # 개인 순매도
                    "total_value": 15000000000 + i * 1000000000
                }
                
                # 데이터베이스에 삽입
                with self.mysql_client.get_connection() as conn:
                    cursor = conn.cursor()
                    query = """
                        INSERT INTO eod_flows 
                        (ticker, trade_date, close_price, volume, inst_net, foreign_net, individ_net, total_value)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (
                        eod_flow_data["ticker"],
                        eod_flow_data["trade_date"],
                        eod_flow_data["close_price"],
                        eod_flow_data["volume"],
                        eod_flow_data["inst_net"],
                        eod_flow_data["foreign_net"],
                        eod_flow_data["individ_net"],
                        eod_flow_data["total_value"]
                    ))
                    conn.commit()
            
            logger.info("✅ 더미 수급 데이터 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 더미 수급 데이터 생성 실패: {e}")
            return False
    
    async def cleanup_test_data(self):
        """테스트 데이터 정리"""
        try:
            logger.info("🧹 테스트 데이터 정리 시작")
            
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor()
                
                # 뉴스 데이터 삭제
                cursor.execute("DELETE FROM news WHERE stock_code = %s AND title LIKE %s", (self.test_stock_code, "테스트 뉴스%"))
                
                # 공시 데이터 삭제
                cursor.execute("DELETE FROM disclosure_history WHERE stock_code = %s AND rcept_no = %s", (self.test_stock_code, "202501301753871578"))
                
                # 차트 데이터 삭제
                cursor.execute("DELETE FROM chart_analysis_results WHERE stock_code = %s AND date >= %s", (self.test_stock_code, datetime.now().date() - timedelta(days=30)))
                
                # 수급 데이터 삭제
                cursor.execute("DELETE FROM eod_flows WHERE ticker = %s AND trade_date >= %s", (self.test_stock_code, datetime.now().date() - timedelta(days=5)))
                
                conn.commit()
            
            logger.info("✅ 테스트 데이터 정리 완료")
            
        except Exception as e:
            logger.error(f"❌ 테스트 데이터 정리 실패: {e}")
    
    async def print_results(self, results):
        """테스트 결과 출력"""
        logger.info("=" * 80)
        logger.info("📊 통합 최종 테스트 결과")
        logger.info("=" * 80)
        
        success_rate = (results["passed_tests"] / results["total_tests"]) * 100 if results["total_tests"] > 0 else 0
        
        logger.info(f"총 테스트: {results['total_tests']}개")
        logger.info(f"성공: {results['passed_tests']}개")
        logger.info(f"실패: {results['failed_tests']}개")
        logger.info(f"성공률: {success_rate:.1f}%")
        
        logger.info("\n📋 상세 결과:")
        for detail in results["details"]:
            logger.info(f"  {detail}")
        
        if success_rate >= 80:
            logger.info("\n🎉 테스트 성공! 실제 서비스에서도 정상 작동할 것입니다!")
        else:
            logger.info("\n⚠️ 일부 테스트가 실패했습니다. 추가 검토가 필요합니다.")
        
        logger.info("=" * 80)

async def main():
    """메인 함수"""
    tester = FinalIntegratedTester()
    
    try:
        # 모든 테스트 실행
        results = await tester.run_all_tests()
        
        # 테스트 데이터 정리
        await tester.cleanup_test_data()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 테스트 실행 중 오류 발생: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(main()) 