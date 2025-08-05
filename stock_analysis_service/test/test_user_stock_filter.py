#!/usr/bin/env python3
"""
사용자별 종목 필터링 테스트
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.service_config.user_config_loader import UserConfigLoader

async def test_user_stock_filtering():
    """사용자별 종목 필터링 테스트"""
    print("🧪 사용자별 종목 필터링 테스트 시작")
    
    try:
        # UserConfigLoader 초기화
        config_loader = UserConfigLoader()
        
        # 테스트할 종목들
        test_stocks = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "051910",  # LG화학
            "006400",  # 삼성SDI
        ]
        
        # 사용자 ID (테스트용)
        user_id = "1"
        
        print(f"\n📊 사용자 {user_id}의 종목 관심도 테스트:")
        
        for stock_code in test_stocks:
            try:
                # 사용자가 이 종목에 관심이 있는지 확인
                is_interested = await config_loader.is_user_interested_in_stock(user_id, stock_code)
                
                status = "✅ 관심 있음" if is_interested else "❌ 관심 없음"
                print(f"  {stock_code}: {status}")
                
            except Exception as e:
                print(f"  {stock_code}: ❌ 오류 - {e}")
        
        # 사용자 종목 목록 조회 테스트
        print(f"\n📋 사용자 {user_id}의 종목 목록:")
        try:
            user_stocks = await config_loader.get_user_stocks(user_id)
            if user_stocks:
                for stock in user_stocks:
                    enabled_status = "✅ 활성화" if stock.get("enabled", True) else "❌ 비활성화"
                    print(f"  {stock.get('stock_code', 'N/A')} ({stock.get('stock_name', 'N/A')}): {enabled_status}")
            else:
                print("  📝 등록된 종목이 없습니다")
        except Exception as e:
            print(f"  ❌ 종목 목록 조회 실패: {e}")
        
        # 알림 설정 조회 테스트
        print(f"\n🔔 사용자 {user_id}의 알림 설정:")
        try:
            notification_settings = await config_loader.get_user_notification_settings(user_id)
            for setting, value in notification_settings.items():
                status = "✅ 활성화" if value else "❌ 비활성화"
                print(f"  {setting}: {status}")
        except Exception as e:
            print(f"  ❌ 알림 설정 조회 실패: {e}")
        
        print("\n✅ 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_user_stock_filtering()) 