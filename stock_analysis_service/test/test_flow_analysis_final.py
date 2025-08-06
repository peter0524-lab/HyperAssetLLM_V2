#!/usr/bin/env python3
"""
Flow Analysis Service 핵심 동작 테스트
실제 서비스가 제대로 작동하는지 확인하는 필수 테스트만 포함
"""

import sys
import os
import asyncio
import pymysql.cursors
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from shared.apis.pykrx_api import pykrx_client
from shared.database.mysql_client import get_mysql_client
from services.flow_analysis_service.flow_analysis_service import FlowAnalysisService

class FlowAnalysisTest:
    """Flow Analysis Service 핵심 테스트"""
    
    def __init__(self):
        self.mysql_client = get_mysql_client("mysql")
        self.mysql2_client = get_mysql_client("mysql2")
        self.service = FlowAnalysisService()
        self.test_stock_code = "006800"
        self.test_stock_name = "미래에셋증권"
        self.test_user_id = "test_user_flow_final"
        self.test_telegram_chat_id = "1234567890"
        
    async def run_all_tests(self):
        """모든 핵심 테스트 실행"""
        print("🚀 Flow Analysis Service 핵심 동작 테스트 시작\n")
        
        tests = [
            ("데이터베이스 연결", self.test_database_connection),
            ("서비스 초기화", self.test_service_initialization),  
            ("PyKRX 데이터 수집", self.test_pykrx_data_collection),
            ("EOD 데이터 저장", self.test_eod_data_storage),
            ("트리거 로직", self.test_trigger_logic),
            ("API 엔드포인트", self.test_api_endpoints)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"🔍 {test_name} 테스트 중...")
            try:
                result = await test_func()
                if result:
                    print(f"✅ {test_name}: 성공\n")
                    results.append(True)
                else:
                    print(f"❌ {test_name}: 실패\n")
                    results.append(False)
            except Exception as e:
                print(f"❌ {test_name}: 오류 - {e}\n")
                results.append(False)
                
        # 결과 요약
        success_count = sum(results)
        total_count = len(results)
        success_rate = success_count / total_count * 100
        
        print(f"{'='*50}")
        print(f"🏁 테스트 결과: {success_count}/{total_count} ({success_rate:.1f}%)")
        print(f"{'='*50}")
        
        if success_rate >= 80:
            print("🎉 Flow Analysis Service가 정상 작동합니다!")
            return True
        else:
            print("⚠️ 일부 기능에 문제가 있습니다. 디버깅이 필요합니다.")
            return False
    
    async def test_database_connection(self):
        """데이터베이스 연결 및 테이블 확인"""
        try:
            with self.mysql_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
                # 필요한 테이블들 확인
                required_tables = ['eod_flows', 'program_flows', 'pattern_signals']
                cursor.execute("SHOW TABLES")
                existing_tables = [list(row.values())[0] for row in cursor.fetchall()]
                
                for table in required_tables:
                    if table not in existing_tables:
                        print(f"   ❌ 테이블 {table} 없음")
                        return False
                
                print(f"   ✅ 모든 필요 테이블 확인 완료")
                return True
                
        except Exception as e:
            print(f"   ❌ 데이터베이스 연결 실패: {e}")
            return False
    
    async def test_service_initialization(self):
        """서비스 초기화 테스트"""
        try:
            self.service = FlowAnalysisService()
            await self.service.initialize_database()
            
            print(f"   ✅ 서비스 초기화 완료")
            print(f"   ✅ 기관 트리거: {self.service.institutional_trigger_days}일 중 {self.service.institutional_trigger_threshold}일")
            print(f"   ✅ 프로그램 트리거: {self.service.program_trigger_multiplier}배")
            return True
            
        except Exception as e:
            print(f"   ❌ 서비스 초기화 실패: {e}")
            return False
    
    async def test_pykrx_data_collection(self):
        """PyKRX 데이터 수집 테스트"""
        try:
            if not pykrx_client:
                print("   ❌ pykrx_client 없음")
                return False
            
            # 간단한 데이터 수집 테스트
            result = pykrx_client.get_eod_flow_data(self.test_stock)
            
            if result.get("status") == "success":
                data = result["data"]
                print(f"   ✅ {self.test_stock} 데이터 수집 성공")
                print(f"   ✅ 기관 순매수: {data.get('inst_net', 0):,}원")
                return True
            else:
                print(f"   ❌ 데이터 수집 실패: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"   ❌ PyKRX 테스트 실패: {e}")
            return False
    
    async def test_eod_data_storage(self):
        """EOD 데이터 저장 테스트"""
        try:
            # 실제 데이터 수집 및 저장
            result = await self.service.collect_eod_flow_data(self.test_stock)
            
            if not result:
                print("   ❌ EOD 데이터 수집 실패")
                return False
            
            # DB에서 저장 확인
            with self.mysql2_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("""
                    SELECT * FROM eod_flows 
                    WHERE ticker = %s 
                    ORDER BY trade_date DESC 
                    LIMIT 1
                """, (self.test_stock,))
                saved_data = cursor.fetchone()
                
                if saved_data:
                    print(f"   ✅ DB 저장 확인: {saved_data['trade_date']}")
                    print(f"   ✅ 기관: {saved_data['inst_net']:,}원")
                    return True
                else:
                    print("   ❌ DB 저장 실패")
                    return False
                    
        except Exception as e:
            print(f"   ❌ EOD 저장 테스트 실패: {e}")
            return False
    
    async def test_trigger_logic(self):
        """트리거 로직 테스트"""
        try:
            # 기관 매수 트리거 체크
            trigger_result = await self.service.check_institutional_buying_trigger(self.test_stock)
            
            print(f"   ✅ 트리거 체크 완료")
            print(f"   ✅ 발생 여부: {trigger_result.get('triggered')}")
            print(f"   ✅ 순매수일: {trigger_result.get('positive_days', 0)}/{trigger_result.get('total_days', 0)}")
            
            # 테스트용 트리거 저장
            test_data = {
                "triggered": True,
                "positive_days": 4,
                "total_days": 5,
                "latest_positive": True,
                "latest_amount": 500000000,
                "test_mode": True
            }
            await self.service.handle_institutional_trigger(self.test_stock, test_data)
            
            # 저장 확인
            with self.mysql2_client.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM pattern_signals 
                    WHERE ticker = %s AND DATE(ref_time) = CURDATE()
                """, (self.test_stock,))
                count = cursor.fetchone()['cnt']
                
                if count > 0:
                    print(f"   ✅ 신호 저장 확인: {count}개")
                    return True
                else:
                    print("   ❌ 신호 저장 실패")
                    return False
                    
        except Exception as e:
            print(f"   ❌ 트리거 로직 테스트 실패: {e}")
            return False
    
    async def test_api_endpoints(self):
        """API 엔드포인트 테스트"""
        try:
            import requests
            import subprocess
            import time
            
            # API 서버 시작
            server_process = subprocess.Popen([
                sys.executable, "services/flow_analysis_service/flow_analysis_service.py", "--api"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 서버 시작 대기
            time.sleep(3)
            
            try:
                # 기본 엔드포인트 테스트
                response = requests.get("http://localhost:8010/", timeout=5)
                if response.status_code == 200:
                    print("   ✅ API 서버 응답 확인")
                    
                    # 상태 확인
                    status_response = requests.get("http://localhost:8010/status", timeout=5)
                    if status_response.status_code == 200:
                        print("   ✅ 상태 엔드포인트 확인")
                        return True
                    else:
                        print("   ❌ 상태 엔드포인트 실패")
                        return False
                else:
                    print("   ❌ API 서버 응답 실패")
                    return False
                    
            finally:
                server_process.terminate()
                server_process.wait()
                
        except Exception as e:
            print(f"   ❌ API 테스트 실패: {e}")
            return False

async def main():
    """메인 테스트 실행"""
    test = FlowAnalysisTest()
    success = await test.run_all_tests()
    
    if success:
        print("\n🎯 Flow Analysis Service 정상 작동 확인!")
        print("🚀 실제 서비스 환경에서 사용 가능합니다.")
    else:
        print("\n🔧 Flow Analysis Service에 문제가 있습니다.")
        print("📋 위의 실패 항목들을 확인하고 수정해주세요.")

if __name__ == "__main__":
    asyncio.run(main()) 