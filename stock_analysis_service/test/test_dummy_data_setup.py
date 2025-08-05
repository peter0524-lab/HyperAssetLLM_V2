#!/usr/bin/env python3
"""
미래에셋 증권 사용자 더미 데이터 설정 및 테스트 스크립트
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from config.env_local import get_config

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def setup_dummy_data():
    """더미 데이터 설정"""
    try:
        logger.info("🧪 미래에셋 증권 사용자 더미 데이터 설정 시작")
        
        # MySQL 클라이언트 초기화
        mysql_client = get_mysql_client()
        
        # 1. 사용자 프로필 생성
        logger.info("1️⃣ 사용자 프로필 생성...")
        profile_query = """
        INSERT INTO HyperAsset.user_profiles (
            user_id, username, phone_number, 
            news_similarity_threshold, news_impact_threshold
        ) VALUES (
            'mirae_user_001', '미래에셋_테스트_사용자', '01012345678',
            0.7, 0.8
        ) ON DUPLICATE KEY UPDATE
            username = VALUES(username),
            phone_number = VALUES(phone_number),
            news_similarity_threshold = VALUES(news_similarity_threshold),
            news_impact_threshold = VALUES(news_impact_threshold)
        """
        
        await mysql_client.execute_query_async(profile_query)
        logger.info("✅ 사용자 프로필 생성 완료")
        
        # 2. 사용자 종목 설정 (미래에셋증권)
        logger.info("2️⃣ 미래에셋증권 종목 설정...")
        stock_query = """
        INSERT INTO HyperAsset.user_stocks (
            user_id, stock_code, stock_name, enabled
        ) VALUES (
            'mirae_user_001', '006800', '미래에셋증권', 1
        ) ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            enabled = VALUES(enabled)
        """
        
        await mysql_client.execute_query_async(stock_query)
        logger.info("✅ 미래에셋증권 종목 설정 완료")
        
        # 3. 사용자 모델 설정
        logger.info("3️⃣ 사용자 모델 설정...")
        model_query = """
        INSERT INTO HyperAsset.user_model (
            user_id, model_type
        ) VALUES (
            'mirae_user_001', 'hyperclova'
        ) ON DUPLICATE KEY UPDATE
            model_type = VALUES(model_type)
        """
        
        await mysql_client.execute_query_async(model_query)
        logger.info("✅ 사용자 모델 설정 완료")
        
        # 4. 사용자 원하는 서비스 설정 (모든 서비스 활성화)
        logger.info("4️⃣ 모든 서비스 활성화...")
        service_query = """
        INSERT INTO HyperAsset.user_wanted_service (
            user_id, phone_number, news_service, disclosure_service,
            report_service, chart_service, flow_service
        ) VALUES (
            'mirae_user_001', '01012345678', 1, 1, 1, 1, 1
        ) ON DUPLICATE KEY UPDATE
            phone_number = VALUES(phone_number),
            news_service = VALUES(news_service),
            disclosure_service = VALUES(disclosure_service),
            report_service = VALUES(report_service),
            chart_service = VALUES(chart_service),
            flow_service = VALUES(flow_service)
        """
        
        await mysql_client.execute_query_async(service_query)
        logger.info("✅ 모든 서비스 활성화 완료")
        
        # 5. 데이터 확인
        logger.info("5️⃣ 설정된 데이터 확인...")
        check_query = """
        SELECT 
            'user_profiles' as table_name, COUNT(*) as count 
        FROM HyperAsset.user_profiles 
        WHERE user_id = 'mirae_user_001'
        UNION ALL
        SELECT 'user_stocks', COUNT(*) 
        FROM HyperAsset.user_stocks 
        WHERE user_id = 'mirae_user_001'
        UNION ALL
        SELECT 'user_model', COUNT(*) 
        FROM HyperAsset.user_model 
        WHERE user_id = 'mirae_user_001'
        UNION ALL
        SELECT 'user_wanted_service', COUNT(*) 
        FROM HyperAsset.user_wanted_service 
        WHERE user_id = 'mirae_user_001'
        """
        
        result = await mysql_client.execute_query_async(check_query, fetch=True)
        for row in result:
            logger.info(f"📊 {row['table_name']}: {row['count']}개 레코드")
        
        logger.info("✅ 더미 데이터 설정 완료!")
        logger.info("📈 테스트 사용자: mirae_user_001")
        logger.info("📈 관심 종목: 미래에셋증권 (006800)")
        logger.info("📈 활성화된 서비스: 뉴스, 공시, 리포트, 차트, 수급분석")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 더미 데이터 설정 실패: {e}")
        return False

async def test_user_config():
    """사용자 설정 테스트"""
    try:
        logger.info("🧪 사용자 설정 테스트 시작")
        
        from shared.user_config.user_config_manager import UserConfigManager
        
        # 사용자 설정 관리자 초기화
        user_config_manager = UserConfigManager()
        
        # 사용자 설정 조회
        user_config = await user_config_manager.get_user_config('mirae_user_001')
        
        if user_config:
            logger.info("✅ 사용자 설정 조회 성공")
            logger.info(f"📊 사용자명: {user_config.get('username', 'N/A')}")
            logger.info(f"📊 종목 수: {len(user_config.get('stocks', []))}")
            logger.info(f"📊 모델 타입: {user_config.get('model_type', 'N/A')}")
            
            # 종목 정보 출력
            stocks = user_config.get('stocks', [])
            for stock in stocks:
                logger.info(f"📈 종목: {stock.get('stock_name', 'N/A')} ({stock.get('stock_code', 'N/A')})")
        else:
            logger.error("❌ 사용자 설정 조회 실패")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ 사용자 설정 테스트 실패: {e}")
        return False

async def main():
    """메인 실행 함수"""
    try:
        logger.info("🚀 미래에셋 증권 사용자 테스트 시작")
        
        # 1. 더미 데이터 설정
        success = await setup_dummy_data()
        if not success:
            logger.error("❌ 더미 데이터 설정 실패")
            return
        
        # 2. 사용자 설정 테스트
        success = await test_user_config()
        if not success:
            logger.error("❌ 사용자 설정 테스트 실패")
            return
        
        logger.info("✅ 모든 테스트 완료!")
        
    except Exception as e:
        logger.error(f"❌ 테스트 실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 