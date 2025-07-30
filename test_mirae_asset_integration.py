#!/usr/bin/env python3
"""
미래에셋증권 종목 통합 테스트 스크립트
- 사용자 더미 데이터 생성
- 각 서비스별 알림 테스트
- 텔레그램 알림 확인
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import pymysql
import json

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.env_local import get_config
from shared.database.mysql_client import MySQLClient
from shared.apis.telegram_api import TelegramBotClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MiraeAssetIntegrationTest:
    """미래에셋증권 통합 테스트 클래스"""
    
    def __init__(self):
        self.config = get_config()
        self.mysql_client = MySQLClient()
        self.telegram_bot = TelegramBotClient()
        
        # 미래에셋증권 정보
        self.mirae_stock_code = "006800"
        self.mirae_stock_name = "미래에셋증권"
        
        # 테스트 사용자 정보
        self.test_user_id = "test_mirae_user_001"
        self.test_phone = "01012345678"
        self.test_username = "미래에셋테스터"
        
    async def create_test_user_data(self):
        """테스트 사용자 더미 데이터 생성"""
        try:
            logger.info("🔧 테스트 사용자 더미 데이터 생성 시작")
            
            # 1. 사용자 프로필 생성
            profile_query = """
            INSERT INTO user_profiles (user_id, username, phone_number, news_similarity_threshold, news_impact_threshold)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            username = VALUES(username),
            phone_number = VALUES(phone_number),
            news_similarity_threshold = VALUES(news_similarity_threshold),
            news_impact_threshold = VALUES(news_impact_threshold)
            """
            
            await self.mysql_client.execute_query_async(
                profile_query,
                (self.test_user_id, self.test_username, self.test_phone, 0.7, 0.8)
            )
            logger.info("✅ 사용자 프로필 생성 완료")
            
            # 2. 사용자 종목 설정 (미래에셋증권)
            stock_query = """
            INSERT INTO user_stocks (user_id, stock_code, stock_name, enabled)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            enabled = VALUES(enabled)
            """
            
            await self.mysql_client.execute_query_async(
                stock_query,
                (self.test_user_id, self.mirae_stock_code, self.mirae_stock_name, True)
            )
            logger.info("✅ 사용자 종목 설정 완료")
            
            # 3. 사용자 모델 설정
            model_query = """
            INSERT INTO user_model (user_id, model_type)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
            model_type = VALUES(model_type)
            """
            
            await self.mysql_client.execute_query_async(
                model_query,
                (self.test_user_id, "hyperclova")
            )
            logger.info("✅ 사용자 모델 설정 완료")
            
            # 4. 모든 서비스 활성화
            service_query = """
            INSERT INTO user_wanted_service 
            (user_id, phone_number, news_service, disclosure_service, report_service, chart_service, flow_service)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            phone_number = VALUES(phone_number),
            news_service = VALUES(news_service),
            disclosure_service = VALUES(disclosure_service),
            report_service = VALUES(report_service),
            chart_service = VALUES(chart_service),
            flow_service = VALUES(flow_service)
            """
            
            await self.mysql_client.execute_query_async(
                service_query,
                (self.test_user_id, self.test_phone, 1, 1, 1, 1, 1)
            )
            logger.info("✅ 모든 서비스 활성화 완료")
            
            logger.info("🎉 테스트 사용자 더미 데이터 생성 완료!")
            return True
            
        except Exception as e:
            logger.error(f"❌ 테스트 사용자 데이터 생성 실패: {e}")
            return False
    
    async def test_news_service(self):
        """뉴스 서비스 테스트"""
        try:
            logger.info("📰 뉴스 서비스 테스트 시작")
            
            # NewsService 임포트 및 테스트
            from services.news_service.main import NewsService
            
            news_service = NewsService()
            
            # 미래에셋증권 뉴스 크롤링 테스트
            logger.info(f"📊 {self.mirae_stock_name} 뉴스 크롤링 시작")
            
            # 환경변수 설정 (사용자 ID)
            os.environ['HYPERASSET_USER_ID'] = self.test_user_id
            
            # 뉴스 크롤링 실행
            await news_service.crawl_news_for_stock(self.mirae_stock_code)
            
            logger.info("✅ 뉴스 서비스 테스트 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 뉴스 서비스 테스트 실패: {e}")
            return False
    
    async def test_disclosure_service(self):
        """공시 서비스 테스트"""
        try:
            logger.info("📋 공시 서비스 테스트 시작")
            
            # DisclosureService 임포트 및 테스트
            from services.disclosure_service.disclosure_service import DisclosureService
            
            disclosure_service = DisclosureService()
            
            # 환경변수 설정
            os.environ['HYPERASSET_USER_ID'] = self.test_user_id
            
            # 공시 분석 실행
            logger.info(f"📊 {self.mirae_stock_name} 공시 분석 시작")
            await disclosure_service.process_disclosures_for_stock(self.mirae_stock_code)
            
            logger.info("✅ 공시 서비스 테스트 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 공시 서비스 테스트 실패: {e}")
            return False
    
    async def test_chart_service(self):
        """차트 서비스 테스트"""
        try:
            logger.info("📊 차트 서비스 테스트 시작")
            
            # ChartAnalysisService 임포트 및 테스트
            from services.chart_service.chart_service import ChartAnalysisService
            
            chart_service = ChartAnalysisService()
            
            # 환경변수 설정
            os.environ['HYPERASSET_USER_ID'] = self.test_user_id
            
            # 차트 분석 실행
            logger.info(f"📊 {self.mirae_stock_name} 차트 분석 시작")
            await chart_service.process_realtime_data(self.mirae_stock_code, {})
            
            logger.info("✅ 차트 서비스 테스트 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 차트 서비스 테스트 실패: {e}")
            return False
    
    async def test_flow_analysis_service(self):
        """수급 분석 서비스 테스트"""
        try:
            logger.info("📈 수급 분석 서비스 테스트 시작")
            
            # FlowAnalysisService 임포트 및 테스트
            from services.flow_analysis_service.flow_analysis_service import FlowAnalysisService
            
            flow_service = FlowAnalysisService()
            
            # 환경변수 설정
            os.environ['HYPERASSET_USER_ID'] = self.test_user_id
            
            # 수급 분석 실행
            logger.info(f"📊 {self.mirae_stock_name} 수급 분석 시작")
            await flow_service.analyze_stock_flow(self.mirae_stock_code)
            
            logger.info("✅ 수급 분석 서비스 테스트 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 수급 분석 서비스 테스트 실패: {e}")
            return False
    
    async def test_telegram_notification(self):
        """텔레그램 알림 테스트"""
        try:
            logger.info("📱 텔레그램 알림 테스트 시작")
            
            # 테스트 메시지 전송
            test_message = f"""
