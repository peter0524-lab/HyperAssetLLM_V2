#!/usr/bin/env python3
"""
오케스트레이터 서비스 (Orchestrator Service)
- 사용자가 활성화한 마이크로서비스만 관리 및 조율
- 서비스 시작/중단/재시작 관리
- 헬스체크 및 모니터링
- 자동 재시작 및 복구
- 사용자별 스케줄링 관리
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
import uvicorn

try:
    import requests
except ImportError:
    print("❌ requests 모듈이 설치되지 않았습니다. pip install requests를 실행하세요.")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("❌ httpx 모듈이 설치되지 않았습니다. pip install httpx를 실행하세요.")
    sys.exit(1)

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from shared.database.mysql_client import get_mysql_client
    from config.env_local import get_config
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print("프로젝트 루트 경로를 확인하세요.")
    sys.exit(1)

# Telegram API는 선택적으로 임포트
try:
    from shared.apis.telegram_api import TelegramBotClient
    TELEGRAM_AVAILABLE = True
except ImportError:
    print("⚠️ Telegram API를 사용할 수 없습니다. 알림 기능이 비활성화됩니다.")
    TELEGRAM_AVAILABLE = False
    class TelegramBotClient:
        async def send_message_async(self, message):
            pass

# FastAPI 앱 생성
app = FastAPI(
    title="Stock Analysis Orchestrator",
    description="주식 분석 시스템 오케스트레이터 - 사용자 기반 서비스 관리",
    version="2.0.0",
)


class UserBasedOrchestrator:
    """사용자 기반 서비스 오케스트레이터 클래스"""

    def __init__(self, config: Dict):
        self.config = config
        self.mysql_client = get_mysql_client()
        self.telegram_bot = TelegramBotClient() if TELEGRAM_AVAILABLE else TelegramBotClient()
        
        # 현재 관리 중인 사용자 ID
        self.current_user_id: Optional[str] = None
        
        # 사용자의 활성화된 서비스 목록
        self.active_services: List[str] = []

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # 전체 서비스 정의 (사용자가 선택할 수 있는 모든 서비스)
        self.all_services = {
            "news_service": {
                "name": "뉴스 크롤링 서비스",
                "script_path": "services/news_service/main.py",
                "port": 8001,
                "check_schedule": True,
                "process": None,
                "status": "stopped",
                "start_time": None,
                "restart_count": 0,
                "last_error": None,
            },
            "disclosure_service": {
                "name": "공시 서비스",
                "script_path": "services/disclosure_service/disclosure_service.py",
                "port": 8002,
                "check_schedule": True,
                "process": None,
                "status": "stopped",
                "start_time": None,
                "restart_count": 0,
                "last_error": None,
            },
            "chart_service": {
                "name": "차트 분석 서비스",
                "script_path": "services/chart_service/chart_service.py",
                "port": 8003,
                "check_schedule": True,
                "process": None,
                "status": "stopped",
                "start_time": None,
                "restart_count": 0,
                "last_error": None,
            },
            "report_service": {
                "name": "주간 보고서 서비스",
                "script_path": "services/report_service/report_service.py",
                "port": 8004,
                "check_schedule": False,
                "process": None,
                "status": "stopped",
                "start_time": None,
                "restart_count": 0,
                "last_error": None,
            },
            "flow_service": {
                "name": "자금 흐름 분석 서비스",
                "script_path": "services/flow_analysis_service/flow_analysis_service.py",
                "port": 8010,
                "check_schedule": True,
                "process": None,
                "status": "stopped",
                "start_time": None,
                "restart_count": 0,
                "last_error": None,
            },
        }

        # 현재 관리 중인 서비스들 (사용자가 활성화한 서비스만)
        self.services: Dict = {}

        # 최대 재시작 횟수
        self.max_restart_count = 3

        # 헬스체크 간격 (초)
        self.health_check_interval = 30

        # User Service URL
        self.user_service_url = "http://localhost:8006"

    async def load_user_services(self, user_id: str) -> bool:
        """사용자의 활성화된 서비스 목록을 로드"""
        try:
            self.logger.info(f"🔍 사용자 서비스 설정 로드: {user_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.user_service_url}/users/{user_id}/wanted-services")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        wanted_services = data.get("data", {})
                        
                        # 활성화된 서비스만 필터링
                        self.active_services = []
                        service_mapping = {
                            "news_service": "news_service",
                            "disclosure_service": "disclosure_service",
                            "report_service": "report_service", 
                            "chart_service": "chart_service",
                            "flow_service": "flow_service"
                        }
                        
                        for service_key, service_name in service_mapping.items():
                            if wanted_services.get(service_key, False):
                                self.active_services.append(service_name)
                        
                        # 현재 관리할 서비스 목록 업데이트
                        self.services = {
                            name: service.copy() 
                            for name, service in self.all_services.items() 
                            if name in self.active_services
                        }
                        
                        self.current_user_id = user_id
                        
                        self.logger.info(f"✅ 사용자 {user_id}의 활성화된 서비스: {self.active_services}")
                        return True
                    else:
                        self.logger.error(f"❌ 사용자 서비스 설정 조회 실패: {data}")
                        return False
                else:
                    self.logger.error(f"❌ User Service 연결 실패: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ 사용자 서비스 로드 실패: {e}")
            return False

    async def start_service(self, service_name: str) -> bool:
        """서비스 시작 - 사용자 컨텍스트 포함"""
        try:
            if service_name not in self.services:
                self.logger.error(f"관리 대상이 아닌 서비스: {service_name}")
                return False

            service = self.services[service_name]

            # 이미 실행 중인 경우
            if service["status"] == "running":
                self.logger.info(f"서비스 이미 실행 중: {service_name}")
                return True

            # 스크립트 파일 경로 확인
            script_path = project_root / service["script_path"]
            if not script_path.exists():
                self.logger.error(f"스크립트 파일 없음: {script_path}")
                service["status"] = "error"
                service["last_error"] = f"스크립트 파일 없음: {script_path}"
                return False

            # 파이썬 스크립트 실행
            if service_name == "chart_service":
                cmd = [sys.executable, str(script_path), "--api"]
            else:
                cmd = [sys.executable, str(script_path)]

            # 환경변수 설정 (사용자 컨텍스트 포함)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)
            if self.current_user_id:
                env["HYPERASSET_USER_ID"] = self.current_user_id

            self.logger.info(f"🚀 서비스 시작 (사용자: {self.current_user_id}): {service_name}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_root,
                env=env
            )

            service["process"] = process
            service["status"] = "starting"
            service["start_time"] = datetime.now()
            service["last_error"] = None

            # 서비스가 실제로 시작될 때까지 대기
            startup_success = await self.wait_for_service_startup(service_name, timeout=60)

            if startup_success:
                service["status"] = "running"
                self.logger.info(f"✅ 서비스 시작 완료: {service_name} (PID: {process.pid})")
                await self.send_service_alert(service_name, "started")
                return True
            else:
                service["status"] = "failed"
                self.logger.error(f"❌ 서비스 시작 실패: {service_name} (시작 대기 시간 초과)")

                # 프로세스 종료
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()

                return False

        except Exception as e:
            self.logger.error(f"서비스 시작 실패: {service_name}, {e}")
            if service_name in self.services:
                self.services[service_name]["status"] = "error"
                self.services[service_name]["last_error"] = str(e)
            return False

    async def wait_for_service_startup(self, service_name: str, timeout: int = 60) -> bool:
        """서비스가 실제로 시작될 때까지 대기"""
        service = self.services[service_name]
        port = service["port"]

        start_time = asyncio.get_event_loop().time()
        self.logger.info(f"⏱️ 서비스 시작 대기: {service_name} (포트: {port}, 최대 {timeout}초)")

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=2)
                if response.status_code == 200:
                    self.logger.info(f"✅ 서비스 헬스체크 성공: {service_name}")
                    return True
            except requests.exceptions.RequestException:
                pass

            if service["process"].returncode is not None:
                self.logger.error(f"❌ 서비스 프로세스가 예기치 않게 종료됨: {service_name}")
                return False

            await asyncio.sleep(1)

        return False

    async def send_schedule_signals(self):
        """활성화된 서비스에만 스케줄링 신호 전송"""
        for service_name, service in self.services.items():
            if service.get("check_schedule", False) and service["status"] == "running":
                try:
                    response = requests.post(
                        f"http://localhost:{service['port']}/check-schedule",
                        timeout=10
                    )

                    if response.status_code == 200:
                        result = response.json()
                        if result.get("executed", False):
                            self.logger.info(f"✅ 스케줄링 실행: {service_name} - {result.get('message', '')}")
                        else:
                            self.logger.info(f"⏳ 스케줄링 대기: {service_name} - {result.get('message', '')}")
                    else:
                        self.logger.warning(f"❌ 스케줄링 신호 실패: {service_name} - {response.status_code}")

                except Exception as e:
                    self.logger.error(f"스케줄링 신호 전송 실패: {service_name} - {e}")

    async def start_user_services(self, user_id: str) -> bool:
        """특정 사용자의 활성화된 서비스들만 시작"""
        try:
            # 사용자 서비스 설정 로드
            if not await self.load_user_services(user_id):
                return False
            
            if not self.active_services:
                self.logger.info(f"사용자 {user_id}가 활성화한 서비스가 없습니다")
                return True
            
            self.logger.info(f"🚀 사용자 {user_id}의 서비스 시작: {self.active_services}")
            
            # 활성화된 서비스들만 시작
            success_count = 0
            for service_name in self.active_services:
                self.logger.info(f"🔄 {service_name} 시작 중...")
                success = await self.start_service(service_name)
                
                if success:
                    success_count += 1
                    self.logger.info(f"✅ {service_name} 시작 성공")
                else:
                    self.logger.error(f"❌ {service_name} 시작 실패")
                
                # 서비스 간 시작 간격
                await asyncio.sleep(3)
            
            self.logger.info(f"🎉 사용자 {user_id} 서비스 시작 완료: {success_count}/{len(self.active_services)}")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"❌ 사용자 서비스 시작 실패: {e}")
            return False

    async def stop_service(self, service_name: str) -> bool:
        """서비스 중단"""
        try:
            if service_name not in self.services:
                self.logger.error(f"관리 대상이 아닌 서비스: {service_name}")
                return False

            service = self.services[service_name]

            if service["status"] != "running" or not service["process"]:
                self.logger.info(f"서비스 이미 중단됨: {service_name}")
                return True

            # 프로세스 종료
            process = service["process"]
            process.terminate()

            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

            service["process"] = None
            service["status"] = "stopped"

            self.logger.info(f"⛔ 서비스 중단 완료: {service_name}")
            await self.send_service_alert(service_name, "stopped")
            return True

        except Exception as e:
            self.logger.error(f"서비스 중단 실패: {service_name}, {e}")
            return False

    async def stop_all_user_services(self):
        """현재 사용자의 모든 서비스 중단"""
        self.logger.info(f"🛑 사용자 {self.current_user_id}의 모든 서비스 중단")
        
        for service_name in list(self.services.keys()):
            await self.stop_service(service_name)
        
        # 사용자 컨텍스트 초기화
        self.current_user_id = None
        self.active_services = []
        self.services = {}

    async def check_service_health(self, service_name: str) -> bool:
        """서비스 헬스체크"""
        try:
            service = self.services[service_name]

            if service["status"] != "running" or not service["process"]:
                return False

            # 프로세스 상태 확인
            if service["process"].returncode is not None:
                service["status"] = "crashed"
                self.logger.warning(f"⚠️ 서비스 프로세스 종료 감지: {service_name}")
                return False

            # HTTP 헬스체크
            try:
                response = requests.get(
                    f"http://localhost:{service['port']}/health",
                    timeout=5
                )
                return response.status_code == 200
            except requests.exceptions.RequestException:
                return False

        except Exception as e:
            self.logger.error(f"서비스 헬스체크 실패: {service_name}, {e}")
            return False

    async def send_service_alert(self, service_name: str, action: str):
        """서비스 상태 알림 전송"""
        try:
            service = self.services[service_name]
            service_name_kr = service["name"]
            user_info = f" (사용자: {self.current_user_id})" if self.current_user_id else ""

            if action == "started":
                message = f"✅ 서비스 시작: {service_name_kr}{user_info}"
            elif action == "stopped":
                message = f"⛔ 서비스 중단: {service_name_kr}{user_info}"
            elif action == "restarted":
                message = f"🔄 서비스 재시작: {service_name_kr}{user_info}"
            else:
                message = f"📢 서비스 알림: {service_name_kr} - {action}{user_info}"

            await self.telegram_bot.send_message_async(message)

        except Exception as e:
            self.logger.error(f"서비스 알림 전송 실패: {e}")

    async def health_check_loop(self):
        """헬스체크 루프 - 활성화된 서비스만 체크"""
        while True:
            try:
                if not self.services:
                    await asyncio.sleep(self.health_check_interval)
                    continue
                    
                for service_name in list(self.services.keys()):
                    is_healthy = await self.check_service_health(service_name)

                    if not is_healthy and self.services[service_name]["status"] == "crashed":
                        restart_count = self.services[service_name]["restart_count"]

                        if restart_count < self.max_restart_count:
                            self.logger.warning(f"🔄 서비스 자동 재시작: {service_name}")
                            await self.start_service(service_name)
                            self.services[service_name]["restart_count"] += 1
                        else:
                            self.logger.error(f"❌ 서비스 재시작 한도 초과: {service_name}")

                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                self.logger.error(f"헬스체크 루프 오류: {e}")
                await asyncio.sleep(60)

    async def schedule_loop(self):
        """스케줄링 루프 - 30분마다 실행"""
        self.logger.info("📅 스케줄링 루프 시작 (30분 간격)")

        while True:
            try:
                if self.services:  # 활성화된 서비스가 있을 때만
                    await self.send_schedule_signals()
                await asyncio.sleep(1800)  # 30분 대기
            except Exception as e:
                self.logger.error(f"스케줄링 루프 오류: {e}")
                await asyncio.sleep(60)


# 글로벌 오케스트레이터 인스턴스
orchestrator = None


def get_orchestrator():
    """오케스트레이터 인스턴스 반환 (지연 초기화)"""
    global orchestrator
    if orchestrator is None:
        orchestrator = UserBasedOrchestrator(get_config())
    return orchestrator


# FastAPI 엔드포인트
@app.get("/")
async def root():
    return {"message": "User-Based Stock Analysis Orchestrator", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/services")
async def get_services():
    """현재 관리 중인 서비스 상태 조회"""
    orchestrator_instance = get_orchestrator()
    services_status = {}
    
    for name, service in orchestrator_instance.services.items():
        services_status[name] = {
            "name": service["name"],
            "status": service["status"],
            "port": service["port"],
            "start_time": (
                service["start_time"].isoformat() if service["start_time"] else None
            ),
            "restart_count": service["restart_count"],
            "last_error": service["last_error"],
        }
    
    return {
        "user_id": orchestrator_instance.current_user_id,
        "active_services": orchestrator_instance.active_services,
        "services": services_status
    }


@app.post("/user/{user_id}/start")
async def start_user_services_endpoint(user_id: str):
    """특정 사용자의 활성화된 서비스들 시작"""
    try:
        success = await get_orchestrator().start_user_services(user_id)
        if success:
            return {"message": f"사용자 {user_id}의 서비스 시작 완료"}
        else:
            raise HTTPException(status_code=500, detail=f"사용자 {user_id}의 서비스 시작 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서비스 시작 실패: {str(e)}")


@app.post("/user/{user_id}/stop")
async def stop_user_services_endpoint(user_id: str):
    """특정 사용자의 모든 서비스 중단"""
    try:
        orchestrator_instance = get_orchestrator()
        if orchestrator_instance.current_user_id == user_id:
            await orchestrator_instance.stop_all_user_services()
            return {"message": f"사용자 {user_id}의 서비스 중단 완료"}
        else:
            raise HTTPException(status_code=400, detail=f"현재 관리 중인 사용자가 아닙니다: {user_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서비스 중단 실패: {str(e)}")


@app.post("/services/{service_name}/start")
async def start_service_endpoint(service_name: str):
    """개별 서비스 시작"""
    success = await get_orchestrator().start_service(service_name)
    if success:
        return {"message": f"서비스 시작 완료: {service_name}"}
    else:
        raise HTTPException(status_code=500, detail=f"서비스 시작 실패: {service_name}")


@app.post("/services/{service_name}/stop")
async def stop_service_endpoint(service_name: str):
    """개별 서비스 중단"""
    success = await get_orchestrator().stop_service(service_name)
    if success:
        return {"message": f"서비스 중단 완료: {service_name}"}
    else:
        raise HTTPException(status_code=500, detail=f"서비스 중단 실패: {service_name}")


@app.get("/user/{user_id}/services")
async def get_user_services(user_id: str):
    """사용자의 활성화된 서비스 목록 조회"""
    try:
        orchestrator_instance = get_orchestrator()
        
        # 임시로 사용자 서비스 로드
        temp_orchestrator = UserBasedOrchestrator(get_config())
        success = await temp_orchestrator.load_user_services(user_id)
        
        if success:
            return {
                "user_id": user_id,
                "active_services": temp_orchestrator.active_services,
                "available_services": list(temp_orchestrator.all_services.keys())
            }
        else:
            raise HTTPException(status_code=404, detail=f"사용자 {user_id}의 서비스 설정을 찾을 수 없습니다")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용자 서비스 조회 실패: {str(e)}")


# 백그라운드 태스크 관리
background_tasks = {}


async def run_background_tasks():
    """백그라운드 태스크 실행 (헬스체크, 스케줄링)"""
    try:
        orchestrator_instance = get_orchestrator()
        
        # 헬스체크 루프 시작
        health_check_task = asyncio.create_task(orchestrator_instance.health_check_loop())
        
        # 스케줄링 루프 시작
        schedule_task = asyncio.create_task(orchestrator_instance.schedule_loop())
        
        background_tasks["health_check"] = health_check_task
        background_tasks["schedule"] = schedule_task
        
        orchestrator_instance.logger.info("🚀 백그라운드 태스크 시작 완료")
        
        # 두 태스크를 동시에 실행
        await asyncio.gather(health_check_task, schedule_task)
        
    except Exception as e:
        orchestrator_instance.logger.error(f"백그라운드 태스크 실행 에러: {e}")


@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    # 백그라운드에서 태스크 실행
    asyncio.create_task(run_background_tasks())


@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 실행"""
    try:
        orchestrator_instance = get_orchestrator()
        orchestrator_instance.logger.info("🛑 Orchestrator 종료 - 모든 서비스 정리 중...")
        
        # 현재 사용자의 모든 서비스 중단
        await orchestrator_instance.stop_all_user_services()
        
        # 백그라운드 태스크 정리
        for task_name, task in background_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        orchestrator_instance.logger.info("✅ Orchestrator 종료 완료")
        
    except Exception as e:
        print(f"종료 중 오류: {e}")


def main():
    """메인 실행 함수"""
    try:
        # FastAPI 서버 실행
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("🛑 오케스트레이터 중단")
    except Exception as e:
        print(f"❌ 오케스트레이터 실행 실패: {e}")


if __name__ == "__main__":
    main()
