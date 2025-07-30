#!/usr/bin/env python3
"""
텔레그램 알림 디버깅 스크립트
실제 서비스들이 텔레그램 알림을 보내는지 자세히 확인
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.apis.telegram_api import TelegramBotClient
from services.disclosure_service.disclosure_service import execute_disclosure_analysis
from services.chart_service.chart_service import execute_chart_analysis
from services.flow_analysis_service.flow_analysis_service import execute_eod_processing

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_telegram_bot_direct():
    """텔레그램 봇 직접 테스트"""
    try:
        logger.info("🔔 텔레그램 봇 직접 테스트 시작")
        
        telegram_bot = TelegramBotClient()
        
        # 테스트 메시지
        test_message = f"""
🔔 **디버깅 테스트 알림** 🔔

📊 **서비스**: 디버깅 테스트
🏢 **종목**: 미래에셋증권 (006800)
📅 **시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💡 **내용**: 이 메시지가 보이면 텔레그램 봇이 정상 작동합니다!

✅ **디버깅 테스트 성공**
        """
        
        logger.info("📤 텔레그램 메시지 전송 중...")
        
        # 동기 방식으로 메시지 전송
        result = telegram_bot.send_message(test_message)
        
        if result:
            logger.info("✅ 텔레그램 메시지 전송 성공!")
            logger.info("📱 텔레그램 채팅방을 확인해주세요.")
            return True
        else:
            logger.error("❌ 텔레그램 메시지 전송 실패!")
            return False
            
    except Exception as e:
        logger.error(f"❌ 텔레그램 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_disclosure_service_with_debug():
    """공시 서비스 디버깅 테스트"""
    try:
        logger.info("🔍 공시 서비스 디버깅 테스트 시작")
        
        # 공시 서비스 실행
        result = await execute_disclosure_analysis()
        
        logger.info(f"📊 공시 서비스 실행 결과: {result}")
        
        if result and result.get("success"):
            logger.info("✅ 공시 서비스 실행 성공!")
            logger.info("📱 텔레그램 채팅방에서 공시 알림을 확인해주세요.")
            return True
        else:
            logger.warning("⚠️ 공시 서비스 실행 결과가 예상과 다릅니다.")
            return False
            
    except Exception as e:
        logger.error(f"❌ 공시 서비스 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_chart_service_with_debug():
    """차트 서비스 디버깅 테스트"""
    try:
        logger.info("🔍 차트 서비스 디버깅 테스트 시작")
        
        # 차트 서비스 실행
        result = await execute_chart_analysis()
        
        logger.info(f"📊 차트 서비스 실행 결과: {result}")
        
        if result and result.get("success"):
            logger.info("✅ 차트 서비스 실행 성공!")
            logger.info("📱 텔레그램 채팅방에서 차트 알림을 확인해주세요.")
            return True
        else:
            logger.warning("⚠️ 차트 서비스 실행 결과가 예상과 다릅니다.")
            return False
            
    except Exception as e:
        logger.error(f"❌ 차트 서비스 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_flow_service_with_debug():
    """수급 분석 서비스 디버깅 테스트"""
    try:
        logger.info("🔍 수급 분석 서비스 디버깅 테스트 시작")
        
        # 수급 분석 서비스 실행
        result = await execute_eod_processing()
        
        logger.info(f"📊 수급 분석 서비스 실행 결과: {result}")
        
        if result and result.get("success"):
            logger.info("✅ 수급 분석 서비스 실행 성공!")
            logger.info("📱 텔레그램 채팅방에서 수급 분석 알림을 확인해주세요.")
            return True
        else:
            logger.warning("⚠️ 수급 분석 서비스 실행 결과가 예상과 다릅니다.")
            return False
            
    except Exception as e:
        logger.error(f"❌ 수급 분석 서비스 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 함수"""
    logger.info("🚀 텔레그램 알림 디버깅 시작")
    logger.info("=" * 80)
    
    # 1. 텔레그램 봇 직접 테스트
    telegram_success = await test_telegram_bot_direct()
    
    logger.info("\n" + "=" * 80)
    
    # 2. 공시 서비스 디버깅
    disclosure_success = await test_disclosure_service_with_debug()
    
    logger.info("\n" + "=" * 80)
    
    # 3. 차트 서비스 디버깅
    chart_success = await test_chart_service_with_debug()
    
    logger.info("\n" + "=" * 80)
    
    # 4. 수급 분석 서비스 디버깅
    flow_success = await test_flow_service_with_debug()
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 디버깅 결과 요약")
    logger.info("=" * 80)
    
    results = [
        ("텔레그램 봇", telegram_success),
        ("공시 서비스", disclosure_success),
        ("차트 서비스", chart_success),
        ("수급 분석 서비스", flow_success)
    ]
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for service_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        logger.info(f"{status}: {service_name}")
    
    logger.info(f"\n📈 성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        logger.info("🎉 모든 서비스가 정상 작동합니다!")
    else:
        logger.info("⚠️ 일부 서비스에 문제가 있습니다.")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(main()) 