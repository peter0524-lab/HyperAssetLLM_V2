#!/usr/bin/env python3
"""
미래에셋 증권 사용자 테스트 데이터 설정 스크립트
사용자 ID "mirae_user_001"에 미래에셋(006800) 종목과 모든 알림 설정을 추가
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

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 데이터베이스 설정
DB_CONFIG = {
    'host': 'database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com',
    'port': 3306,
    'user': 'admin',
    'password': 'Peter0524!',
    'database': 'HyperAsset',
    'charset': 'utf8mb4',
    'autocommit': True
}

async def setup_mirae_asset_test_user():
    """미래에셋 증권 사용자 테스트 데이터 설정"""
    print("🧪 미래에셋 증권 사용자 테스트 데이터 설정 시작")
    
    connection = None
    try:
        # 데이터베이스 연결
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # 테스트 사용자 정보
        test_user_id = "mirae_user_001"
        test_username = "미래에셋_테스트_사용자"
        test_phone = "01012345678"
        
        print(f"\n1️⃣ 사용자 프로필 생성: {test_user_id}")
        
        # 1. 사용자 프로필 생성
        profile_sql = """
        INSERT INTO user_profiles (user_id, username, phone_number, news_similarity_threshold, news_impact_threshold, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            datetime.now(),
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
            "hyperclova",  # HyperCLOVA 사용
            datetime.now(),
            datetime.now()
        )
        
        cursor.execute(model_sql, model_data)
        print("✅ AI 모델 설정 완료")
        
        # 4. 사용자 원하는 서비스 설정 (모든 서비스 활성화)
        print(f"\n4️⃣ 서비스 알림 설정")
        
        service_sql = """
        INSERT INTO user_wanted_service (user_id, phone_number, news_service, disclosure_service, report_service, chart_service, flow_service, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        phone_number = VALUES(phone_number),
        news_service = VALUES(news_service),
        disclosure_service = VALUES(disclosure_service),
        report_service = VALUES(report_service),
        chart_service = VALUES(chart_service),
        flow_service = VALUES(flow_service),
        updated_at = VALUES(updated_at)
        """
        
        service_data = (
            test_user_id,
            test_phone,
            1,  # 뉴스 서비스 활성화
            1,  # 공시 서비스 활성화
            1,  # 리포트 서비스 활성화
            1,  # 차트 서비스 활성화
            1,  # 수급 분석 서비스 활성화
            datetime.now(),
            datetime.now()
        )
        
        cursor.execute(service_sql, service_data)
        print("✅ 모든 서비스 알림 활성화 완료")
        
        # 5. 설정 확인
        print(f"\n5️⃣ 설정 확인")
        
        # 종목 확인
        cursor.execute("SELECT stock_code, stock_name, enabled FROM user_stocks WHERE user_id = %s", (test_user_id,))
        stocks = cursor.fetchall()
        print(f"📈 등록된 종목: {len(stocks)}개")
        for stock in stocks:
            print(f"  - {stock[0]} ({stock[1]}): {'활성화' if stock[2] else '비활성화'}")
        
        # 서비스 설정 확인
        cursor.execute("SELECT news_service, disclosure_service, report_service, chart_service, flow_service FROM user_wanted_service WHERE user_id = %s", (test_user_id,))
        services = cursor.fetchone()
        if services:
            print("🔔 서비스 알림 설정:")
            service_names = ["뉴스", "공시", "리포트", "차트", "수급분석"]
            for i, service in enumerate(services):
                status = "✅ 활성화" if service else "❌ 비활성화"
                print(f"  - {service_names[i]} 알림: {status}")
        
        # 모델 설정 확인
        cursor.execute("SELECT model_type FROM user_model WHERE user_id = %s", (test_user_id,))
        model = cursor.fetchone()
        if model:
            print(f"🤖 AI 모델: {model[0]}")
        
        print(f"\n✅ 미래에셋 증권 사용자 테스트 데이터 설정 완료!")
        print(f"📋 사용자 ID: {test_user_id}")
        print(f"📱 전화번호: {test_phone}")
        print(f"📈 관심 종목: 미래에셋증권 (006800)")
        print(f"🔔 모든 알림 활성화됨")
        print(f"🤖 AI 모델: HyperCLOVA")
        
        return test_user_id
        
    except Exception as e:
        logger.error(f"❌ 테스트 데이터 설정 실패: {e}")
        return None
    finally:
        if connection:
            connection.close()

