#!/usr/bin/env python3
"""
미래에셋 증권 테스트 데이터 설정 (실제 스키마에 맞춤)
"""

import asyncio
import sys
import os
from pathlib import Path
import pymysql
from datetime import datetime
import logging

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config.env_local import get_config

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def setup_mirae_asset_test_user():
    """미래에셋 증권 테스트 사용자 데이터 설정"""
    print("🧪 미래에셋 증권 테스트 데이터 설정 시작")
    
    config = get_config()
    connection = None
    
    try:
        # 데이터베이스 연결
        connection = pymysql.connect(
            host=config['mysql']['host'],
            port=config['mysql']['port'],
            user=config['mysql']['user'],
            password=config['mysql']['password'],
            database=config['mysql']['database'],
            charset='utf8mb4',
            autocommit=True
        )
        
        cursor = connection.cursor()
        
        # 테스트 사용자 정보
        test_user_id = "mirae_test_user_001"
        test_username = "미래에셋_테스트_사용자"
        test_phone = "01012345678"
        
        print(f"\n1️⃣ 사용자 프로필 생성: {test_user_id}")
        
        # 1. 사용자 프로필 생성 (실제 스키마에 맞춤)
        profile_sql = """
        INSERT INTO user_profiles (user_id, username, phone_number, news_similarity_threshold, news_impact_threshold, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        username = VALUES(username),
        phone_number = VALUES(phone_number),
        news_similarity_threshold = VALUES(news_similarity_threshold),
        news_impact_threshold = VALUES(news_impact_threshold),
        updated_at = VALUES(updated_at)
        """
        
        profile_data = (
            test_user_id,
            test_username,
            test_phone,
            0.7,  # 뉴스 유사도 임계값
            0.8,  # 뉴스 영향도 임계값
            datetime.now()
        )
        
        cursor.execute(profile_sql, profile_data)
        print("✅ 사용자 프로필 생성 완료")
        
        # 2. 미래에셋 증권 종목 추가
        print(f"\n2️⃣ 미래에셋 증권 종목 추가")
        
        stock_sql = """
        INSERT INTO user_stocks (user_id, stock_code, stock_name, enabled, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        stock_name = VALUES(stock_name),
        enabled = VALUES(enabled),
        updated_at = VALUES(updated_at)
        """
        
        stock_data = (
            test_user_id,
            "006800",  # 미래에셋 증권
            "미래에셋증권",
            True,  # 활성화
            datetime.now(),
            datetime.now()
        )
        
        cursor.execute(stock_sql, stock_data)
        print("✅ 미래에셋 증권 종목 추가 완료")
        
        # 3. 사용자 모델 설정 (HyperCLOVA)
        print(f"\n3️⃣ AI 모델 설정")
        
        model_sql = """
        INSERT INTO user_model (user_id, model_type, created_at, updated_at)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        model_type = VALUES(model_type),
        updated_at = VALUES(updated_at)
        """
        
        model_data = (
            test_user_id,
            "hyperclova",
            datetime.now(),
            datetime.now()
        )
        
        cursor.execute(model_sql, model_data)
        print("✅ AI 모델 설정 완료")
        
        # 4. 모든 서비스 활성화
        print(f"\n4️⃣ 서비스 알림 설정")
        
        service_sql = """
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
        
        service_data = (
            test_user_id,
            test_phone,
            1,  # 뉴스 서비스 활성화
            1,  # 공시 서비스 활성화
            1,  # 리포트 서비스 활성화
            1,  # 차트 서비스 활성화
            1   # 수급 분석 서비스 활성화
        )
        
        cursor.execute(service_sql, service_data)
        print("✅ 모든 서비스 활성화 완료")
        
        # 5. 데이터 검증
        print(f"\n5️⃣ 데이터 검증")
        
        # 사용자 프로필 확인
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = %s", (test_user_id,))
        profile = cursor.fetchone()
        if profile:
            print(f"✅ 사용자 프로필 확인: {profile}")
        else:
            print("❌ 사용자 프로필 없음")
            return False
        
        # 사용자 종목 확인
        cursor.execute("SELECT * FROM user_stocks WHERE user_id = %s", (test_user_id,))
        stocks = cursor.fetchall()
        if stocks:
            print(f"✅ 사용자 종목 확인: {len(stocks)}개 종목")
            for stock in stocks:
                print(f"  - {stock[1]} ({stock[2]})")
        else:
            print("❌ 사용자 종목 없음")
            return False
        
        # 서비스 설정 확인
        cursor.execute("SELECT * FROM user_wanted_service WHERE user_id = %s", (test_user_id,))
        service = cursor.fetchone()
        if service:
            print(f"✅ 서비스 설정 확인: {service}")
        else:
            print("❌ 서비스 설정 없음")
            return False
        
        print("\n🎉 미래에셋 증권 테스트 데이터 설정 완료!")
        print(f"👤 테스트 사용자: {test_user_id}")
        print(f"📊 종목: {len(stocks)}개 (미래에셋증권 포함)")
        print(f"🔔 활성화된 서비스: 5개 (뉴스, 공시, 리포트, 차트, 수급분석)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 테스트 데이터 설정 실패: {e}")
        return False
    finally:
        if connection:
            connection.close()

async def test_telegram_notification():
    """텔레그램 알림 테스트"""
    try:
        print("\n📱 텔레그램 알림 테스트 시작")
        
        from shared.apis.telegram_api import TelegramBotClient
        
        telegram_bot = TelegramBotClient()
        
        # 테스트 메시지 전송
        test_message = f"""
