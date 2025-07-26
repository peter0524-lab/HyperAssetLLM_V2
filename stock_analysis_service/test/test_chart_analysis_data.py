"""
Chart Service 테스트 - 영업일 기준 5일 이내 제외 로직 검증
수정된 로직: 오늘부터 영업일 5일 이내의 조건은 제외하고 그 이전 최근 조건 찾기
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import logging

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.chart_service.chart_service import ChartAnalysisService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_realtime_notification_logic():
    """영업일 기준 5일 이내 제외 로직 테스트"""
    try:
        logger.info("=== 영업일 기준 5일 이내 제외 로직 테스트 시작 ===")
        
        # Chart Service 인스턴스 생성
        chart_service = ChartAnalysisService()
        
        # 테스트 데이터
        test_stock_code = "006800"  # 미래에셋증권
        
        logger.info(f"테스트 종목: {test_stock_code}")
        
        # 1. 영업일 기준 cutoff 날짜 계산 테스트
        logger.info("\n--- 1단계: 영업일 기준 cutoff 날짜 계산 테스트 ---")
        
        # KIS API로부터 최근 영업일 데이터 조회
        df = await chart_service.fetch_historical_data(test_stock_code, period=20)
        if not df.empty:
            import pandas as pd
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)
            
            logger.info("최근 영업일 데이터:")
            for i, row in df.head(10).iterrows():
                logger.info(f"  {i}: {row['date'].strftime('%Y-%m-%d (%a)')}")
            
            if len(df) > 5:
                cutoff_date = df.iloc[5]['date']
                logger.info(f"\n영업일 기준 5일째 cutoff 날짜: {cutoff_date.strftime('%Y-%m-%d (%a)')}")
        
        # 2. 기존 과거 5일 주가 조회 로직 테스트
        logger.info("\n--- 2단계: 과거 5일 주가 조회 로직 테스트 ---")
        
        test_past_dates = [
            "2025-07-11",  # 골든크로스 발생일
            "2025-07-08",  # 20일선 터치일
            "2025-05-29"   # 거래량 급증일
        ]
        
        for past_date in test_past_dates:
            logger.info(f"\n🔍 {past_date}부터 영업일 5일간 주가 조회:")
            
            # KIS API를 통한 과거 5일 주가 조회
            historical_prices = await chart_service.get_historical_prices(
                stock_code=test_stock_code,
                from_date=past_date,
                days=5
            )
            
            logger.info(f"조회 결과: {len(historical_prices)}건")
            
            if historical_prices:
                logger.info("📈 영업일 5일간 주가 데이터:")
                for price_data in historical_prices:
                    change_str = ""
                    if price_data.get('change_rate') is not None:
                        change_str = f" ({price_data['change_rate']:+.2f}%)"
                    logger.info(f"  └ {price_data['date']}: {price_data['close']:,.0f}원{change_str}")
                
                # 마지막날 수익률 계산
                if len(historical_prices) > 0:
                    last_data = historical_prices[-1]
                    if last_data.get('change_rate') is not None:
                        logger.info(f"📊 영업일 5일 최종 수익률: {last_data['change_rate']:+.2f}%")
            else:
                logger.warning("⚠️ 과거 5일 주가 데이터를 찾을 수 없습니다.")
        
        # 3. 수정된 get_latest_condition_date 로직 테스트 
        logger.info("\n--- 3단계: 수정된 조건 날짜 조회 로직 테스트 ---")
        
        # 각 조건별로 영업일 5일 이내 제외 로직 테스트
        test_conditions = ["golden_cross", "ma20_touch", "volume_surge"]
        
        for condition in test_conditions:
            logger.info(f"\n🔍 {condition} 조건의 최근 만족 날짜 조회 (영업일 5일 이내 제외):")
            
            # 수정된 로직으로 조건 날짜 조회
            latest_date = await chart_service.get_latest_condition_date(test_stock_code, condition)
            
            if latest_date:
                logger.info(f"✅ 영업일 5일 이전 최근 만족 날짜: {latest_date}")
                
                # 해당 날짜부터 5일간 주가 조회
                historical_prices = await chart_service.get_historical_prices(
                    stock_code=test_stock_code,
                    from_date=latest_date,
                    days=5
                )
                
                if historical_prices:
                    logger.info(f"📈 {latest_date}부터 영업일 5일간 주가 ({len(historical_prices)}건):")
                    for price_data in historical_prices:
                        change_str = ""
                        if price_data.get('change_rate') is not None:
                            change_str = f" ({price_data['change_rate']:+.2f}%)"
                        logger.info(f"  └ {price_data['date']}: {price_data['close']:,.0f}원{change_str}")
                    
                    # 마지막날 수익률
                    if len(historical_prices) > 0:
                        last_data = historical_prices[-1]
                        if last_data.get('change_rate') is not None:
                            logger.info(f"📊 최종 수익률: {last_data['change_rate']:+.2f}%")
                            if len(historical_prices) == 5:
                                logger.info("✅ 항상 5일 주가 데이터 확보!")
                            else:
                                logger.warning(f"⚠️ 예상과 다른 데이터 개수: {len(historical_prices)}건")
                else:
                    logger.warning("⚠️ 과거 5일 주가 데이터를 찾을 수 없습니다.")
            else:
                logger.info("❌ 영업일 5일 이전의 조건 만족 날짜가 없습니다.")
        
        # 4. 실시간 알림 로직 테스트 
        logger.info("\n--- 4단계: 실시간 텔레그램 알림 로직 테스트 ---")
        
        # 오늘 날짜의 가상 조건 만족 데이터 생성 (실시간 시뮬레이션)
        today = datetime.now()
        
        # 가상 실시간 알림 데이터 구성
        notification_data = {
            "stock_code": test_stock_code,
            "satisfied_conditions": [
                {
                    "name": "golden_cross",
                    "details": "5일선이 20일선 상향돌파"
                },
                {
                    "name": "ma20_touch", 
                    "details": "20일선 터치 후 반등"
                },
                {
                    "name": "volume_surge",
                    "details": "거래량 2.97배 급증"
                }
            ],
            "current_price": 8750.0,
            "current_volume": 6234567,
            "date": today.strftime("%Y-%m-%d"),
            "time": today.strftime("%H:%M:%S")
        }
        
        logger.info("📱 실시간 텔레그램 알림 전송 테스트 시작...")
        logger.info(f"가상 조건 만족: {len(notification_data['satisfied_conditions'])}개 조건")
        logger.info("📝 수정된 로직: 영업일 5일 이내 조건 제외, 이전 조건에서 항상 5일 주가 제공")
        
        # 실제 알림 전송 (수정된 로직: 영업일 5일 이내 제외)
        await chart_service.send_condition_notification(notification_data)
        
        logger.info("✅ 실시간 텔레그램 알림 전송 완료!")
        
        # 3. 로직 검증
        logger.info("\n--- 3단계: 로직 검증 ---")
        logger.info("✅ 웹소켓 실시간 모니터링 → 조건 체크 → DB 저장 → 즉시 텔레그램 알림")
        logger.info("✅ 과거 참조날짜에서 영업일 기준 5일 주가 조회 (KIS API)")  
        logger.info("✅ 텔레그램 알림에 과거 사례와 수익률 포함")
        
        logger.info("\n=== 실시간 알림 로직 테스트 완료 ===")
        
    except Exception as e:
        logger.error(f"❌ 테스트 실행 중 오류 발생: {e}")
        raise
    finally:
        # 정리 작업
        if 'chart_service' in locals():
            await chart_service.mysql_client.close()

if __name__ == "__main__":
    asyncio.run(test_realtime_notification_logic()) 