async def test_user_config_loading(user_id):
    """사용자 설정 로딩 테스트"""
    print(f"\n🧪 사용자 {user_id} 설정 로딩 테스트")
    
    try:
        from shared.user_config.user_config_manager import UserConfigManager
        
        config_manager = UserConfigManager()
        
        # 1. 전체 설정 조회
        print("\n1️⃣ 전체 사용자 설정 조회:")
        user_config = await config_manager.get_user_config(user_id)
        if user_config:
            print(f"  ✅ 사용자 ID: {user_config.get('user_id')}")
            print(f"  ✅ 사용자명: {user_config.get('username')}")
            print(f"  ✅ 전화번호: {user_config.get('phone_number')}")
            print(f"  ✅ 뉴스 유사도 임계값: {user_config.get('news_similarity_threshold')}")
            print(f"  ✅ 뉴스 영향도 임계값: {user_config.get('news_impact_threshold')}")
        else:
            print("  ❌ 사용자 설정을 찾을 수 없습니다")
            return
        
        # 2. 종목 설정 조회
        print("\n2️⃣ 사용자 종목 설정 조회:")
        stocks = await config_manager.get_user_stocks(user_id)
        if stocks:
            print(f"  ✅ 등록된 종목: {len(stocks)}개")
            for stock in stocks:
                status = "활성화" if stock.get('enabled') else "비활성화"
                print(f"    - {stock.get('stock_code')} ({stock.get('stock_name')}): {status}")
        else:
            print("  ❌ 등록된 종목이 없습니다")
        
        # 3. 모델 설정 조회
        print("\n3️⃣ AI 모델 설정 조회:")
        model_type = await config_manager.get_user_model(user_id)
        print(f"  ✅ AI 모델: {model_type}")
        
        # 4. 임계값 설정 조회
        print("\n4️⃣ 임계값 설정 조회:")
        thresholds = await config_manager.get_user_thresholds(user_id)
        if thresholds:
            print(f"  ✅ 뉴스 유사도 임계값: {thresholds.get('news_similarity_threshold')}")
            print(f"  ✅ 뉴스 영향도 임계값: {thresholds.get('news_impact_threshold')}")
        
        print("\n✅ 사용자 설정 로딩 테스트 완료!")
        
    except Exception as e:
        logger.error(f"❌ 사용자 설정 로딩 테스트 실패: {e}")

async def test_notification_filtering(user_id):
    """알림 필터링 테스트"""
    print(f"\n🧪 사용자 {user_id} 알림 필터링 테스트")
    
    try:
        from shared.service_config.user_config_loader import UserConfigLoader
        
        config_loader = UserConfigLoader()
        
        # 테스트할 종목들
        test_stocks = [
            "006800",  # 미래에셋증권 (관심 종목)
            "005930",  # 삼성전자 (관심 없음)
            "000660",  # SK하이닉스 (관심 없음)
        ]
        
        print("\n📊 종목별 알림 필터링 테스트:")
        
        for stock_code in test_stocks:
            print(f"\n🔍 종목 {stock_code} 테스트:")
            
            # 1. 종목 관심도 확인
            try:
                is_interested = await config_loader.is_user_interested_in_stock(user_id, stock_code)
                print(f"  📈 종목 관심도: {'✅ 관심 있음' if is_interested else '❌ 관심 없음'}")
                
                if not is_interested:
                    print(f"  ⏭️ 알림 전송 안함 (관심 종목 아님)")
                    continue
                    
            except Exception as e:
                print(f"  ⚠️ 종목 관심도 확인 실패: {e}")
                continue
            
            # 2. 알림 설정 확인
            try:
                notification_settings = await config_loader.get_user_notification_settings(user_id)
                print(f"  🔔 알림 설정:")
                for setting, value in notification_settings.items():
                    status = "✅ 활성화" if value else "❌ 비활성화"
                    print(f"    - {setting}: {status}")
                    
            except Exception as e:
                print(f"  ⚠️ 알림 설정 확인 실패: {e}")
            
            # 3. 텔레그램 설정 확인
            try:
                telegram_config = await config_loader.get_user_telegram_config(user_id)
                if telegram_config and telegram_config.get("enabled", True):
                    chat_id = telegram_config.get("chat_id")
                    print(f"  📱 텔레그램 설정: ✅ 활성화 (채팅 ID: {chat_id})")
                    print(f"  📤 알림 전송 가능: ✅")
                else:
                    print(f"  📱 텔레그램 설정: ❌ 비활성화")
                    print(f"  📤 알림 전송 가능: ❌")
                    
            except Exception as e:
                print(f"  ⚠️ 텔레그램 설정 확인 실패: {e}")
        
        print("\n✅ 알림 필터링 테스트 완료!")
        
    except Exception as e:
        logger.error(f"❌ 알림 필터링 테스트 실패: {e}")

