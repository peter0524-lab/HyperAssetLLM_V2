#!/usr/bin/env python3
"""
수정된 pykrx 시가총액과 PER 조회 기능 테스트
"""

import sys
import os
import logging
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_fixed_pykrx():
    """수정된 pykrx 기능 테스트"""
    print("🔍 수정된 pykrx 기능 테스트 시작")
    
    try:
        # pykrx import
        from pykrx import stock
        print("✅ pykrx import 성공")
        
        # 테스트 종목
        stock_code = "005930"  # 삼성전자
        today = datetime.now().strftime("%Y%m%d")
        
        print(f"📊 테스트 종목: {stock_code} (삼성전자)")
        print(f"📅 오늘 날짜: {today}")
        
        # 1. 전체 시장 시가총액 조회 테스트
        print("\n💰 1. 전체 시장 시가총액 조회 테스트")
        try:
            cap_df = stock.get_market_cap(today)
            print(f"✅ 전체 시장 시가총액 조회 성공: {len(cap_df)}개 종목")
            print(f"📊 시가총액 컬럼: {list(cap_df.columns)}")
            
            # 삼성전자 검색
            if stock_code in cap_df.index:
                market_cap = int(cap_df.loc[stock_code, '시가총액'])
                print(f"✅ 삼성전자 시가총액: {market_cap:,}원")
            else:
                print("⚠️ 삼성전자가 전체 시장 데이터에 없음")
                # 종목명으로 검색
                stock_name = stock.get_market_ticker_name(stock_code)
                print(f"🔍 종목명으로 검색: {stock_name}")
                matching_rows = cap_df[cap_df.index.str.contains(stock_name, na=False)]
                if not matching_rows.empty:
                    market_cap = int(matching_rows.iloc[0]['시가총액'])
                    print(f"✅ 종목명으로 찾은 시가총액: {market_cap:,}원")
                else:
                    print("❌ 종목명으로도 찾을 수 없음")
                    
        except Exception as e:
            print(f"❌ 전체 시장 시가총액 조회 실패: {e}")
        
        # 2. 전체 시장 PER 조회 테스트
        print("\n📊 2. 전체 시장 PER 조회 테스트")
        try:
            fundamental_df = stock.get_market_fundamental(today)
            print(f"✅ 전체 시장 PER 조회 성공: {len(fundamental_df)}개 종목")
            print(f"📊 PER 컬럼: {list(fundamental_df.columns)}")
            
            # 삼성전자 검색
            if stock_code in fundamental_df.index:
                per = float(fundamental_df.loc[stock_code, 'PER'])
                print(f"✅ 삼성전자 PER: {per:.2f}")
            else:
                print("⚠️ 삼성전자가 전체 시장 데이터에 없음")
                # 종목명으로 검색
                stock_name = stock.get_market_ticker_name(stock_code)
                print(f"🔍 종목명으로 검색: {stock_name}")
                matching_rows = fundamental_df[fundamental_df.index.str.contains(stock_name, na=False)]
                if not matching_rows.empty:
                    per = float(matching_rows.iloc[0]['PER'])
                    print(f"✅ 종목명으로 찾은 PER: {per:.2f}")
                else:
                    print("❌ 종목명으로도 찾을 수 없음")
                    
        except Exception as e:
            print(f"❌ 전체 시장 PER 조회 실패: {e}")
        
        # 3. 실제 NaverStockAPI 클래스 테스트
        print("\n🔧 3. 실제 NaverStockAPI 클래스 테스트")
        try:
            from services.news_service.main import NaverStockAPI
            api = NaverStockAPI()
            stock_info = api.get_stock_info(stock_code)
            print(f"✅ NaverStockAPI 테스트 성공")
            print(f"📊 조회된 정보: {stock_info}")
            
            # 시가총액과 PER 확인
            print(f"💰 시가총액: {stock_info.get('시가총액', 'N/A')}")
            print(f"📊 PER: {stock_info.get('PER', 'N/A')}")
            
        except Exception as e:
            print(f"❌ NaverStockAPI 테스트 실패: {e}")
            import traceback
            print(f"❌ 상세 에러: {traceback.format_exc()}")
        
        print("\n✅ 수정된 pykrx 기능 테스트 완료")
        
    except ImportError as e:
        print(f"❌ pykrx import 실패: {e}")
        print("💡 pip install pykrx를 실행하세요.")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 에러: {traceback.format_exc()}")

if __name__ == "__main__":
    test_fixed_pykrx() 