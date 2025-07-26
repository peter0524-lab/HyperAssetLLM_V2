"""
주가 추이 분석 서비스 테스트 파일
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 프로젝트 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from stock_trend_service import StockTrendService


class TestStockTrendService(unittest.TestCase):
    """주가 추이 분석 서비스 테스트 클래스"""
    
    @classmethod
    def setUpClass(cls):
        """테스트 클래스 초기화"""
        print("=" * 60)
        print("🧪 주가 추이 분석 서비스 테스트 시작")
        print("=" * 60)
        
        cls.service = StockTrendService()
        
        # 테스트에 사용할 종목 코드
        cls.test_stock_codes = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # 네이버
        ]
        
        # 실제 텔레그램 전송 테스트 여부
        cls.enable_telegram_test = False  # True로 설정하면 실제 전송 테스트
        
    def setUp(self):
        """각 테스트 메서드 실행 전 초기화"""
        print(f"\n🔍 테스트 시작: {self._testMethodName}")
        
    def tearDown(self):
        """각 테스트 메서드 실행 후 정리"""
        print(f"✅ 테스트 완료: {self._testMethodName}")
        
    def test_01_service_initialization(self):
        """서비스 초기화 테스트"""
        self.assertIsNotNone(self.service)
        self.assertIsNotNone(self.service.telegram_client)
        self.assertEqual(self.service.analysis_days, 5)
        print("   ✓ 서비스 초기화 성공")
        
    def test_02_stock_name_lookup(self):
        """종목명 조회 테스트"""
        for stock_code in self.test_stock_codes:
            stock_name = self.service.get_stock_name(stock_code)
            self.assertIsInstance(stock_name, str)
            self.assertNotEqual(stock_name, "")
            print(f"   ✓ {stock_code}: {stock_name}")
            
    def test_03_business_days_lookup(self):
        """영업일 조회 테스트"""
        business_days = self.service.get_business_days(5)
        
        self.assertIsInstance(business_days, list)
        self.assertEqual(len(business_days), 5)
        
        # 날짜 형식 확인
        for day in business_days:
            self.assertIsInstance(day, str)
            self.assertEqual(len(day), 8)  # YYYYMMDD 형식
            
        print(f"   ✓ 영업일 조회 성공: {business_days}")
        
    def test_04_ohlcv_data_retrieval(self):
        """OHLCV 데이터 조회 테스트"""
        stock_code = self.test_stock_codes[0]  # 삼성전자
        
        df = self.service.get_stock_ohlcv_data(stock_code, 5)
        
        self.assertIsNotNone(df)
        if df is not None and hasattr(df, 'empty') and not df.empty:
            # 필수 컬럼 확인
            required_columns = ['시가', '고가', '저가', '종가', '거래량', '거래대금', '등락률']
            if hasattr(df, 'columns'):
                for col in required_columns:
                    self.assertIn(col, df.columns)
                self.assertIn('거래대금_억원', df.columns)
                self.assertIn('거래량_만주', df.columns)
            print(f"   ✓ OHLCV 데이터 조회 성공: {len(df)}일간 데이터")
            if hasattr(df, 'iloc') and hasattr(df, '__len__') and len(df) > 0:
                print(f"   ✓ 최근 종가: {df.iloc[-1]['종가']:,}원")
        
    def test_05_stock_trend_analysis(self):
        """주가 추이 분석 테스트"""
        stock_code = self.test_stock_codes[0]  # 삼성전자
        
        analysis = self.service.analyze_stock_trend(stock_code, 5)
        
        self.assertIsNotNone(analysis)
        if analysis is not None and isinstance(analysis, dict):
            # 필수 키 확인
            required_keys = [
                'stock_code', 'stock_name', 'analysis_period',
                'start_date', 'end_date', 'current_price',
                'daily_data', 'summary'
            ]
            for key in required_keys:
                self.assertIn(key, analysis)
            
            # 요약 통계 확인
            summary = analysis.get('summary', {}) if isinstance(analysis.get('summary', {}), dict) else {}
            summary_keys = [
                'total_change_rate', 'avg_volume_man', 'avg_trading_value_eok',
                'max_daily_change', 'min_daily_change', 'volatility'
            ]
            for key in summary_keys:
                self.assertIn(key, summary)
            
            print(f"   ✓ 주가 추이 분석 성공: {analysis.get('stock_name', '')}")
            print(f"   ✓ 기간 수익률: {summary.get('total_change_rate', 0):+.2f}%")
            print(f"   ✓ 평균 거래량: {summary.get('avg_volume_man', 0):,.1f}만주")
            print(f"   ✓ 평균 거래대금: {summary.get('avg_trading_value_eok', 0):,.1f}억원")
        
    def test_06_message_formatting(self):
        """메시지 포맷팅 테스트"""
        stock_code = self.test_stock_codes[0]  # 삼성전자
        
        # 분석 데이터 생성
        analysis = self.service.analyze_stock_trend(stock_code, 5)
        self.assertIsNotNone(analysis)
        if analysis is not None and isinstance(analysis, dict):
            # 메시지 포맷팅
            message = self.service.format_trend_message(analysis)
            
            self.assertIsInstance(message, str)
            self.assertGreater(len(message), 0)
            
            # 필수 요소 포함 확인
            self.assertIn(analysis.get('stock_name', ''), message)
            self.assertIn(analysis.get('stock_code', ''), message)
            self.assertIn("현재가", message)
            self.assertIn("기간 수익률", message)
            self.assertIn("거래량", message)
            self.assertIn("거래대금", message)
            
            print(f"   ✓ 메시지 포맷팅 성공: {len(message)}자")
            print(f"   ✓ 메시지 미리보기:")
            print("   " + "=" * 50)
            print("   " + message[:200] + "...")
            print("   " + "=" * 50)
        
    def test_07_popular_stocks_lookup(self):
        """인기 종목 조회 테스트"""
        # KOSPI 인기 종목 조회
        kospi_stocks = self.service.get_popular_stocks("KOSPI", 5)
        
        self.assertIsInstance(kospi_stocks, list)
        self.assertEqual(len(kospi_stocks), 5)
        
        # 종목 코드 형식 확인
        for stock_code in kospi_stocks:
            self.assertIsInstance(stock_code, str)
            self.assertEqual(len(stock_code), 6)  # 6자리 종목코드
            
        print(f"   ✓ KOSPI 인기 종목 조회 성공: {kospi_stocks}")
        
        # 종목명 확인
        for stock_code in kospi_stocks[:3]:  # 상위 3개만
            stock_name = self.service.get_stock_name(stock_code)
            print(f"   ✓ {stock_code}: {stock_name}")
            
    def test_08_service_health_check(self):
        """서비스 상태 확인 테스트"""
        status = self.service.health_check()
        
        self.assertIsInstance(status, dict)
        if status is not None and isinstance(status, dict):
            self.assertIn("status", status)
            self.assertIn("telegram_status", status)
            self.assertIn("pykrx_status", status)
            self.assertIn("timestamp", status)
            print(f"   ✓ 서비스 상태: {status.get('status', '')}")
            print(f"   ✓ 텔레그램 상태: {status.get('telegram_status', {}).get('status', '')}")
            print(f"   ✓ pykrx 상태: {status.get('pykrx_status', '')}")
        
    def test_09_multiple_stock_analysis(self):
        """복수 종목 분석 테스트"""
        results = {}
        
        for stock_code in self.test_stock_codes:
            analysis = self.service.analyze_stock_trend(stock_code, 5)
            results[stock_code] = analysis
            
        # 모든 종목 분석 성공 확인
        for stock_code, analysis in results.items():
            self.assertIsNotNone(analysis)
            if analysis is not None and isinstance(analysis, dict):
                stock_name = analysis.get('stock_name', '')
                change_rate = analysis.get('summary', {}).get('total_change_rate', 0)
                
                print(f"   ✓ {stock_code} ({stock_name}): {change_rate:+.2f}%")
            
    def test_10_telegram_send_test(self):
        """텔레그램 전송 테스트 (선택적)"""
        if not self.enable_telegram_test:
            print("   ⚠️  텔레그램 전송 테스트 비활성화됨")
            print("   ℹ️  실제 전송 테스트를 원하면 enable_telegram_test=True로 설정")
            return
            
        stock_code = self.test_stock_codes[0]  # 삼성전자
        
        print(f"   📲 텔레그램 알림 전송 테스트 시작: {stock_code}")
        
        success = self.service.send_trend_alert(stock_code, 5)
        
        if success:
            print("   ✅ 텔레그램 알림 전송 성공")
        else:
            print("   ❌ 텔레그램 알림 전송 실패")
            
        # 실패해도 테스트는 통과 (네트워크 상황에 따라 다를 수 있음)
        self.assertIsInstance(success, bool)


def run_integration_test():
    """통합 테스트 실행"""
    print("\n" + "=" * 60)
    print("🔄 통합 테스트 시작")
    print("=" * 60)
    
    try:
        service = StockTrendService()
        
        # 1. 서비스 상태 확인
        print("1️⃣ 서비스 상태 확인 중...")
        status = service.health_check()
        print(f"   📊 전체 상태: {status.get('status', '')}")
        
        # 2. 실제 종목 분석
        print("\n2️⃣ 실제 종목 분석 중...")
        test_stock = "005930"  # 삼성전자
        analysis = service.analyze_stock_trend(test_stock, 5)
        
        if analysis:
            print(f"   ✅ {analysis.get('stock_name', '')} 분석 성공")
            print(f"   📈 현재가: {analysis.get('current_price', 0):,}원")
            print(f"   📊 기간 수익률: {analysis.get('summary', {}).get('total_change_rate', 0):+.2f}%")
        else:
            print("   ❌ 종목 분석 실패")
            
        # 3. 메시지 생성 테스트
        print("\n3️⃣ 메시지 생성 테스트 중...")
        if analysis:
            message = service.format_trend_message(analysis)
            print(f"   ✅ 메시지 생성 성공: {len(message)}자")
            print(f"   📝 메시지 미리보기:")
            print("   " + "-" * 50)
            lines = message.split('\n')
            for i, line in enumerate(lines[:10]):  # 처음 10줄만 표시
                print(f"   {line}")
            if len(lines) > 10:
                print(f"   ... (총 {len(lines)}줄)")
            print("   " + "-" * 50)
        else:
            print("   ❌ 메시지 생성 실패")
            
        print("\n✅ 통합 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


def run_quick_test():
    """빠른 테스트 실행"""
    print("\n" + "=" * 60)
    print("⚡ 빠른 테스트 시작")
    print("=" * 60)
    
    try:
        service = StockTrendService()
        
        # 기본 기능 테스트
        test_stock = "005930"  # 삼성전자
        
        print(f"1️⃣ 종목명 조회: {test_stock}")
        stock_name = service.get_stock_name(test_stock)
        print(f"   ✅ {stock_name}")
        
        print(f"\n2️⃣ 영업일 조회 (5일)")
        business_days = service.get_business_days(5)
        print(f"   ✅ {business_days}")
        
        print(f"\n3️⃣ 주가 분석")
        analysis = service.analyze_stock_trend(test_stock, 5)
        if analysis:
            print(f"   ✅ 분석 성공: {analysis.get('stock_name', '')}")
            print(f"   📈 현재가: {analysis.get('current_price', 0):,}원")
            print(f"   📊 기간 수익률: {analysis.get('summary', {}).get('total_change_rate', 0):+.2f}%")
        else:
            print("   ❌ 분석 실패")
            
        print(f"\n4️⃣ 서비스 상태 확인")
        status = service.health_check()
        print(f"   📊 전체 상태: {status.get('status', '')}")
        print(f"   📲 텔레그램: {status.get('telegram_status', {}).get('status', '')}")
        print(f"   📈 pykrx: {status.get('pykrx_status', '')}")
        
        print("\n✅ 빠른 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 빠른 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="주가 추이 분석 서비스 테스트")
    parser.add_argument("--mode", choices=["unit", "integration", "quick"], default="unit",
                        help="테스트 모드 (unit: 단위 테스트, integration: 통합 테스트, quick: 빠른 테스트)")
    parser.add_argument("--telegram", action="store_true",
                        help="텔레그램 전송 테스트 활성화")
    
    args = parser.parse_args()
    
    if args.mode == "unit":
        # 단위 테스트 실행
        if args.telegram:
            TestStockTrendService.enable_telegram_test = True
            
        unittest.main(argv=[''])
        
    elif args.mode == "integration":
        # 통합 테스트 실행
        run_integration_test()
        
    elif args.mode == "quick":
        # 빠른 테스트 실행
        run_quick_test()
        
    else:
        print("알 수 없는 테스트 모드입니다.") 