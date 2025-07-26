#!/usr/bin/env python3
"""
pykrx 시가총액과 PER 조회 기능 테스트
"""

import sys
import os
import logging
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_pykrx_functions():
    """pykrx 기능 테스트"""
    print("🔍 pykrx 기능 테스트 시작")
    
    try:
        # pykrx import
        from pykrx import stock
        print("✅ pykrx import 성공")
        
        # 테스트 종목
        stock_code = "005930"  # 삼성전자
        today = datetime.now().strftime("%Y%m%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        
        print(f"📊 테스트 종목: {stock_code} (삼성전자)")
        print(f"📅 오늘 날짜: {today}")
        print(f"📅 어제 날짜: {yesterday}")
        
        # 1. 기본 OHLCV 데이터 테스트
        print("\n📈 1. 기본 OHLCV 데이터 테스트")
        try:
            ohlcv_df = stock.get_market_ohlcv(today, today, stock_code)
            print(f"✅ OHLCV 데이터 조회 성공: {len(ohlcv_df)}개 행")
            if not ohlcv_df.empty:
                print(f"📊 OHLCV 컬럼: {list(ohlcv_df.columns)}")
                print(f"📊 첫 번째 행: {ohlcv_df.iloc[0].to_dict()}")
        except Exception as e:
            print(f"❌ OHLCV 데이터 조회 실패: {e}")
        
        # 2. 시가총액 데이터 테스트
        print("\n💰 2. 시가총액 데이터 테스트")
        try:
            cap_df = stock.get_market_cap(today, stock_code)
            print(f"✅ 시가총액 데이터 조회 성공: {len(cap_df)}개 행")
            if not cap_df.empty:
                print(f"📊 시가총액 컬럼: {list(cap_df.columns)}")
                print(f"📊 첫 번째 행: {cap_df.iloc[0].to_dict()}")
            else:
                print("⚠️ 시가총액 데이터가 비어있음")
        except Exception as e:
            print(f"❌ 시가총액 데이터 조회 실패: {e}")
        
        # 3. PER 데이터 테스트
        print("\n📊 3. PER 데이터 테스트")
        try:
            fundamental_df = stock.get_market_fundamental(today, stock_code)
            print(f"✅ PER 데이터 조회 성공: {len(fundamental_df)}개 행")
            if not fundamental_df.empty:
                print(f"📊 PER 컬럼: {list(fundamental_df.columns)}")
                print(f"📊 첫 번째 행: {fundamental_df.iloc[0].to_dict()}")
            else:
                print("⚠️ PER 데이터가 비어있음")
        except Exception as e:
            print(f"❌ PER 데이터 조회 실패: {e}")
        
        # 4. 어제 데이터로 재시도
        print("\n🔄 4. 어제 데이터로 재시도")
        try:
            cap_df_yesterday = stock.get_market_cap(yesterday, stock_code)
            print(f"✅ 어제 시가총액 데이터 조회 성공: {len(cap_df_yesterday)}개 행")
            if not cap_df_yesterday.empty:
                print(f"📊 어제 시가총액: {cap_df_yesterday.iloc[0].to_dict()}")
        except Exception as e:
            print(f"❌ 어제 시가총액 데이터 조회 실패: {e}")
        
        try:
            fundamental_df_yesterday = stock.get_market_fundamental(yesterday, stock_code)
            print(f"✅ 어제 PER 데이터 조회 성공: {len(fundamental_df_yesterday)}개 행")
            if not fundamental_df_yesterday.empty:
                print(f"📊 어제 PER: {fundamental_df_yesterday.iloc[0].to_dict()}")
        except Exception as e:
            print(f"❌ 어제 PER 데이터 조회 실패: {e}")
        
        # 5. 다른 종목으로 테스트
        print("\n🔍 5. 다른 종목으로 테스트 (미래에셋증권)")
        test_stock = "006800"
        try:
            cap_df_other = stock.get_market_cap(today, test_stock)
            print(f"✅ 다른 종목 시가총액 조회 성공: {len(cap_df_other)}개 행")
            if not cap_df_other.empty:
                print(f"📊 다른 종목 시가총액: {cap_df_other.iloc[0].to_dict()}")
        except Exception as e:
            print(f"❌ 다른 종목 시가총액 조회 실패: {e}")
        
        print("\n✅ pykrx 기능 테스트 완료")
        
    except ImportError as e:
        print(f"❌ pykrx import 실패: {e}")
        print("💡 pip install pykrx를 실행하세요.")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 에러: {traceback.format_exc()}")

if __name__ == "__main__":
    test_pykrx_functions() 