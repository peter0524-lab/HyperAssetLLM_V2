import pandas as pd
from pykrx import stock
from datetime import datetime

def find_significant_days(stock_code="006800", start_date="20150101", end_date="20250716"):
    """
    거래량 1000만주 이상 또는 등락률 +5% 이상인 날짜 찾기
    """
    
    print(f"미래에셋증권({stock_code}) 분석 중...")
    print(f"기간: {start_date} ~ {end_date}")
    print("-" * 50)
    
    try:
        # OHLCV 데이터 가져오기
        df = stock.get_market_ohlcv_by_date(start_date, end_date, stock_code)
        
        if df.empty:
            print("데이터가 없습니다.")
            return None
        
        # 등락률 계산 (전일 대비)
        df['등락률'] = df['종가'].pct_change() * 100
        
        # 조건: 거래량 1000만 이상 또는 등락률 +5% 이상
        condition = (df['거래량'] >= 10000000) | (df['등락률'] >= 10.0)
        result = df[condition]
        
        if result.empty:
            print("조건에 맞는 날짜가 없습니다.")
            return None
        
        # 결과 출력
        print(f"\n총 {len(result)}개 날짜 발견:\n")
        
        for date, row in result.iterrows():
            # 날짜를 문자열로 변환 (가장 안전한 방법)
            date_str = str(date)[:10]  # YYYY-MM-DD 형태로 추출
            
            print(f"날짜: {date_str}")
            print(f"  - 종가: {row['종가']:,}원")
            print(f"  - 거래량: {row['거래량']:,}주", end="")
            if row['거래량'] >= 10000000:
                print(" ★", end="")
            print()
            print(f"  - 등락률: {row['등락률']:.2f}%", end="")
            if row['등락률'] >= 5.0:
                print(" ★", end="")
            print("\n")
        
        return result
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return None


# 실행
if __name__ == "__main__":
    # 2024년 데이터 분석
    result = find_significant_days("006800", "20150101", "20250716")
    
    # 결과를 DataFrame으로 보고 싶다면
    if result is not None:
        print("\n=== DataFrame 형태로 보기 ===")
        print(result[['종가', '거래량', '등락률']])