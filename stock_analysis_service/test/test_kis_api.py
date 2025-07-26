"""
KIS API 테스트 모듈
주가 데이터 수집 기능 테스트
"""

import logging
import time
import asyncio
from datetime import datetime
from shared.apis.kis_api import KISAPIClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_health_check(api: KISAPIClient):
    """서버 상태 확인 테스트"""
    logger.info("서버 상태 확인 테스트 시작")
    result = api.health_check()
    
    if result:
        logger.info("서버 상태 확인 성공:")
        logger.info(f"상태: {result}")
        return True
    else:
        logger.error("서버 상태 확인 실패")
        return False

def test_current_price(api: KISAPIClient, stock_code: str):
    """현재가 조회 테스트"""
    logger.info(f"현재가 조회 테스트 시작 - {stock_code}")
    result = api.get_current_price(stock_code)
    
    if result:
        logger.info("현재가 조회 성공:")
        logger.info(f"종목코드: {result['stock_code']}")
        logger.info(f"현재가: {result['current_price']}")
        logger.info(f"등락률: {result['change_rate']}%")
        logger.info(f"거래량: {result['volume']}")
        return True
    else:
        logger.error("현재가 조회 실패")
        return False

async def test_daily_chart(api: KISAPIClient, stock_code: str):
    """일봉 데이터 조회 테스트"""
    logger.info(f"일봉 데이터 조회 테스트 시작 - {stock_code}")
    result = await api.get_daily_chart(stock_code, days=10)  # 최근 10일간의 데이터
    
    if result and len(result) > 0:
        logger.info("일봉 데이터 조회 성공:")
        logger.info(f"데이터 개수: {len(result)}개")
        logger.info("최근 일봉 데이터:")
        for day_data in result[:3]:  # 최근 3일 데이터만 출력
            logger.info(f"날짜: {day_data['date']}, 종가: {day_data['close']}")
        return True
    else:
        logger.error("일봉 데이터 조회 실패")
        return False

def test_minute_chart(api: KISAPIClient, stock_code: str):
    """분봉 데이터 조회 테스트"""
    logger.info(f"분봉 데이터 조회 테스트 시작 - {stock_code}")
    result = api.get_minute_chart(stock_code, time_unit=1)  # 1분봉 데이터
    
    if result and len(result) > 0:
        logger.info("분봉 데이터 조회 성공:")
        logger.info(f"데이터 개수: {len(result)}개")
        logger.info("최근 분봉 데이터:")
        for minute_data in result[:3]:  # 최근 3개 분봉 데이터만 출력
            logger.info(f"날짜: {minute_data['date']}, 시간: {minute_data['time']}, 종가: {minute_data['close']}")
        return True
    else:
        logger.error("분봉 데이터 조회 실패")
        return False

def realtime_price_callback(data: dict):
    """실시간 가격 데이터 콜백 함수"""
    logger.info("실시간 데이터 수신:")
    logger.info(f"종목코드: {data['stock_code']}")
    logger.info(f"현재가: {data['current_price']}")
    logger.info(f"체결시간: {data['timestamp']}")

def test_realtime_price(api: KISAPIClient, stock_code: str):
    """실시간 가격 데이터 구독 테스트"""
    logger.info(f"실시간 가격 데이터 구독 테스트 시작 - {stock_code}")
    
    # 실시간 데이터 구독 시작
    success = api.start_realtime_price(stock_code, realtime_price_callback)
    
    if success:
        logger.info("실시간 데이터 구독 시작")
        # 10초간 데이터 수신
        time.sleep(10)
        
        # 구독 중지
        api.stop_realtime_price(stock_code)
        logger.info("실시간 데이터 구독 중지")
        return True
    else:
        logger.error("실시간 데이터 구독 실패")
        return False

async def main():
    """메인 테스트 함수"""
    # KIS API 클라이언트 초기화
    api = KISAPIClient()
    
    # 서버 상태 확인
    test_health_check(api)
    
    # 테스트할 종목코드 (삼성전자)
    stock_code = "005930"
    
    # 각 기능 테스트
    test_results = {
        "현재가 조회": test_current_price(api, stock_code),
        "일봉 데이터": await test_daily_chart(api, stock_code),
        "분봉 데이터": test_minute_chart(api, stock_code),
        "실시간 데이터": test_realtime_price(api, stock_code)
    }
    
    # 테스트 결과 출력
    logger.info("\n=== 테스트 결과 요약 ===")
    for test_name, result in test_results.items():
        logger.info(f"{test_name}: {'성공' if result else '실패'}")

if __name__ == "__main__":
    asyncio.run(main()) 