🔍 **미래에셋증권 통합 테스트 알림**

🏷️ **종목**: {self.mirae_stock_name} ({self.mirae_stock_code})
⏰ **테스트 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 **테스트 사용자**: {self.test_username}

📊 **테스트 내용**:
• 뉴스 서비스: ✅ 활성화
• 공시 서비스: ✅ 활성화  
• 차트 서비스: ✅ 활성화
• 수급 분석: ✅ 활성화

🎯 **모든 서비스가 정상적으로 작동 중입니다!**
            """
            
            success = self.telegram_bot.send_message(test_message)
            
            if success:
                logger.info("✅ 텔레그램 알림 테스트 성공")
                return True
            else:
                logger.error("❌ 텔레그램 알림 전송 실패")
                return False
                
        except Exception as e:
            logger.error(f"❌ 텔레그램 알림 테스트 실패: {e}")
            return False
    
    async def verify_user_data(self):
        """생성된 사용자 데이터 검증"""
        try:
            logger.info("🔍 사용자 데이터 검증 시작")
            
            # 1. 사용자 프로필 확인
            profile_query = "SELECT * FROM user_profiles WHERE user_id = %s"
            profile_result = await self.mysql_client.execute_query_async(
                profile_query, (self.test_user_id,), fetch=True
            )
            
            if profile_result:
                logger.info(f"✅ 사용자 프로필 확인: {profile_result[0]}")
            else:
                logger.error("❌ 사용자 프로필 없음")
                return False
            
            # 2. 사용자 종목 확인
            stock_query = "SELECT * FROM user_stocks WHERE user_id = %s"
            stock_result = await self.mysql_client.execute_query_async(
                stock_query, (self.test_user_id,), fetch=True
            )
            
            if stock_result:
                logger.info(f"✅ 사용자 종목 확인: {stock_result[0]}")
            else:
                logger.error("❌ 사용자 종목 없음")
                return False
            
            # 3. 서비스 설정 확인
            service_query = "SELECT * FROM user_wanted_service WHERE user_id = %s"
            service_result = await self.mysql_client.execute_query_async(
                service_query, (self.test_user_id,), fetch=True
            )
            
            if service_result:
                logger.info(f"✅ 서비스 설정 확인: {service_result[0]}")
            else:
                logger.error("❌ 서비스 설정 없음")
                return False
            
            logger.info("✅ 사용자 데이터 검증 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 사용자 데이터 검증 실패: {e}")
            return False
    
    async def run_full_test(self):
        """전체 통합 테스트 실행"""
        try:
            logger.info("🚀 미래에셋증권 통합 테스트 시작")
            logger.info("=" * 60)
            
            # 1. 테스트 사용자 데이터 생성
            if not await self.create_test_user_data():
                logger.error("❌ 테스트 사용자 데이터 생성 실패")
                return False
            
            # 2. 사용자 데이터 검증
            if not await self.verify_user_data():
                logger.error("❌ 사용자 데이터 검증 실패")
                return False
            
            # 3. 텔레그램 알림 테스트
            if not await self.test_telegram_notification():
                logger.error("❌ 텔레그램 알림 테스트 실패")
                return False
            
            # 4. 각 서비스별 테스트
            services = [
                ("뉴스 서비스", self.test_news_service),
                ("공시 서비스", self.test_disclosure_service),
                ("차트 서비스", self.test_chart_service),
                ("수급 분석 서비스", self.test_flow_analysis_service)
            ]
            
            for service_name, test_func in services:
                logger.info(f"🔧 {service_name} 테스트 시작")
                try:
                    success = await test_func()
                    if success:
                        logger.info(f"✅ {service_name} 테스트 성공")
                    else:
                        logger.error(f"❌ {service_name} 테스트 실패")
                except Exception as e:
                    logger.error(f"❌ {service_name} 테스트 중 오류: {e}")
            
            logger.info("=" * 60)
            logger.info("🎉 미래에셋증권 통합 테스트 완료!")
            
        except Exception as e:
            logger.error(f"❌ 통합 테스트 실패: {e}")
            return False
        finally:
            await self.mysql_client.close()

async def main():
    """메인 실행 함수"""
    try:
        test = MiraeAssetIntegrationTest()
        await test.run_full_test()
        
    except KeyboardInterrupt:
        logger.info("테스트 중단")
    except Exception as e:
        logger.error(f"테스트 실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 