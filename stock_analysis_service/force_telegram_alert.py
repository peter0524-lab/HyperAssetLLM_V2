#!/usr/bin/env python3
"""
강제 텔레그램 알림 발생 스크립트
실제 서비스들이 알림을 보내는지 확인하기 위해 테스트 데이터를 생성하고 알림을 발생시킨다.
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.apis.telegram_api import TelegramBotClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def force_disclosure_alert():
    """강제 공시 알림 발생"""
    try:
        logger.info("🔔 강제 공시 알림 발생 시작")
        
        mysql_client = get_mysql_client()
        
        # 새로운 공시 데이터 생성 (강제로 중요 공시)
        new_disclosure = {
            "rcept_no": f"20250730{datetime.now().strftime('%H%M%S')}",
            "corp_name": "미래에셋증권",
            "corp_code": "00111722",
            "stock_code": "006800",
            "report_nm": "[긴급] 미래에셋증권, 대규모 투자 확대 결정",
            "flr_nm": "미래에셋증권",
            "rcept_dt": datetime.now().date(),
            "rm": "AI 기술 투자 확대 및 신규 사업 진출 결정",
            "summary": "미래에셋증권이 AI 기술 투자를 대폭 확대하고 신규 사업에 진출한다고 발표했다.",
            "impact_score": 0.95,  # 매우 높은 영향도
            "sentiment": "positive",
            "sentiment_reason": "대규모 투자 확대로 인한 성장 기대",
            "expected_impact": "positive",
            "impact_duration": "long",
            "keywords": "AI,투자,확대,신규사업,성장",
            "created_at": datetime.now()
        }
        
        # 공시 데이터 삽입
        insert_query = """
        INSERT INTO disclosure_history (rcept_no, corp_name, corp_code, stock_code, 
                                     report_nm, flr_nm, rcept_dt, rm, summary, impact_score,
                                     sentiment, sentiment_reason, expected_impact, 
                                     impact_duration, keywords, created_at)
        VALUES (%(rcept_no)s, %(corp_name)s, %(corp_code)s, %(stock_code)s,
                %(report_nm)s, %(flr_nm)s, %(rcept_dt)s, %(rm)s, %(summary)s, %(impact_score)s,
                %(sentiment)s, %(sentiment_reason)s, %(expected_impact)s,
                %(impact_duration)s, %(keywords)s, %(created_at)s)
        """
        
        mysql_client.execute_query(insert_query, new_disclosure)
        logger.info("✅ 강제 공시 데이터 삽입 완료")
        
        # 공시 서비스 실행
        from services.disclosure_service.disclosure_service import execute_disclosure_analysis
        result = await execute_disclosure_analysis()
        
        logger.info(f"📊 공시 서비스 실행 결과: {result}")
        
        if result and result.get("success"):
            logger.info("✅ 강제 공시 알림 발생 성공!")
            return True
        else:
            logger.warning("⚠️ 강제 공시 알림 발생 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ 강제 공시 알림 발생 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def force_chart_alert():
    """강제 차트 알림 발생"""
    try:
        logger.info("🔔 강제 차트 알림 발생 시작")
        
        mysql_client = get_mysql_client()
        
        # 차트 조건 데이터 생성 (골든크로스 발생)
        chart_condition = {
            "stock_code": "006800",
            "condition_name": "golden_cross",
            "condition_result": True,
            "condition_data": '{"ma5": 15000, "ma20": 14800, "crossover_point": 14900}',
            "adj_close": 15000,
            "created_at": datetime.now()
        }
        
        # 차트 조건 데이터 삽입
        insert_query = """
        INSERT INTO chart_conditions (stock_code, condition_name, condition_result, 
                                    condition_data, adj_close, created_at)
        VALUES (%(stock_code)s, %(condition_name)s, %(condition_result)s,
                %(condition_data)s, %(adj_close)s, %(created_at)s)
        """
        
        mysql_client.execute_query(insert_query, chart_condition)
        logger.info("✅ 강제 차트 조건 데이터 삽입 완료")
        
        # 차트 서비스 실행
        from services.chart_service.chart_service import execute_chart_analysis
        result = await execute_chart_analysis()
        
        logger.info(f"📊 차트 서비스 실행 결과: {result}")
        
        if result and result.get("success"):
            logger.info("✅ 강제 차트 알림 발생 성공!")
            return True
        else:
            logger.warning("⚠️ 강제 차트 알림 발생 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ 강제 차트 알림 발생 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def force_flow_alert():
    """강제 수급 분석 알림 발생"""
    try:
        logger.info("🔔 강제 수급 분석 알림 발생 시작")
        
        mysql_client = get_mysql_client()
        
        # 수급 데이터 생성 (복합 신호 발생)
        # 실제로는 더 복잡한 데이터가 필요하지만, 테스트용으로 간단하게 생성
        
        # 수급 분석 서비스 실행
        from services.flow_analysis_service.flow_analysis_service import execute_eod_processing
        result = await execute_eod_processing()
        
        logger.info(f"📊 수급 분석 서비스 실행 결과: {result}")
        
        if result and result.get("success"):
            logger.info("✅ 강제 수급 분석 알림 발생 성공!")
            return True
        else:
            logger.warning("⚠️ 강제 수급 분석 알림 발생 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ 강제 수급 분석 알림 발생 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def send_direct_test_alert():
    """직접 테스트 알림 전송"""
    try:
        logger.info("🔔 직접 테스트 알림 전송 시작")
        
        telegram_bot = TelegramBotClient()
        
        test_message = f"""
🚨 **강제 알림 테스트** 🚨

📊 **서비스**: 강제 알림 테스트
🏢 **종목**: 미래에셋증권 (006800)
📅 **시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💡 **내용**: 이 메시지는 강제 알림 테스트입니다!

🔔 **공시**: 대규모 투자 확대 결정
📈 **차트**: 골든크로스 발생
💰 **수급**: 복합 신호 발생

✅ **강제 알림 테스트 성공**
        """
        
        result = telegram_bot.send_message(test_message)
        
        if result:
            logger.info("✅ 직접 테스트 알림 전송 성공!")
            return True
        else:
            logger.error("❌ 직접 테스트 알림 전송 실패!")
            return False
            
    except Exception as e:
        logger.error(f"❌ 직접 테스트 알림 전송 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 함수"""
    logger.info("🚀 강제 텔레그램 알림 발생 시작")
    logger.info("=" * 80)
    
    # 1. 직접 테스트 알림
    direct_success = await send_direct_test_alert()
    
    logger.info("\n" + "=" * 80)
    
    # 2. 강제 공시 알림
    disclosure_success = await force_disclosure_alert()
    
    logger.info("\n" + "=" * 80)
    
    # 3. 강제 차트 알림
    chart_success = await force_chart_alert()
    
    logger.info("\n" + "=" * 80)
    
    # 4. 강제 수급 분석 알림
    flow_success = await force_flow_alert()
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 강제 알림 발생 결과 요약")
    logger.info("=" * 80)
    
    results = [
        ("직접 테스트 알림", direct_success),
        ("강제 공시 알림", disclosure_success),
        ("강제 차트 알림", chart_success),
        ("강제 수급 분석 알림", flow_success)
    ]
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for service_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        logger.info(f"{status}: {service_name}")
    
    logger.info(f"\n📈 성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        logger.info("🎉 모든 강제 알림이 성공적으로 발생했습니다!")
        logger.info("📱 텔레그램 채팅방을 확인해주세요!")
    else:
        logger.info("⚠️ 일부 강제 알림에 문제가 있습니다.")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(main()) 