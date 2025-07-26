#!/usr/bin/env python3
"""
모든 서비스 헬스체크 도구
- 각 서비스의 /health 엔드포인트 확인
- 서비스 상태 및 응답 시간 측정
- 요약 정보 제공
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ServiceInfo:
    name: str
    port: int
    url: str
    status: str = "unknown"
    response_time: float = 0.0
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None

class HealthChecker:
    def __init__(self):
        self.services = [
            ServiceInfo("News Service", 8001, "http://localhost:8001/health"),
            ServiceInfo("Disclosure Service", 8002, "http://localhost:8002/health"),
            ServiceInfo("Chart Service", 8003, "http://localhost:8003/health"),
            ServiceInfo("Report Service", 8004, "http://localhost:8004/health"),
            ServiceInfo("API Gateway", 8005, "http://localhost:8005/health"),
            ServiceInfo("User Service", 8006, "http://localhost:8006/health"),
            ServiceInfo("Flow Analysis Service", 8010, "http://localhost:8010/health"),
        ]
        
        # 서비스별 특별 타임아웃 설정
        self.service_timeouts = {
            "News Service": 60,  # news_service는 초기화가 매우 오래 걸림 (Chrome Driver, 임베딩 모델 등)
            "Disclosure Service": 15,
            "Chart Service": 15,
            "Report Service": 15,
            "API Gateway": 10,
            "User Service": 10,
            "Flow Analysis Service": 15,
        }
    
    async def check_service_health(self, service: ServiceInfo) -> ServiceInfo:
        """개별 서비스 헬스체크"""
        try:
            start_time = time.time()
            
            # 서비스별 타임아웃 적용
            service_timeout = self.service_timeouts.get(service.name, 10)
            timeout = aiohttp.ClientTimeout(total=service_timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(service.url) as response:
                    end_time = time.time()
                    service.response_time = round((end_time - start_time) * 1000, 2)  # ms
                    
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            service.response_data = response_data
                            service.status = "healthy"
                        except:
                            service.status = "healthy"
                            service.response_data = {"status": "ok"}
                    else:
                        service.status = "unhealthy"
                        service.error_message = f"HTTP {response.status}"
                        
        except asyncio.TimeoutError:
            service_timeout = self.service_timeouts.get(service.name, 10)
            service.status = "timeout"
            service.error_message = f"응답 시간 초과 ({service_timeout}초)"
            service.response_time = service_timeout * 1000.0
        except aiohttp.ClientConnectionError:
            service.status = "offline"
            service.error_message = "연결 실패 - 서비스가 실행되지 않음"
        except Exception as e:
            service.status = "error"
            service.error_message = str(e)
        
        return service
    
    async def check_all_services(self) -> List[ServiceInfo]:
        """모든 서비스 병렬 헬스체크"""
        print("🔍 모든 서비스 헬스체크 시작...")
        print("-" * 80)
        
        # 모든 서비스를 병렬로 체크
        tasks = [self.check_service_health(service) for service in self.services]
        results = await asyncio.gather(*tasks)
        
        return results
    
    def print_results(self, results: List[ServiceInfo]):
        """결과 출력"""
        print("📊 서비스 상태 결과")
        print("=" * 80)
        
        healthy_count = 0
        unhealthy_services = []
        
        # 개별 서비스 상태 출력
        for service in results:
            status_icon = {
                "healthy": "✅",
                "unhealthy": "⚠️",
                "offline": "❌",
                "timeout": "⏰",
                "error": "💥",
                "unknown": "❓"
            }.get(service.status, "❓")
            
            print(f"{status_icon} {service.name:<25} (포트: {service.port})")
            print(f"   상태: {service.status}")
            print(f"   응답시간: {service.response_time}ms")
            
            if service.status == "healthy":
                healthy_count += 1
                if service.response_data:
                    if isinstance(service.response_data, dict):
                        for key, value in service.response_data.items():
                            if key != "status":
                                print(f"   {key}: {value}")
            else:
                unhealthy_services.append(service)
                if service.error_message:
                    print(f"   오류: {service.error_message}")
            
            print()
        
        # 요약 정보
        total_services = len(results)
        print("-" * 80)
        print("📈 요약")
        print("-" * 80)
        print(f"전체 서비스: {total_services}개")
        print(f"정상 서비스: {healthy_count}개")
        print(f"비정상 서비스: {total_services - healthy_count}개")
        
        if healthy_count == total_services:
            print("🎉 모든 서비스가 정상 작동 중입니다!")
        else:
            print(f"⚠️ {total_services - healthy_count}개 서비스에 문제가 있습니다.")
        
        # 평균 응답 시간
        avg_response_time = sum(s.response_time for s in results if s.response_time > 0) / len([s for s in results if s.response_time > 0])
        print(f"평균 응답 시간: {avg_response_time:.2f}ms")
        
        # 문제가 있는 서비스 상세 정보
        if unhealthy_services:
            print("\n" + "=" * 80)
            print("🚨 문제가 있는 서비스들")
            print("=" * 80)
            
            for service in unhealthy_services:
                print(f"❌ {service.name} (포트: {service.port})")
                print(f"   상태: {service.status}")
                
                if service.error_message:
                    print(f"   오류: {service.error_message}")
                
                # 해결 방법 제안
                if service.status == "offline":
                    print(f"   💡 해결방법: python services/{service.name.lower().replace(' ', '_')}/{service.name.lower().replace(' ', '_')}.py")
                elif service.status == "timeout":
                    print(f"   💡 해결방법: 서비스 재시작 또는 로그 확인")
                
                print()
        
        print("-" * 80)
        print("🔧 유용한 명령어들:")
        print("   모든 서비스 시작: python start_all_services.py")
        print("   모든 서비스 종료: python stop_all_services.py")
        print("   API 게이트웨이 테스트: python test_api_gateway.py")
    
    def save_results_json(self, results: List[ServiceInfo], filename: str = None):
        """결과를 JSON 파일로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_check_{timestamp}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "services": []
        }
        
        for service in results:
            service_data = {
                "name": service.name,
                "port": service.port,
                "status": service.status,
                "response_time_ms": service.response_time,
                "error_message": service.error_message,
                "response_data": service.response_data
            }
            data["services"].append(service_data)
        
        # 요약 정보 추가
        healthy_count = sum(1 for s in results if s.status == "healthy")
        data["summary"] = {
            "total_services": len(results),
            "healthy_services": healthy_count,
            "unhealthy_services": len(results) - healthy_count,
            "average_response_time_ms": sum(s.response_time for s in results if s.response_time > 0) / len([s for s in results if s.response_time > 0])
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"📄 결과가 {filename}에 저장되었습니다.")
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")

async def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🏥 주식 분석 시스템 - 서비스 헬스체크")
    print("=" * 80)
    print(f"검사 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    checker = HealthChecker()
    
    try:
        # 헬스체크 실행
        results = await checker.check_all_services()
        
        # 결과 출력
        checker.print_results(results)
        
        # JSON 저장 여부 확인
        save_json = input("\n결과를 JSON 파일로 저장하시겠습니까? (y/N): ").strip().lower()
        if save_json == 'y':
            checker.save_results_json(results)
        
    except KeyboardInterrupt:
        print("\n헬스체크가 중단되었습니다.")
    except Exception as e:
        print(f"❌ 헬스체크 실행 중 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 