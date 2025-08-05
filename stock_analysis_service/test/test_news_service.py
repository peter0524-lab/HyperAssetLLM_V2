#!/usr/bin/env python3
"""
뉴스 서비스 테스트 스크립트
미래에셋 증권 사용자를 위한 뉴스 크롤링 및 알림 테스트
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from services.news_service.main import NewsService
from shared.user_config.user_config_manager import UserConfigManager
from config.env_local import get_config

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_news_service():
    """뉴스 서비스 테스트"""
    try:
        logger.info("🧪 뉴스 서비스 테스트 시작")
        
        # 환경변수 설정 (미래에셋 사용자)
        os.environ['HYPERASSET_USER_ID'] = 'mirae_user_001'
        
        # 사용자 설정 확인
        user_config_manager = UserConfigManager()
        user_config = await user_config_manager.get_user_config('mirae_user_001')
        
        if not user_config:
            logger.error("❌ 사용자 설정을 찾을 수 없습니다")
            return False
            
        logger.info(f"✅ 사용자 설정 확인: {user_config.get('username', 'N/A')}")
        logger.info(f"📊 관심 종목: {len(user_config.get('stocks', []))}개")
        
        # 뉴스 서비스 초기화
        news_service = NewsService()
        
        # 미래에셋증권 뉴스 크롤링 테스트
        logger.info("📰 미래에셋증권 뉴스 크롤링 테스트...")
        
        # 뉴스 크롤링 실행
        stock_code = "006800"  # 미래에셋증권
        
        # 뉴스 크롤링 메서드 호출
        news_list = news_service.crawl_naver_finance_news(stock_code, pages=1, size=5)
        
        if news_list:
            logger.info(f"✅ 뉴스 크롤링 성공: {len(news_list)}개 뉴스 수집")
            
            # 첫 번째 뉴스 상세 정보 출력
            if news_list:
                first_news = news_list[0]
                logger.info(f"📰 첫 번째 뉴스:")
                logger.info(f"  - 제목: {first_news.get('title', 'N/A')}")
                logger.info(f"  - URL: {first_news.get('url', 'N/A')}")
                logger.info(f"  - 발행일: {first_news.get('published_at', 'N/A')}")
                logger.info(f"  - 출처: {first_news.get('source', 'N/A')}")
        else:
            logger.warning("⚠️ 뉴스 크롤링 결과가 없습니다")
        
        # 뉴스 처리 테스트
        logger.info("🔍 뉴스 처리 테스트...")
        
        if news_list:
            # 첫 번째 뉴스 처리
            test_news = news_list[0]
            test_news['stock_code'] = stock_code
            test_news['stock_name'] = '미래에셋증권'
            
            # 뉴스 처리 메서드 호출
            await news_service.process_news_item(test_news)
            logger.info("✅ 뉴스 처리 완료")
        
        logger.info("✅ 뉴스 서비스 테스트 완료")
        return True
        
    except Exception as e:
        logger.error(f"❌ 뉴스 서비스 테스트 실패: {e}")
        import traceback
        logger.error(f"스택 트레이스: {traceback.format_exc()}")
        return False

async def test_news_alert():
    """뉴스 알림 테스트"""
    try:
        logger.info("🔔 뉴스 알림 테스트 시작")
        
        from shared.apis.telegram_api import TelegramBotClient
        
        # 텔레그램 봇 초기화
        telegram_bot = TelegramBotClient()
        
        # 테스트 메시지 전송
        test_message = """
📰 **미래에셋증권 뉴스 알림 테스트**

🏷️ **종목**: 006800 - 미래에셋증권
📅 **날짜**: 2025-07-30
⭐ **영향도**: 0.85/1.0

📝 **제목**: 미래에셋증권, 신규 투자 계약 체결

📊 **요약**: 미래에셋증권이 새로운 투자 계약을 체결했다. 이번 계약으로 인해 회사의 수익성이 크게 개선될 것으로 예상된다.

🔍 **키워드**: 투자계약, 수익성개선, 미래에셋증권

📈 **과거 사례**: 유사한 투자 계약 체결 시 주가 상승 패턴 관찰

🧪 **테스트 메시지입니다**
        """
        
        # 텔레그램 전송
        success = telegram_bot.send_message(test_message)
        
        if success:
            logger.info("✅ 뉴스 알림 테스트 메시지 전송 성공")
        else:
            logger.error("❌ 뉴스 알림 테스트 메시지 전송 실패")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ 뉴스 알림 테스트 실패: {e}")
        return False

async def main():
    """메인 실행 함수"""
    try:
        logger.info("🚀 미래에셋증권 뉴스 서비스 테스트 시작")
        
        # 1. 뉴스 서비스 테스트
        success = await test_news_service()
        if not success:
            logger.error("❌ 뉴스 서비스 테스트 실패")
            return
        
        # 2. 뉴스 알림 테스트
        success = await test_news_alert()
        if not success:
            logger.error("❌ 뉴스 알림 테스트 실패")
            return
        
        logger.info("✅ 모든 뉴스 서비스 테스트 완료!")
        
    except Exception as e:
        logger.error(f"❌ 테스트 실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 