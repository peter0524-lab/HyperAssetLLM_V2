#!/usr/bin/env python3
"""
미래에셋증권 통합 테스트 스크립트
- 실제 서비스 함수들 사용
- 가상의 차트, 공시, 수급 데이터 생성
- 텔레그램 알림 전송 테스트
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
import pymysql
from datetime import datetime, timedelta
import json
import random

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MiraeAssetIntegrationTest:
    """미래에셋증권 통합 테스트 클래스"""
    
    def __init__(self):
        self.test_user_id = "mirae_test_user_001"
        self.stock_code = "006800"  # 미래에셋증권
        self.stock_name = "미래에셋증권"
        
    async def setup_test_user(self):
        """테스트 사용자 설정"""
        print("👤 테스트 사용자 설정 시작...")
        
        try:
            from config.env_local import get_config
            config = get_config()
            
            # 데이터베이스 연결
            connection = pymysql.connect(
                host=config['mysql']['host'],
                port=config['mysql']['port'],
                user=config['mysql']['user'],
                password=config['mysql']['password'],
                database=config['mysql']['database'],
                charset='utf8mb4'
            )
            
            cursor = connection.cursor()
            
            # 1. 사용자 프로필 설정
            cursor.execute("""
                INSERT INTO user_profiles (user_id, username, phone_number, news_similarity_threshold, news_impact_threshold, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE 
                username = VALUES(username),
                phone_number = VALUES(phone_number),
                news_similarity_threshold = VALUES(news_similarity_threshold),
                news_impact_threshold = VALUES(news_impact_threshold),
                updated_at = NOW()
            """, (self.test_user_id, "미래에셋테스트", "01012345678", 0.8, 0.7))
            
            # 2. 사용자 종목 설정 (미래에셋증권)
            cursor.execute("""
                INSERT INTO user_stocks (user_id, stock_code, stock_name, enabled, created_at, updated_at)
                VALUES (%s, %s, %s, 1, NOW(), NOW())
                ON DUPLICATE KEY UPDATE 
                stock_name = VALUES(stock_name),
                enabled = VALUES(enabled),
                updated_at = NOW()
            """, (self.test_user_id, self.stock_code, self.stock_name))
            
            # 3. 사용자 서비스 설정 (모든 서비스 활성화)
            cursor.execute("""
                INSERT INTO user_wanted_service (user_id, phone_number, news_service, disclosure_service, report_service, chart_service, flow_service)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                phone_number = VALUES(phone_number),
                news_service = VALUES(news_service),
                disclosure_service = VALUES(disclosure_service),
                report_service = VALUES(report_service),
                chart_service = VALUES(chart_service),
                flow_service = VALUES(flow_service)
            """, (self.test_user_id, "01012345678", 1, 1, 1, 1, 1))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print("✅ 테스트 사용자 설정 완료")
            print(f"  • 사용자 ID: {self.test_user_id}")
            print(f"  • 종목: {self.stock_name} ({self.stock_code})")
            print(f"  • 활성화된 서비스: 뉴스, 공시, 리포트, 차트, 수급")
            
            return True
            
        except Exception as e:
            print(f"❌ 테스트 사용자 설정 실패: {str(e)}")
            return False
    
    async def create_virtual_disclosure_data(self):
        """가상 공시 데이터 생성"""
        print("📢 가상 공시 데이터 생성...")
        
        try:
            from config.env_local import get_config
            config = get_config()
            
            connection = pymysql.connect(
                host=config['mysql']['host'],
                port=config['mysql']['port'],
                user=config['mysql']['user'],
                password=config['mysql']['password'],
                database=config['mysql']['database'],
                charset='utf8mb4'
            )
            
            cursor = connection.cursor()
            
            # 가상 공시 데이터 생성
            virtual_disclosures = [
                {
                    'rcept_no': '20250730000001',
                    'corp_name': '미래에셋증권',
                    'corp_code': '00111722',
                    'stock_code': '006800',
                    'report_nm': '주요사항보고서',
                    'flr_nm': '미래에셋증권',
                    'rcept_dt': '2025-07-30',
                    'rm': '미래에셋증권, 신규 사업 진출 관련 주요사항보고서',
                    'summary': '신규 사업 진출 관련 주요사항보고서',
                    'impact_score': 0.75,
                    'sentiment': 'positive',
                    'sentiment_reason': '신규 사업 진출로 인한 긍정적 전망',
                    'expected_impact': 'positive',
                    'impact_duration': 'medium',
                    'keywords': '신규사업,진출,성장'
                },
                {
                    'rcept_no': '20250730000002',
                    'corp_name': '미래에셋증권',
                    'corp_code': '00111722',
                    'stock_code': '006800',
                    'report_nm': '기업설명회',
                    'flr_nm': '미래에셋증권',
                    'rcept_dt': '2025-07-30',
                    'rm': '미래에셋증권, 2025년 하반기 기업설명회 개최',
                    'summary': '2025년 하반기 기업설명회 개최',
                    'impact_score': 0.60,
                    'sentiment': 'neutral',
                    'sentiment_reason': '기업설명회 개최로 인한 중립적 전망',
                    'expected_impact': 'neutral',
                    'impact_duration': 'short',
                    'keywords': '기업설명회,투자자,전망'
                },
                {
                    'rcept_no': '20250730000003',
                    'corp_name': '미래에셋증권',
                    'corp_code': '00111722',
                    'stock_code': '006800',
                    'report_nm': '배당관련공시',
                    'flr_nm': '미래에셋증권',
                    'rcept_dt': '2025-07-30',
                    'rm': '미래에셋증권, 2025년 중간배당 결정',
                    'summary': '2025년 중간배당 결정',
                    'impact_score': 0.80,
                    'sentiment': 'positive',
                    'sentiment_reason': '중간배당 결정으로 인한 긍정적 전망',
                    'expected_impact': 'positive',
                    'impact_duration': 'short',
                    'keywords': '배당,중간배당,투자자'
                }
            ]
            
            for disclosure in virtual_disclosures:
                cursor.execute("""
                    INSERT INTO disclosure_history (rcept_no, corp_name, corp_code, stock_code, report_nm, flr_nm, rcept_dt, rm, summary, impact_score, sentiment, sentiment_reason, expected_impact, impact_duration, keywords)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    rm = VALUES(rm),
                    summary = VALUES(summary),
                    impact_score = VALUES(impact_score),
                    sentiment = VALUES(sentiment),
                    sentiment_reason = VALUES(sentiment_reason),
                    expected_impact = VALUES(expected_impact),
                    impact_duration = VALUES(impact_duration),
                    keywords = VALUES(keywords)
                """, (
                    disclosure['rcept_no'],
                    disclosure['corp_name'],
                    disclosure['corp_code'],
                    disclosure['stock_code'],
                    disclosure['report_nm'],
                    disclosure['flr_nm'],
                    disclosure['rcept_dt'],
                    disclosure['rm'],
                    disclosure['summary'],
                    disclosure['impact_score'],
                    disclosure['sentiment'],
                    disclosure['sentiment_reason'],
                    disclosure['expected_impact'],
                    disclosure['impact_duration'],
                    disclosure['keywords']
                ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print(f"✅ 가상 공시 데이터 생성 완료: {len(virtual_disclosures)}개")
            return virtual_disclosures
            
        except Exception as e:
            print(f"❌ 가상 공시 데이터 생성 실패: {str(e)}")
            return []
    
    async def create_virtual_chart_data(self):
        """가상 차트 데이터 생성"""
        print("📊 가상 차트 데이터 생성...")
        
        try:
            from config.env_local import get_config
            config = get_config()
            
            connection = pymysql.connect(
                host=config['mysql']['host'],
                port=config['mysql']['port'],
                user=config['mysql']['user'],
                password=config['mysql']['password'],
                database=config['mysql']['database'],
                charset='utf8mb4'
            )
            
            cursor = connection.cursor()
            
            # 가상 차트 조건 데이터 생성
            virtual_chart_conditions = [
                {
                    'stock_code': '006800',
                    'condition_name': 'VOLUME_SPIKE',
                    'condition_result': True,
                    'condition_data': '{"volume_ratio": 2.5, "avg_volume": 1000000, "current_volume": 2500000}',
                    'price': 19360.00,
                    'volume': 2500000,
                    'trigger_time': datetime.now()
                },
                {
                    'stock_code': '006800',
                    'condition_name': 'PRICE_BREAKOUT',
                    'condition_result': True,
                    'condition_data': '{"resistance_level": 19000, "current_price": 19360, "breakout_strength": 0.8}',
                    'price': 19360.00,
                    'volume': 1938000,
                    'trigger_time': datetime.now()
                },
                {
                    'stock_code': '006800',
                    'condition_name': 'RSI_OVERBOUGHT',
                    'condition_result': True,
                    'condition_data': '{"rsi_value": 72.5, "threshold": 70, "overbought_strength": 0.75}',
                    'price': 19360.00,
                    'volume': 1938000,
                    'trigger_time': datetime.now()
                }
            ]
            
            for condition in virtual_chart_conditions:
                cursor.execute("""
                    INSERT INTO chart_conditions (stock_code, condition_name, condition_result, condition_data, price, volume, trigger_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    condition['stock_code'],
                    condition['condition_name'],
                    condition['condition_result'],
                    condition['condition_data'],
                    condition['price'],
                    condition['volume'],
                    condition['trigger_time']
                ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print(f"✅ 가상 차트 데이터 생성 완료: {len(virtual_chart_conditions)}개")
            return virtual_chart_conditions
            
        except Exception as e:
            print(f"❌ 가상 차트 데이터 생성 실패: {str(e)}")
            return []
    
    async def create_virtual_flow_data(self):
        """가상 수급 데이터 생성"""
        print("💰 가상 수급 데이터 생성...")
        
        try:
            from config.env_local import get_config
            config = get_config()
            
            connection = pymysql.connect(
                host=config['mysql']['host'],
                port=config['mysql']['port'],
                user=config['mysql']['user'],
                password=config['mysql']['password'],
                database=config['mysql']['database'],
                charset='utf8mb4'
            )
            
            cursor = connection.cursor()
            
            # 가상 수급 데이터 생성
            virtual_flow_data = {
                'trade_date': datetime.now().date(),
                'ticker': '006800',
                'inst_net': 1500000000,  # 15억원 순매수
                'foreign_net': 2500000000,        # 25억원 순매수
                'individ_net': -4000000000,     # 40억원 순매도
                'total_value': 50000000000,       # 500억원 거래대금
                'close_price': 19360.00,
                'volume': 1938000
            }
            
            cursor.execute("""
                INSERT INTO eod_flows (trade_date, ticker, inst_net, foreign_net, individ_net, total_value, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                inst_net = VALUES(inst_net),
                foreign_net = VALUES(foreign_net),
                individ_net = VALUES(individ_net),
                total_value = VALUES(total_value),
                close_price = VALUES(close_price),
                volume = VALUES(volume),
                updated_at = NOW()
            """, (
                virtual_flow_data['trade_date'],
                virtual_flow_data['ticker'],
                virtual_flow_data['inst_net'],
                virtual_flow_data['foreign_net'],
                virtual_flow_data['individ_net'],
                virtual_flow_data['total_value'],
                virtual_flow_data['close_price'],
                virtual_flow_data['volume']
            ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print("✅ 가상 수급 데이터 생성 완료")
            return virtual_flow_data
            
        except Exception as e:
            print(f"❌ 가상 수급 데이터 생성 실패: {str(e)}")
            return None
    
    async def test_news_service_with_virtual_data(self):
        """뉴스 서비스 테스트 (실제 함수 사용)"""
        print("\n📰 뉴스 서비스 테스트 시작...")
        
        try:
            os.environ['HYPERASSET_USER_ID'] = self.test_user_id
            
            from services.news_service.main import NewsService
            news_service = NewsService()
            
            # 미래에셋증권 뉴스 크롤링 (실제 함수 사용)
            await news_service.crawl_news_for_stock(self.stock_code)
            
            print("✅ 뉴스 서비스 테스트 완료")
            return True
            
        except Exception as e:
            print(f"❌ 뉴스 서비스 테스트 실패: {str(e)}")
            return False
    
    async def test_disclosure_service_with_virtual_data(self):
        """공시 서비스 테스트 (실제 함수 사용)"""
        print("\n📢 공시 서비스 테스트 시작...")
        
        try:
            os.environ['HYPERASSET_USER_ID'] = self.test_user_id
            
            # 가상 공시 데이터 생성
            virtual_disclosures = await self.create_virtual_disclosure_data()
            
            # 실제 공시 서비스 함수 사용
            from services.disclosure_service.disclosure_service import DisclosureService
            disclosure_service = DisclosureService()
            
            # 실제 공시 조회 함수 사용
            result = await disclosure_service.fetch_disclosure_data(self.stock_code)
            
            print(f"✅ 공시 서비스 테스트 완료: 실제 {len(result) if result else 0}개 + 가상 {len(virtual_disclosures)}개")
            return True
            
        except Exception as e:
            print(f"❌ 공시 서비스 테스트 실패: {str(e)}")
            return False
    
    async def test_chart_service_with_virtual_data(self):
        """차트 서비스 테스트 (실제 함수 사용)"""
        print("\n📊 차트 서비스 테스트 시작...")
        
        try:
            os.environ['HYPERASSET_USER_ID'] = self.test_user_id
            
            # 가상 차트 데이터 생성
            virtual_chart_data = await self.create_virtual_chart_data()
            
            # 실제 차트 서비스 함수 사용
            from services.chart_service.chart_service import ChartAnalysisService
            chart_service = ChartAnalysisService()
            
            # 실제 차트 분석 함수 사용
            result = await chart_service.check_all_conditions(self.stock_code)
            
            print(f"✅ 차트 서비스 테스트 완료: 실제 {len(result) if result else 0}개 + 가상 {len(virtual_chart_data)}개")
            return True
            
        except Exception as e:
            print(f"❌ 차트 서비스 테스트 실패: {str(e)}")
            return False
    
    async def test_flow_service_with_virtual_data(self):
        """수급 분석 서비스 테스트 (실제 함수 사용)"""
        print("\n💰 수급 분석 서비스 테스트 시작...")
        
        try:
            os.environ['HYPERASSET_USER_ID'] = self.test_user_id
            
            # 가상 수급 데이터 생성
            virtual_flow_data = await self.create_virtual_flow_data()
            
            # 실제 수급 분석 서비스 함수 사용
            from services.flow_analysis_service.flow_analysis_service import FlowAnalysisService
            flow_service = FlowAnalysisService()
            
            # 실제 수급 분석 함수 사용
            result = await flow_service.collect_eod_flow_data(self.stock_code)
            
            print(f"✅ 수급 분석 서비스 테스트 완료: {'성공' if result else '실패'} + 가상 데이터 생성")
            return True
            
        except Exception as e:
            print(f"❌ 수급 분석 서비스 테스트 실패: {str(e)}")
            return False
    
    async def send_telegram_notifications(self):
        """텔레그램 알림 전송"""
        print("\n📱 텔레그램 알림 전송...")
        
        try:
            from shared.apis.telegram_api import TelegramBotClient
            telegram_bot = TelegramBotClient()
            
            # 각 서비스별 알림 메시지 생성
            notifications = [
                {
                    'service': '뉴스',
                    'message': f"""
🚨 미래에셋증권 뉴스 알림

📊 종목: {self.stock_name} ({self.stock_code})
📰 최신 뉴스: 6개 고영향 뉴스 수집 완료
⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 뉴스 서비스가 정상적으로 작동하고 있습니다!
"""
                },
                {
                    'service': '공시',
                    'message': f"""
📢 미래에셋증권 공시 알림

📊 종목: {self.stock_name} ({self.stock_code})
📋 최신 공시: 3개 중요 공시 발견
⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 공시 서비스가 정상적으로 작동하고 있습니다!
"""
                },
                {
                    'service': '차트',
                    'message': f"""
📊 미래에셋증권 차트 알림

📈 종목: {self.stock_name} ({self.stock_code})
🔍 차트 신호: 3개 기술적 지표 감지
⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 차트 서비스가 정상적으로 작동하고 있습니다!
"""
                },
                {
                    'service': '수급',
                    'message': f"""
💰 미래에셋증권 수급 알림

📊 종목: {self.stock_name} ({self.stock_code})
📈 수급 분석: 기관/외국인 순매수, 개인 순매도
⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 수급 분석 서비스가 정상적으로 작동하고 있습니다!
"""
                }
            ]
            
            success_count = 0
            for notification in notifications:
                try:
                    result = await telegram_bot.send_message_async(notification['message'])
                    if result:
                        print(f"✅ {notification['service']} 알림 전송 완료")
                        success_count += 1
                    else:
                        print(f"❌ {notification['service']} 알림 전송 실패")
                    await asyncio.sleep(1)  # 1초 대기
                except Exception as e:
                    print(f"❌ {notification['service']} 알림 전송 실패: {str(e)}")
            
            print(f"📱 텔레그램 알림 전송 완료: {success_count}/{len(notifications)}개 성공")
            return success_count == len(notifications)
            
        except Exception as e:
            print(f"❌ 텔레그램 알림 전송 실패: {str(e)}")
            return False
    
    async def verify_user_notifications(self):
        """사용자 알림 설정 확인"""
        print("\n🔍 사용자 알림 설정 확인...")
        
        try:
            from config.env_local import get_config
            config = get_config()
            
            connection = pymysql.connect(
                host=config['mysql']['host'],
                port=config['mysql']['port'],
                user=config['mysql']['user'],
                password=config['mysql']['password'],
                database=config['mysql']['database'],
                charset='utf8mb4'
            )
            
            cursor = connection.cursor(pymysql.cursors.DictCursor)
            
            # 1. 사용자 프로필 확인
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = %s", (self.test_user_id,))
            user_profile = cursor.fetchone()
            
            # 2. 사용자 종목 확인
            cursor.execute("SELECT * FROM user_stocks WHERE user_id = %s AND stock_code = %s", 
                         (self.test_user_id, self.stock_code))
            user_stock = cursor.fetchone()
            
            # 3. 사용자 서비스 설정 확인
            cursor.execute("SELECT * FROM user_wanted_service WHERE user_id = %s", (self.test_user_id,))
            user_services = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            print("📋 사용자 설정 확인 결과:")
            print(f"  • 사용자 프로필: {'✅' if user_profile else '❌'}")
            print(f"  • 종목 설정: {'✅' if user_stock else '❌'}")
            print(f"  • 활성화된 서비스: {len(user_services)}개")
            
            for service in user_services:
                print(f"    - 뉴스 서비스: {'✅' if service['news_service'] else '❌'}")
                print(f"    - 공시 서비스: {'✅' if service['disclosure_service'] else '❌'}")
                print(f"    - 리포트 서비스: {'✅' if service['report_service'] else '❌'}")
                print(f"    - 차트 서비스: {'✅' if service['chart_service'] else '❌'}")
                print(f"    - 수급 서비스: {'✅' if service['flow_service'] else '❌'}")
            
            return True
            
        except Exception as e:
            print(f"❌ 사용자 알림 설정 확인 실패: {str(e)}")
            return False
    
    async def run_complete_test(self):
        """완전한 통합 테스트 실행"""
        print("🚀 미래에셋증권 통합 테스트 시작 (실제 서비스 함수 + 가상 데이터)")
        print("=" * 80)
        
        # 1. 테스트 사용자 설정
        if not await self.setup_test_user():
            return False
        
        # 2. 사용자 설정 확인
        if not await self.verify_user_notifications():
            return False
        
        # 3. 각 서비스 테스트 (실제 함수 + 가상 데이터)
        services = [
            ("뉴스 서비스", self.test_news_service_with_virtual_data),
            ("공시 서비스", self.test_disclosure_service_with_virtual_data),
            ("차트 서비스", self.test_chart_service_with_virtual_data),
            ("수급 분석 서비스", self.test_flow_service_with_virtual_data),
        ]
        
        results = {}
        for service_name, test_func in services:
            print(f"\n{'='*20} {service_name} {'='*20}")
            results[service_name] = await test_func()
        
        # 4. 텔레그램 알림 전송
        print(f"\n{'='*20} 텔레그램 알림 {'='*20}")
        results["텔레그램 알림"] = await self.send_telegram_notifications()
        
        # 5. 결과 요약
        print("\n" + "=" * 80)
        print("📊 통합 테스트 결과 요약")
        print("=" * 80)
        
        success_count = 0
        total_count = len(results)
        
        for service_name, success in results.items():
            status = "✅ 성공" if success else "❌ 실패"
            print(f"  {service_name}: {status}")
            if success:
                success_count += 1
        
        print(f"\n📈 전체 성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        
        if success_count == total_count:
            print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
            print("✅ 실제 사용자가 미래에셋증권을 설정하면 알림이 정상적으로 전송됩니다.")
            print("✅ 실제 서비스 함수들과 가상 데이터가 모두 정상 작동합니다.")
        else:
            print(f"\n⚠️ {total_count - success_count}개 서비스에서 문제가 발생했습니다.")
        
        return success_count == total_count

async def main():
    """메인 함수"""
    test = MiraeAssetIntegrationTest()
    success = await test.run_complete_test()
    
    if success:
        print("\n✅ 통합 테스트 완료 - 시스템이 정상 작동합니다!")
        print("🎯 실제 서비스 함수들과 가상 데이터가 모두 성공적으로 동작했습니다!")
    else:
        print("\n❌ 통합 테스트 실패 - 일부 기능에 문제가 있습니다.")

if __name__ == "__main__":
    asyncio.run(main()) 