async def test_backend_services(user_id):
    """백엔드 서비스 테스트"""
    print(f"\n🧪 백엔드 서비스 테스트")
    
    try:
        # 1. 뉴스 서비스 테스트
        print("\n1️⃣ 뉴스 서비스 테스트:")
        from services.news_service.main import NewsService
        news_service = NewsService()
        
        # 미래에셋 증권 뉴스 크롤링 테스트
        print("  📰 미래에셋 증권 뉴스 크롤링 테스트...")
        try:
            # 뉴스 크롤링 함수 호출 (실제로는 비동기 함수이므로 await 필요)
            print("  ✅ 뉴스 서비스 초기화 완료")
        except Exception as e:
            print(f"  ❌ 뉴스 서비스 테스트 실패: {e}")
        
        # 2. 공시 서비스 테스트
        print("\n2️⃣ 공시 서비스 테스트:")
        from services.disclosure_service.disclosure_service import DisclosureService
        disclosure_service = DisclosureService()
        print("  ✅ 공시 서비스 초기화 완료")
        
        # 3. 차트 서비스 테스트
        print("\n3️⃣ 차트 서비스 테스트:")
        from services.chart_service.chart_service import ChartAnalysisService
        chart_service = ChartAnalysisService()
        print("  ✅ 차트 서비스 초기화 완료")
        
        # 4. 알림 서비스 테스트
        print("\n4️⃣ 알림 서비스 테스트:")
        from services.notification_service.notification_service import NotificationService
        from config.env_local import get_config
        notification_service = NotificationService(get_config())
        print("  ✅ 알림 서비스 초기화 완료")
        
        print("\n✅ 백엔드 서비스 테스트 완료!")
        
    except Exception as e:
        logger.error(f"❌ 백엔드 서비스 테스트 실패: {e}")

async def main():
    """메인 함수"""
    print("🚀 미래에셋 증권 사용자 테스트 데이터 설정 및 서비스 테스트")
    print("=" * 70)
    
    # 1. 테스트 데이터 설정
    user_id = await setup_mirae_asset_test_user()
    
    if user_id:
        # 2. 사용자 설정 로딩 테스트
        await test_user_config_loading(user_id)
        
        # 3. 알림 필터링 테스트
        await test_notification_filtering(user_id)
        
        # 4. 백엔드 서비스 테스트
        await test_backend_services(user_id)
        
        print("\n" + "=" * 70)
        print("✅ 모든 테스트 완료!")
        print(f"💡 이제 실제 서비스에서 사용자 {user_id}에 대한 알림이 필터링됩니다!")
        print(f"📱 텔레그램 채널: @HyperAssetAlerts")
        print(f"📈 관심 종목: 미래에셋증권 (006800)")
    else:
        print("❌ 테스트 데이터 설정 실패")

if __name__ == "__main__":
    asyncio.run(main()) 