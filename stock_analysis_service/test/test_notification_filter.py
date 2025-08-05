#!/usr/bin/env python3
"""
실제 알림 필터링 로직 테스트
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.service_config.user_config_loader import UserConfigLoader

async def simulate_news_notification():
    """뉴스 알림 시뮬레이션"""
    print("📰 뉴스 알림 시뮬레이션 시작")
    
    try:
        config_loader = UserConfigLoader()
        user_id = "1"
        
        # 시뮬레이션할 뉴스 데이터들
        test_news = [
            {"stock_code": "005930", "title": "삼성전자 실적 발표", "impact_score": 0.8},
            {"stock_code": "000660", "title": "SK하이닉스 신제품 출시", "impact_score": 0.7},
            {"stock_code": "035420", "title": "NAVER AI 기술 발표", "impact_score": 0.6},
            {"stock_code": "051910", "title": "LG화학 배터리 사업 확장", "impact_score": 0.9},
            {"stock_code": "006400", "title": "삼성SDI 전기차 배터리 공급", "impact_score": 0.8},
        ]
        
        for news in test_news:
            stock_code = news["stock_code"]
            title = news["title"]
            impact_score = news["impact_score"]
            
            print(f"\n📰 뉴스: {title} ({stock_code})")
            
            # 1단계: 사용자가 이 종목에 관심이 있는지 확인
            try:
                is_interested = await config_loader.is_user_interested_in_stock(user_id, stock_code)
                if not is_interested:
                    print(f"  ❌ 사용자가 {stock_code}에 관심 없음 - 알림 전송 안함")
                    continue
                print(f"  ✅ 사용자가 {stock_code}에 관심 있음 - 다음 단계 진행")
            except Exception as e:
                print(f"  ⚠️ 종목 관심도 확인 실패: {e} - 기본값으로 진행")
                is_interested = True  # 기본값으로 진행
            
            # 2단계: 사용자 알림 설정 확인
            try:
                notification_settings = await config_loader.get_user_notification_settings(user_id)
                news_alerts_enabled = notification_settings.get("news_alerts", True)
                overall_enabled = notification_settings.get("enabled", True)
                
                if not overall_enabled:
                    print(f"  ❌ 전체 알림이 비활성화됨 - 알림 전송 안함")
                    continue
                
                if not news_alerts_enabled:
                    print(f"  ❌ 뉴스 알림이 비활성화됨 - 알림 전송 안함")
                    continue
                
                print(f"  ✅ 뉴스 알림 활성화됨 - 알림 전송 진행")
                
            except Exception as e:
                print(f"  ⚠️ 알림 설정 확인 실패: {e} - 기본값으로 진행")
                news_alerts_enabled = True
                overall_enabled = True
            
            # 3단계: 텔레그램 설정 확인
            try:
                telegram_config = await config_loader.get_user_telegram_config(user_id)
                if telegram_config and telegram_config.get("enabled", True):
                    chat_id = telegram_config.get("chat_id")
                    if chat_id:
                        print(f"  ✅ 텔레그램 설정 완료 - 채팅 ID: {chat_id}")
                        print(f"  📤 알림 전송: {title}")
                    else:
                        print(f"  ❌ 텔레그램 채팅 ID 없음 - 알림 전송 안함")
                else:
                    print(f"  ❌ 텔레그램 비활성화됨 - 알림 전송 안함")
                    
            except Exception as e:
                print(f"  ⚠️ 텔레그램 설정 확인 실패: {e} - 알림 전송 안함")
        
        print("\n✅ 뉴스 알림 시뮬레이션 완료!")
        
    except Exception as e:
        print(f"❌ 뉴스 알림 시뮬레이션 실패: {e}")

async def simulate_chart_notification():
    """차트 알림 시뮬레이션"""
    print("\n📊 차트 알림 시뮬레이션 시작")
    
    try:
        config_loader = UserConfigLoader()
        user_id = "1"
        
        # 시뮬레이션할 차트 데이터들
        test_charts = [
            {"stock_code": "005930", "condition": "골든크로스", "impact_score": 0.8},
            {"stock_code": "000660", "condition": "볼린저밴드 터치", "impact_score": 0.7},
            {"stock_code": "035420", "condition": "RSI 과매수", "impact_score": 0.6},
            {"stock_code": "051910", "condition": "MACD 신호", "impact_score": 0.9},
            {"stock_code": "006400", "condition": "지지선 돌파", "impact_score": 0.8},
        ]
        
        for chart in test_charts:
            stock_code = chart["stock_code"]
            condition = chart["condition"]
            impact_score = chart["impact_score"]
            
            print(f"\n📊 차트: {condition} ({stock_code})")
            
            # 1단계: 사용자가 이 종목에 관심이 있는지 확인
            try:
                is_interested = await config_loader.is_user_interested_in_stock(user_id, stock_code)
                if not is_interested:
                    print(f"  ❌ 사용자가 {stock_code}에 관심 없음 - 알림 전송 안함")
                    continue
                print(f"  ✅ 사용자가 {stock_code}에 관심 있음 - 다음 단계 진행")
            except Exception as e:
                print(f"  ⚠️ 종목 관심도 확인 실패: {e} - 기본값으로 진행")
                is_interested = True  # 기본값으로 진행
            
            # 2단계: 사용자 알림 설정 확인
            try:
                notification_settings = await config_loader.get_user_notification_settings(user_id)
                chart_alerts_enabled = notification_settings.get("chart_alerts", True)
                overall_enabled = notification_settings.get("enabled", True)
                
                if not overall_enabled:
                    print(f"  ❌ 전체 알림이 비활성화됨 - 알림 전송 안함")
                    continue
                
                if not chart_alerts_enabled:
                    print(f"  ❌ 차트 알림이 비활성화됨 - 알림 전송 안함")
                    continue
                
                print(f"  ✅ 차트 알림 활성화됨 - 알림 전송 진행")
                
            except Exception as e:
                print(f"  ⚠️ 알림 설정 확인 실패: {e} - 기본값으로 진행")
                chart_alerts_enabled = True
                overall_enabled = True
            
            # 3단계: 텔레그램 설정 확인
            try:
                telegram_config = await config_loader.get_user_telegram_config(user_id)
                if telegram_config and telegram_config.get("enabled", True):
                    chat_id = telegram_config.get("chat_id")
                    if chat_id:
                        print(f"  ✅ 텔레그램 설정 완료 - 채팅 ID: {chat_id}")
                        print(f"  📤 알림 전송: {condition} - {stock_code}")
                    else:
                        print(f"  ❌ 텔레그램 채팅 ID 없음 - 알림 전송 안함")
                else:
                    print(f"  ❌ 텔레그램 비활성화됨 - 알림 전송 안함")
                    
            except Exception as e:
                print(f"  ⚠️ 텔레그램 설정 확인 실패: {e} - 알림 전송 안함")
        
        print("\n✅ 차트 알림 시뮬레이션 완료!")
        
    except Exception as e:
        print(f"❌ 차트 알림 시뮬레이션 실패: {e}")

async def main():
    """메인 테스트 함수"""
    print("🧪 사용자별 알림 필터링 테스트 시작")
    print("=" * 50)
    
    await simulate_news_notification()
    await simulate_chart_notification()
    
    print("\n" + "=" * 50)
    print("✅ 모든 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main()) 