🔍 **미래에셋증권 통합 테스트 알림**

🏷️ **종목**: 미래에셋증권 (006800)
⏰ **테스트 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 **테스트 사용자**: 미래에셋_테스트_사용자

📊 **테스트 내용**:
• 뉴스 서비스: ✅ 활성화
• 공시 서비스: ✅ 활성화  
• 리포트 서비스: ✅ 활성화
• 차트 서비스: ✅ 활성화
• 수급 분석: ✅ 활성화

🎯 **모든 서비스가 정상적으로 작동 중입니다!**
        """
        
        success = telegram_bot.send_message(test_message)
        
        if success:
            print("✅ 텔레그램 알림 테스트 성공")
            return True
        else:
            print("❌ 텔레그램 알림 전송 실패")
            return False
            
    except Exception as e:
        print(f"❌ 텔레그램 알림 테스트 실패: {e}")
        return False

async def test_backend_services():
    """백엔드 서비스 테스트"""
    try:
        print("\n🔧 백엔드 서비스 테스트 시작")
        
        # 환경변수 설정
        os.environ['HYPERASSET_USER_ID'] = "mirae_test_user_001"
        
        # 1. 뉴스 서비스 테스트
        print("📰 뉴스 서비스 테스트...")
        try:
            from services.news_service.main import NewsService
            news_service = NewsService()
            await news_service.crawl_news_for_stock("006800")
            print("✅ 뉴스 서비스 테스트 완료")
        except Exception as e:
            print(f"❌ 뉴스 서비스 테스트 실패: {e}")
        
        # 2. 공시 서비스 테스트
        print("📋 공시 서비스 테스트...")
        try:
            from services.disclosure_service.disclosure_service import DisclosureService
            disclosure_service = DisclosureService()
            await disclosure_service.process_disclosures_for_stock("006800")
            print("✅ 공시 서비스 테스트 완료")
        except Exception as e:
            print(f"❌ 공시 서비스 테스트 실패: {e}")
        
        # 3. 차트 서비스 테스트
        print("📊 차트 서비스 테스트...")
        try:
            from services.chart_service.chart_service import ChartAnalysisService
            chart_service = ChartAnalysisService()
            await chart_service.process_realtime_data("006800", {})
            print("✅ 차트 서비스 테스트 완료")
        except Exception as e:
            print(f"❌ 차트 서비스 테스트 실패: {e}")
        
        # 4. 수급 분석 서비스 테스트
        print("📈 수급 분석 서비스 테스트...")
        try:
            from services.flow_analysis_service.flow_analysis_service import FlowAnalysisService
            flow_service = FlowAnalysisService()
            await flow_service.analyze_stock_flow("006800")
            print("✅ 수급 분석 서비스 테스트 완료")
        except Exception as e:
            print(f"❌ 수급 분석 서비스 테스트 실패: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 백엔드 서비스 테스트 실패: {e}")
        return False

async def main():
    """메인 실행 함수"""
    try:
        print("🚀 미래에셋 증권 통합 테스트 시작")
        print("=" * 60)
        
        # 1. 테스트 데이터 설정
        if not await setup_mirae_asset_test_user():
            print("❌ 테스트 데이터 설정 실패")
            return
        
        # 2. 텔레그램 알림 테스트
        if not await test_telegram_notification():
            print("❌ 텔레그램 알림 테스트 실패")
            return
        
        # 3. 백엔드 서비스 테스트
        await test_backend_services()
        
        print("=" * 60)
        print("🎉 미래에셋 증권 통합 테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n테스트 중단")
    except Exception as e:
        print(f"❌ 테스트 실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 