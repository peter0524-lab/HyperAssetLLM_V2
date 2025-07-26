"""
주가 추이 분석 서비스 메인 실행 파일
"""

import argparse
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# 프로젝트 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from stock_trend_service import StockTrendService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_trend_main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="주가 추이 분석 서비스",
    description="pykrx를 사용한 주가 추이 분석 및 텔레그램 알림 서비스",
    version="1.0.0"
)

# 서비스 인스턴스
trend_service = StockTrendService()


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "주가 추이 분석 서비스", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    try:
        status = trend_service.health_check()
        return JSONResponse(content=status, status_code=200 if status.get("status") == "healthy" else 503)
    except Exception as e:
        logger.error(f"상태 확인 실패: {e}")
        return JSONResponse(content={"status": "unhealthy", "error": str(e)}, status_code=503)


@app.post("/analyze/{stock_code}")
async def analyze_stock(stock_code: str, days: int = 5):
    """단일 종목 분석"""
    try:
        logger.info(f"종목 분석 요청: {stock_code} ({days}일)")
        
        analysis = trend_service.analyze_stock_trend(stock_code, days)
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"종목 분석 실패: {stock_code}")
        
        return JSONResponse(content=analysis, status_code=200)
        
    except Exception as e:
        logger.error(f"종목 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alert/{stock_code}")
async def send_alert(stock_code: str, background_tasks: BackgroundTasks, days: int = 5):
    """단일 종목 알림 전송"""
    try:
        logger.info(f"종목 알림 요청: {stock_code} ({days}일)")
        
        # 백그라운드 태스크로 실행
        if background_tasks:
            background_tasks.add_task(trend_service.send_trend_alert, stock_code, days)
            return {"message": f"알림 전송 작업이 시작되었습니다: {stock_code}"}
        else:
            # 동기 실행
            success = trend_service.send_trend_alert(stock_code, days)
            
            if success:
                return {"message": f"알림 전송 완료: {stock_code}"}
            else:
                raise HTTPException(status_code=500, detail=f"알림 전송 실패: {stock_code}")
                
    except Exception as e:
        logger.error(f"종목 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alert/multiple")
async def send_multiple_alerts(stock_codes: List[str], background_tasks: BackgroundTasks, days: int = 5):
    """복수 종목 알림 전송"""
    try:
        logger.info(f"복수 종목 알림 요청: {len(stock_codes)}개 종목 ({days}일)")
        
        # 백그라운드 태스크로 실행
        if background_tasks:
            background_tasks.add_task(trend_service.send_multiple_trend_alerts, stock_codes, days)
            return {"message": f"알림 전송 작업이 시작되었습니다: {len(stock_codes)}개 종목"}
        else:
            # 동기 실행
            results = trend_service.send_multiple_trend_alerts(stock_codes, days)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(stock_codes)
            
            return {
                "message": f"알림 전송 완료: {success_count}/{total_count} 성공",
                "results": results
            }
            
    except Exception as e:
        logger.error(f"복수 종목 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alert/popular")
async def send_popular_alerts(background_tasks: BackgroundTasks, market: str = "KOSPI", count: int = 5, days: int = 5):
    """인기 종목 알림 전송"""
    try:
        logger.info(f"인기 종목 알림 요청: {market} {count}개 종목 ({days}일)")
        
        # 인기 종목 조회
        popular_stocks = trend_service.get_popular_stocks(market, count)
        
        # 백그라운드 태스크로 실행
        if background_tasks:
            background_tasks.add_task(trend_service.send_multiple_trend_alerts, popular_stocks, days)
            return {
                "message": f"인기 종목 알림 전송 작업이 시작되었습니다: {len(popular_stocks)}개 종목",
                "stocks": popular_stocks
            }
        else:
            # 동기 실행
            results = trend_service.send_multiple_trend_alerts(popular_stocks, days)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(popular_stocks)
            
            return {
                "message": f"인기 종목 알림 전송 완료: {success_count}/{total_count} 성공",
                "stocks": popular_stocks,
                "results": results
            }
            
    except Exception as e:
        logger.error(f"인기 종목 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stocks/popular")
