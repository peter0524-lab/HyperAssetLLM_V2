#!/usr/bin/env python3
"""
완전한 백엔드 데이터 흐름 테스트 스크립트
- API Gateway와 각 서비스 간 통신 테스트
- 사용자별 설정 데이터 흐름 테스트
- LLM 모델 선택 및 적용 테스트
- 실제 서비스 실행 테스트
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional
import time
from datetime import datetime

# 테스트할 서비스 설정
SERVICES = {
    "api_gateway": {"port": 8005, "base_url": "http://localhost:8005"},
    "user_service": {"port": 8006, "base_url": "http://localhost:8006"},
    "news_service": {"port": 8001, "base_url": "http://localhost:8001"},
    "disclosure_service": {"port": 8002, "base_url": "http://localhost:8002"},
    "chart_service": {"port": 8003, "base_url": "http://localhost:8003"},
    "report_service": {"port": 8004, "base_url": "http://localhost:8004"},
    "flow_analysis_service": {"port": 8010, "base_url": "http://localhost:8010"}
}

# 테스트 사용자 데이터
TEST_USERS = [
    {
        "user_id": "test_user_1",
        "user_name": "테스트유저1",
        "phone_number": "01012345678",
        "news_similarity_threshold": 0.8,
        "news_impact_threshold": 0.7,
        "model_type": "gemini",
        "stocks": [
            {"stock_code": "005930", "stock_name": "삼성전자"},
            {"stock_code": "000660", "stock_name": "SK하이닉스"}
        ]
    },
    {
        "user_id": "test_user_2",
        "user_name": "테스트유저2", 
        "phone_number": "01087654322",
        "news_similarity_threshold": 0.9,
        "news_impact_threshold": 0.6,
        "model_type": "gpt",
        "stocks": [
            {"stock_code": "035720", "stock_name": "카카오"},
            {"stock_code": "373220", "stock_name": "LG에너지솔루션"}
        ]
    }
]

class DataFlowTester:
    def __init__(self):
        self.session = None
        self.results = {
            "health_checks": {},
            "user_config_tests": {},
            "service_execution_tests": {},
            "data_flow_tests": {}
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)  # 더 긴 타임아웃
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    # ===== 1. 기본 헬스체크 =====
    async def test_service_health(self, service_name: str, config: Dict) -> Dict:
        """개별 서비스 헬스체크"""
        try:
            url = f"{config['base_url']}/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "✅ HEALTHY",
                        "response_time": f"{response.headers.get('X-Process-Time', 'N/A')}ms",
                        "data": data
                    }
                else:
                    return {
                        "status": f"❌ UNHEALTHY ({response.status})",
                        "response_time": "N/A",
                        "error": await response.text()
                    }
        except Exception as e:
            return {"status": f"❌ ERROR: {str(e)}", "response_time": "N/A"}

    # ===== 2. 사용자 설정 테스트 =====
    async def test_user_config_api(self, user_data: Dict) -> Dict:
        """사용자 설정 API 테스트"""
        user_id = user_data["user_id"]
        gateway_url = SERVICES["api_gateway"]["base_url"]
        
        results = {}
        
        try:
            # 0. 사용자 프로필 생성 (먼저 시도)
            profile_data = {
                "username": user_data["user_name"],
                "phone_number": user_data["phone_number"],
                "news_similarity_threshold": user_data["news_similarity_threshold"],
                "news_impact_threshold": user_data["news_impact_threshold"]
            }
            
            # User Service에 직접 프로필 생성 요청
            user_service_url = SERVICES["user_service"]["base_url"]
            actual_user_id = None
            
            async with self.session.post(
                f"{user_service_url}/users/profile",
                json=profile_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    profile_result = await response.json()
                    # 생성된 실제 user_id 사용
                    actual_user_id = profile_result.get("data", {}).get("user_id", user_id)
                    print(f"      ✅ 사용자 프로필 생성 완료: {actual_user_id}")
                    # 실제 생성된 user_id로 업데이트
                    user_data["user_id"] = actual_user_id
                else:
                    print(f"      ⚠️ 사용자 프로필 생성 실패 (이미 존재할 수 있음): {user_id}")
                    # 기존 사용자 조회 시도
                    try:
                        async with self.session.get(
                            f"{user_service_url}/users/{user_id}/profile",
                            headers={"Content-Type": "application/json"}
                        ) as get_response:
                            if get_response.status == 200:
                                profile_data = await get_response.json()
                                actual_user_id = profile_data.get("data", {}).get("user_id", user_id)
                                print(f"      ✅ 기존 사용자 프로필 확인: {actual_user_id}")
                                user_data["user_id"] = actual_user_id
                            else:
                                print(f"      ❌ 사용자 프로필 없음: {user_id}")
                                return {"success": False, "error": "사용자 프로필 생성/조회 실패"}
                    except Exception as e:
                        print(f"      ❌ 사용자 프로필 조회 실패: {e}")
                        return {"success": False, "error": f"사용자 프로필 조회 실패: {e}"}
            
            if not actual_user_id:
                return {"success": False, "error": "유효한 user_id를 얻을 수 없음"}
            
            # 1. 사용자 기본 정보 설정 (API Gateway)
            config_data = {
                "username": user_data["user_name"],
                "phone_number": user_data["phone_number"],
                "news_similarity_threshold": user_data["news_similarity_threshold"],
                "news_impact_threshold": user_data["news_impact_threshold"]
            }
            
            async with self.session.post(
                f"{gateway_url}/api/user/config/{actual_user_id}",
                json=config_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                results["user_config"] = {
                    "status": "✅ SUCCESS" if response.status == 200 else f"❌ FAILED ({response.status})",
                    "data": await response.json() if response.status == 200 else await response.text()
                }
            
            # 2. 종목 설정
            stocks_data = {"stocks": user_data["stocks"]}
            async with self.session.post(
                f"{gateway_url}/api/user/stocks/{actual_user_id}",
                json=stocks_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                results["user_stocks"] = {
                    "status": "✅ SUCCESS" if response.status == 200 else f"❌ FAILED ({response.status})",
                    "data": await response.json() if response.status == 200 else await response.text()
                }
            
            # 3. LLM 모델 설정
            model_data = {"model_type": user_data["model_type"]}
            async with self.session.post(
                f"{gateway_url}/api/user/model/{actual_user_id}",
                json=model_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                results["user_model"] = {
                    "status": "✅ SUCCESS" if response.status == 200 else f"❌ FAILED ({response.status})",
                    "data": await response.json() if response.status == 200 else await response.text()
                }
                
        except Exception as e:
            results["error"] = f"❌ ERROR: {str(e)}"
        
        return results

    # ===== 3. 서비스 실행 테스트 =====
    async def test_service_execution(self, service_name: str, user_id: str) -> Dict:
        """각 서비스의 /execute 엔드포인트 테스트"""
        gateway_url = SERVICES["api_gateway"]["base_url"]
        
        # 서비스별 API 경로 매핑
        service_paths = {
            "news": "/api/news/execute",
            "disclosure": "/api/disclosure/execute", 
            "chart": "/api/chart/execute",
            "report": "/api/report/execute",
            "flow": "/api/flow/execute"
        }
        
        if service_name not in service_paths:
            return {"status": "❌ INVALID SERVICE", "error": f"Unknown service: {service_name}"}
        
        try:
            url = f"{gateway_url}{service_paths[service_name]}"
            headers = {
                "Content-Type": "application/json",
                "X-User-ID": str(user_id)  # 핵심: 사용자 ID 헤더 전달
            }
            
            print(f"      🔄 {service_name} 서비스 실행 중... (사용자 {user_id})")
            
            async with self.session.post(url, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        data = json.loads(response_text)
                        return {
                            "status": "✅ SUCCESS",
                            "response_time": f"{response.headers.get('X-Process-Time', 'N/A')}ms",
                            "data": data
                        }
                    except json.JSONDecodeError:
                        return {
                            "status": "✅ SUCCESS (TEXT)",
                            "response_time": f"{response.headers.get('X-Process-Time', 'N/A')}ms",
                            "data": response_text[:500]
                        }
                else:
                    return {
                        "status": f"❌ FAILED ({response.status})",
                        "error": response_text[:500],
                        "headers": dict(response.headers)
                    }
                    
        except asyncio.TimeoutError:
            return {"status": "⏰ TIMEOUT", "error": "Request timed out after 30 seconds"}
        except Exception as e:
            return {"status": f"❌ ERROR", "error": str(e)}

    # ===== 4. 데이터 흐름 통합 테스트 =====
    async def test_complete_data_flow(self, user_data: Dict) -> Dict:
        """완전한 데이터 흐름 테스트 (설정 → 실행 → 결과 확인)"""
        user_id = user_data["user_id"]
        print(f"    🔄 사용자 {user_id} ({user_data['user_name']}) 완전한 데이터 흐름 테스트...")
        
        results = {}
        
        # 1단계: 사용자 설정 적용
        print(f"      📝 1단계: 사용자 설정 적용...")
        config_results = await self.test_user_config_api(user_data)
        results["config_setup"] = config_results
        
        # 실제 생성된 user_id 추출
        actual_user_id = user_data.get("user_id")  # 이미 actual_user_id로 업데이트되어 있음
        
        # config_results에서 성공적으로 생성된 경우 actual_user_id가 업데이트되었는지 확인
        if not actual_user_id or config_results.get("success") is False:
            print(f"      ❌ 사용자 설정 실패로 인해 테스트 중단")
            results["summary"] = {
                "user_id": user_id,
                "user_name": user_data["user_name"], 
                "successful_configs": "0/3",
                "successful_services": "0/5",
                "model_type": user_data["model_type"],
                "total_success": False
            }
            return results
        
        # 잠시 대기 (설정 적용 시간)
        await asyncio.sleep(2)
        
        # 2단계: 각 서비스 실행 및 설정 반영 확인
        print(f"      🚀 2단계: 각 서비스 실행...")
        service_results = {}
        
        for service in ["news", "disclosure", "chart", "report", "flow"]:
            service_results[service] = await self.test_service_execution(service, actual_user_id)
            await asyncio.sleep(1)  # 서비스 간 간격
        
        results["service_executions"] = service_results
        
        # 3단계: 결과 분석
        successful_configs = sum(1 for r in config_results.values() 
                               if isinstance(r, dict) and "SUCCESS" in r.get("status", ""))
        successful_services = sum(1 for r in service_results.values() 
                                if "SUCCESS" in r.get("status", ""))
        
        results["summary"] = {
            "user_id": user_id,
            "user_name": user_data["user_name"],
            "successful_configs": f"{successful_configs}/3",
            "successful_services": f"{successful_services}/5",
            "model_type": user_data["model_type"],
            "total_success": successful_configs == 3 and successful_services >= 3
        }
        
        return results

    # ===== 5. 메인 테스트 실행기 =====
    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 완전한 백엔드 데이터 흐름 테스트 시작")
        print("=" * 80)
        
        # 1. 기본 헬스체크
        print("\n📋 1단계: 서비스 헬스체크")
        print("-" * 50)
        
        for service_name, config in SERVICES.items():
            result = await self.test_service_health(service_name, config)
            self.results["health_checks"][service_name] = result
            print(f"{service_name:25} | {result['status']}")
        
        # 2. 각 사용자별 완전한 데이터 흐름 테스트
        print(f"\n🔄 2단계: 사용자별 완전한 데이터 흐름 테스트")
        print("-" * 50)
        
        for user_data in TEST_USERS:
            original_user_id = user_data["user_id"]
            flow_result = await self.test_complete_data_flow(user_data)
            
            # 실제 생성된 user_id 사용 (user_data가 업데이트되었을 수 있음)
            actual_user_id = user_data.get("user_id", original_user_id)
            self.results["data_flow_tests"][f"user_{original_user_id}"] = flow_result
            
            summary = flow_result["summary"]
            status = "✅ 성공" if summary["total_success"] else "❌ 실패"
            print(f"사용자 {original_user_id} ({summary['user_name']}) | {status} | "
                  f"설정: {summary['successful_configs']} | 서비스: {summary['successful_services']}")
        
        # 3. 전체 결과 요약
        print(f"\n📊 3단계: 전체 테스트 결과 요약")
        print("=" * 80)
        
        # 헬스체크 요약
        healthy_services = sum(1 for r in self.results["health_checks"].values() 
                             if "HEALTHY" in r["status"])
        total_services = len(self.results["health_checks"])
        
        # 데이터 흐름 요약
        successful_flows = sum(1 for r in self.results["data_flow_tests"].values() 
                             if r["summary"]["total_success"])
        total_flows = len(self.results["data_flow_tests"])
        
        print(f"✅ 서비스 상태: {healthy_services}/{total_services} 정상")
        print(f"✅ 데이터 흐름: {successful_flows}/{total_flows} 성공")
        
        if healthy_services == total_services and successful_flows == total_flows:
            print(f"\n🎉 모든 테스트 통과! 백엔드 데이터 흐름이 완벽하게 작동합니다!")
        elif healthy_services == total_services:
            print(f"\n⚠️  서비스는 정상이지만 일부 데이터 흐름에 문제가 있습니다.")
        else:
            print(f"\n❌ 일부 서비스에 문제가 있습니다. 로그를 확인해주세요.")
        
        # 세부 실패 원인 분석
        print(f"\n🔍 세부 분석:")
        for user_id, flow_result in self.results["data_flow_tests"].items():
            if not flow_result["summary"]["total_success"]:
                print(f"  - {user_id}: 설정 문제 또는 서비스 실행 실패")
                
                # 설정 문제 확인
                config_results = flow_result["config_setup"]
                for config_type, result in config_results.items():
                    if isinstance(result, dict) and "FAILED" in result.get("status", ""):
                        print(f"    ❌ {config_type}: {result.get('data', 'Unknown error')}")
                
                # 서비스 실행 문제 확인  
                service_results = flow_result["service_executions"]
                for service_name, result in service_results.items():
                    if "FAILED" in result.get("status", "") or "ERROR" in result.get("status", ""):
                        print(f"    ❌ {service_name}: {result.get('error', 'Unknown error')[:100]}")
        
        return self.results

async def main():
    """메인 실행 함수"""
    print("🔧 완전한 백엔드 데이터 흐름 테스트 도구")
    print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    async with DataFlowTester() as tester:
        results = await tester.run_all_tests()
        
        # 상세 결과를 JSON 파일로 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backend_data_flow_test_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 상세 결과가 '{filename}'에 저장되었습니다.")
        print(f"⏰ 테스트 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main()) 