async def get_popular_stocks(market: str = "KOSPI", count: int = 10):
    """인기 종목 리스트 조회"""
    try:
        logger.info(f"인기 종목 조회 요청: {market} {count}개")
        
        popular_stocks = trend_service.get_popular_stocks(market, count)
        
        # 종목명 추가
        stocks_with_names = []
        for stock_code in popular_stocks:
            stock_name = trend_service.get_stock_name(stock_code)
            stocks_with_names.append({
                "code": stock_code,
                "name": stock_name
            })
        
        return {
            "market": market,
            "count": len(stocks_with_names),
            "stocks": stocks_with_names
        }
        
    except Exception as e:
        logger.error(f"인기 종목 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def run_cli():
    """명령줄 인터페이스 실행"""
    parser = argparse.ArgumentParser(description="주가 추이 분석 서비스")
    
    # 서브커맨드 설정
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령')
    
    # 단일 종목 분석 명령
    analyze_parser = subparsers.add_parser('analyze', help='단일 종목 분석')
    analyze_parser.add_argument('stock_code', help='종목 코드 (예: 005930)')
    analyze_parser.add_argument('--days', type=int, default=5, help='분석 기간 (기본: 5일)')
    
    # 단일 종목 알림 명령
    alert_parser = subparsers.add_parser('alert', help='단일 종목 알림 전송')
    alert_parser.add_argument('stock_code', help='종목 코드 (예: 005930)')
    alert_parser.add_argument('--days', type=int, default=5, help='분석 기간 (기본: 5일)')
    
    # 복수 종목 알림 명령
    multi_alert_parser = subparsers.add_parser('multi-alert', help='복수 종목 알림 전송')
    multi_alert_parser.add_argument('stock_codes', nargs='+', help='종목 코드 리스트 (예: 005930 000660)')
    multi_alert_parser.add_argument('--days', type=int, default=5, help='분석 기간 (기본: 5일)')
    
    # 인기 종목 알림 명령
    popular_parser = subparsers.add_parser('popular', help='인기 종목 알림 전송')
    popular_parser.add_argument('--market', choices=['KOSPI', 'KOSDAQ'], default='KOSPI', help='시장 (기본: KOSPI)')
    popular_parser.add_argument('--count', type=int, default=5, help='종목 수 (기본: 5개)')
    popular_parser.add_argument('--days', type=int, default=5, help='분석 기간 (기본: 5일)')
    
    # 서버 실행 명령
    server_parser = subparsers.add_parser('server', help='API 서버 실행')
    server_parser.add_argument('--host', default='0.0.0.0', help='서버 호스트 (기본: 0.0.0.0)')
    server_parser.add_argument('--port', type=int, default=8000, help='서버 포트 (기본: 8000)')
    
    # 상태 확인 명령
    health_parser = subparsers.add_parser('health', help='서비스 상태 확인')
    
    # 인수 파싱
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'analyze':
            # 단일 종목 분석
            print(f"📊 종목 분석 시작: {args.stock_code} ({args.days}일)")
            analysis = trend_service.analyze_stock_trend(args.stock_code, args.days)
            
            if analysis:
                print(f"✅ 분석 완료: {analysis['stock_name']} ({analysis['stock_code']})")
                print(f"📈 현재가: {analysis['current_price']:,}원")
                print(f"📊 기간 수익률: {analysis['summary']['total_change_rate']:+.2f}%")
                print(f"📊 평균 거래량: {analysis['summary']['avg_volume_man']:,.1f}만주")
                print(f"📊 평균 거래대금: {analysis['summary']['avg_trading_value_eok']:,.1f}억원")
            else:
                print("❌ 분석 실패")
                
        elif args.command == 'alert':
            # 단일 종목 알림
            print(f"📲 종목 알림 전송 시작: {args.stock_code} ({args.days}일)")
            success = trend_service.send_trend_alert(args.stock_code, args.days)
            
            if success:
                print("✅ 알림 전송 완료")
            else:
                print("❌ 알림 전송 실패")
                
        elif args.command == 'multi-alert':
            # 복수 종목 알림
            print(f"📲 복수 종목 알림 전송 시작: {len(args.stock_codes)}개 종목 ({args.days}일)")
            results = trend_service.send_multiple_trend_alerts(args.stock_codes, args.days)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(args.stock_codes)
            
            print(f"✅ 알림 전송 완료: {success_count}/{total_count} 성공")
            
            # 실패한 종목 출력
            failed_stocks = [code for code, success in results.items() if not success]
            if failed_stocks:
                print(f"❌ 실패한 종목: {', '.join(failed_stocks)}")
                
        elif args.command == 'popular':
            # 인기 종목 알림
            print(f"📲 인기 종목 알림 전송 시작: {args.market} {args.count}개 종목 ({args.days}일)")
            
            popular_stocks = trend_service.get_popular_stocks(args.market, args.count)
            print(f"📊 선택된 종목: {', '.join(popular_stocks)}")
            
            results = trend_service.send_multiple_trend_alerts(popular_stocks, args.days)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(popular_stocks)
            
            print(f"✅ 인기 종목 알림 전송 완료: {success_count}/{total_count} 성공")
            
        elif args.command == 'server':
            # API 서버 실행
            print(f"🚀 API 서버 시작: http://{args.host}:{args.port}")
            uvicorn.run(
                "main:app",
                host=args.host,
                port=args.port,
                reload=True,
                log_level="info"
            )
            
        elif args.command == 'health':
            # 상태 확인
            print("🔍 서비스 상태 확인 중...")
            status = trend_service.health_check()
            
            print(f"📊 전체 상태: {status['status']}")
            print(f"📲 텔레그램 상태: {status['telegram_status']['status']}")
            print(f"📈 pykrx 상태: {status['pykrx_status']}")
            print(f"⏰ 확인 시각: {status['timestamp']}")
            
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"CLI 실행 중 오류: {e}")
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    print("🚀 주가 추이 분석 서비스 시작")
    print("=" * 50)
    
    if len(sys.argv) == 1:
        print("사용법:")
        print("  python main.py analyze 005930          # 삼성전자 분석")
        print("  python main.py alert 005930            # 삼성전자 알림")
        print("  python main.py multi-alert 005930 000660  # 복수 종목 알림")
        print("  python main.py popular --market KOSPI  # 인기 종목 알림")
        print("  python main.py server                  # API 서버 실행")
        print("  python main.py health                  # 상태 확인")
        print("=" * 50)
    
    run_cli() 