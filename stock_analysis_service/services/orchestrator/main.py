#!/usr/bin/env python3
"""
오케스트레이터 서비스 (Orchestrator Service)
- 모든 마이크로서비스 관리 및 조율
- 서비스 시작/중단/재시작 관리
- 헬스체크 및 모니터링
- 자동 재시작 및 복구
- 스케줄링 관리
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict
from pathlib import Path
from fastapi import FastAPI, HTTPException
import uvicorn
import requests

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config

# FastAPI 앱 생성
app = FastAPI(
    title="Stock Analysis Orchestrator",
    description="주식 분석 시스템 오케스트레이터",
    version="1.0.0",
)


class ServiceOrchestrator:
    """서비스 오케스트레이터 클래스"""

    def __init__(self, config: Dict):
        self.config = config
        self.mysql_client = get_mysql_client()
        self.telegram_bot = TelegramBotClient()

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # 서비스 정의 (완전 수정된 버전)
        self.services = {
            "news_service": {
                "name": "뉴스 크롤링 서비스",
                "script_path": "services/news_service/main.py",
                "port": 8001,
                "check_schedule": True,  # 스케줄링 신호 필요
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
                "check_schedule": True,  # 스케줄링 신호 필요
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
                "check_schedule": True,  # 스케줄링 신호 필요
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
                "check_schedule": False,  # 주간 보고서는 자체 스케줄링
                "process": None,
                "status": "stopped",
                "start_time": None,
                "restart_count": 0,
                "last_error": None,
            },
            "flow_analysis_service": {
                "name": "자금 흐름 분석 서비스",
                "script_path": "services/flow_analysis_service/flow_analysis_service.py",
                "port": 8010,
                "check_schedule": True,  # 스케줄링 신호 필요
                "process": None,
                "status": "stopped",
                "start_time": None,
                "restart_count": 0,
                "last_error": None,
            },
            "user_service": {
                "name": "사용자 설정 관리 서비스",
                "script_path": "services/user_service/user_service.py",
                "port": 8006,
                "check_schedule": False,  # 사용자 서비스는 스케줄링 불필요
                "process": None,
                "status": "stopped",
                "start_time": None,
                "restart_count": 0,
                "last_error": None,
            },
        }

        # 최대 재시작 횟수
        self.max_restart_count = 3

        # 헬스체크 간격 (초)
        self.health_check_interval = 30

        # 서비스 시작 순서 (의존성 기반)
        self.service_start_order = [
            "user_service",         # 1순위: 다른 서비스에서 사용자 설정 필요
            "news_service",         # 2순위: ChromaDB 초기화
            "disclosure_service",   # 3순위
            "chart_service",        # 4순위
            "flow_analysis_service", # 5순위
            "report_service",       # 6순위: 가장 나중에
        ]

        # 서비스별 시작 대기 시간 (초)
        self.start_delays = {
            "user_service": 5,      # 가장 먼저 (다른 서비스에서 필요)
            "news_service": 15,     # 뉴스 서비스 (ChromaDB 초기화 시간)
            "disclosure_service": 10,
            "chart_service": 10,
            "flow_analysis_service": 10,
            "report_service": 5,    # 가장 가벼움
        }

    async def start_service(self, service_name: str) -> bool:
        """서비스 시작 - 완전 수정된 버전"""
        try:
            if service_name not in self.services:
                self.logger.error(f"알 수 없는 서비스: {service_name}")
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

            # 파이썬 스크립트 직접 실행 (차트 서비스 특별 처리)
            if service_name == "chart_service":
                cmd = [sys.executable, str(script_path), "--api"]
            else:
                cmd = [sys.executable, str(script_path)]

            # 환경변수 설정
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)

            self.logger.info(f"서비스 시작 시도: {service_name} - {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_root,
                env=env
            )

            service["process"] = process
            service["status"] = "starting"  # starting 상태 추가
            service["start_time"] = datetime.now()
            service["last_error"] = None

            self.logger.info(f"서비스 프로세스 시작: {service_name} (PID: {process.pid})")

            # 서비스가 실제로 시작될 때까지 대기 (최대 30초)
            startup_success = await self.wait_for_service_startup(service_name, timeout=30)

            if startup_success:
                service["status"] = "running"
                self.logger.info(f"서비스 시작 완료: {service_name} (PID: {process.pid})")
                await self.send_service_alert(service_name, "started")
                return True
            else:
                service["status"] = "failed"
                self.logger.error(f"서비스 시작 실패: {service_name} (시작 대기 시간 초과)")

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

    async def wait_for_service_startup(self, service_name: str, timeout: int = 30) -> bool:
        """서비스가 실제로 시작될 때까지 대기"""
        service = self.services[service_name]
        port = service["port"]

        start_time = asyncio.get_event_loop().time()

        self.logger.info(f"서비스 시작 대기 중: {service_name} (포트: {port}, 최대 {timeout}초)")

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # 헬스체크 엔드포인트 호출
                response = requests.get(
                    f"http://localhost:{port}/health",
                    timeout=2
                )
                if response.status_code == 200:
                    self.logger.info(f"서비스 헬스체크 성공: {service_name}")
                    return True
            except requests.exceptions.RequestException:
                # 아직 서비스가 준비되지 않음
                pass

            # 프로세스가 종료되었는지 확인
            if service["process"].returncode is not None:
                self.logger.error(f"서비스 프로세스가 예기치 않게 종료됨: {service_name}")
                return False

            await asyncio.sleep(1)  # 1초 대기 후 재시도

        self.logger.error(f"서비스 시작 대기 시간 초과: {service_name}")
        return False

    async def stop_service(self, service_name: str) -> bool:
        """서비스 중단"""
        try:
            if service_name not in self.services:
                self.logger.error(f"알 수 없는 서비스: {service_name}")
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

            self.logger.info(f"서비스 중단 완료: {service_name}")

            # 중단 알림 전송
            await self.send_service_alert(service_name, "stopped")

            return True

        except Exception as e:
            self.logger.error(f"서비스 중단 실패: {service_name}, {e}")
            return False

    async def restart_service(self, service_name: str) -> bool:
        """서비스 재시작"""
        try:
            self.logger.info(f"서비스 재시작: {service_name}")

            # 서비스 중단
            await self.stop_service(service_name)

            # 잠시 대기
            await asyncio.sleep(2)

            # 서비스 시작
            success = await self.start_service(service_name)

            if success:
                self.services[service_name]["restart_count"] += 1
                self.logger.info(f"서비스 재시작 완료: {service_name}")

                # 재시작 알림 전송
                await self.send_service_alert(service_name, "restarted")

            return success

        except Exception as e:
            self.logger.error(f"서비스 재시작 실패: {service_name}, {e}")
            return False

    async def check_service_health(self, service_name: str) -> bool:
        """서비스 헬스체크 - 개선된 버전"""
        try:
            service = self.services[service_name]

            if service["status"] != "running" or not service["process"]:
                return False

            # 프로세스 상태 확인
            if service["process"].returncode is not None:
                service["status"] = "crashed"  # crashed 상태로 변경
                self.logger.warning(f"서비스 프로세스 종료 감지: {service_name}")
                return False

            # HTTP 헬스체크 개선
            try:
                response = requests.get(
                    f"http://localhost:{service['port']}/health",
                    timeout=5
                )

                if response.status_code == 200:
                    # 응답 내용도 확인
                    try:
                        health_data = response.json()
                        if health_data.get("status") == "healthy":
                            return True
                        else:
                            self.logger.warning(f"서비스 상태 이상: {service_name} - {health_data}")
                            return False
                    except Exception:
                        # JSON 파싱 실패해도 200이면 일단 OK
                        return True
                else:
                    self.logger.warning(f"서비스 HTTP 오류: {service_name} - {response.status_code}")
                    return False

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"서비스 HTTP 연결 실패: {service_name} - {e}")
                return False

        except Exception as e:
            self.logger.error(f"서비스 헬스체크 실패: {service_name}, {e}")
            return False

    async def send_service_alert(self, service_name: str, action: str):
        """서비스 상태 알림 전송"""
        try:
            service = self.services[service_name]
            service_name_kr = service["name"]

            if action == "started":
                message = f"✅ 서비스 시작: {service_name_kr}"
            elif action == "stopped":
                message = f"⛔ 서비스 중단: {service_name_kr}"
            elif action == "restarted":
                message = f"🔄 서비스 재시작: {service_name_kr}"
            elif action == "error":
                message = f"❌ 서비스 오류: {service_name_kr}"
            else:
                message = f"📢 서비스 알림: {service_name_kr} - {action}"

            await self.telegram_bot.send_message_async(message)

        except Exception as e:
            self.logger.error(f"서비스 알림 전송 실패: {e}")

    async def send_schedule_signals(self):
        """모든 서비스에 스케줄링 신호 전송"""
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

    async def schedule_loop(self):
        """스케줄링 루프 - 30분마다 실행"""
        self.logger.info("스케줄링 루프 시작 (30분 간격)")

        while True:
            try:
                await self.send_schedule_signals()
                await asyncio.sleep(1800)  # 30분 대기 (1800초)
            except Exception as e:
                self.logger.error(f"스케줄링 루프 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기 후 재시도

    async def start_all_services(self):
        """모든 서비스 시작 - 의존성 순서 및 시간 차등화"""
        self.logger.info("모든 서비스 시작 (의존성 순서 기반)")

        for service_name in self.service_start_order:
            if service_name in self.services:  # 안전 체크
                self.logger.info(f"🚀 {service_name} 시작 중...")
                success = await self.start_service(service_name)

                if success:
                    self.logger.info(f"✅ {service_name} 시작 성공")
                else:
                    self.logger.error(f"❌ {service_name} 시작 실패")

                # 서비스별 차등 대기 시간
                delay = self.start_delays.get(service_name, 10)
                self.logger.info(f"⏱️ {service_name} 안정화 대기: {delay}초")
                await asyncio.sleep(delay)
            else:
                self.logger.warning(f"⚠️ 정의되지 않은 서비스: {service_name}")

        self.logger.info("🎉 모든 서비스 시작 완료")

    async def stop_all_services(self):
        """모든 서비스 중단"""
        self.logger.info("모든 서비스 중단")

        for service_name in self.services:
            await self.stop_service(service_name)

    async def health_check_loop(self):
        """헬스체크 루프"""
        while True:
            try:
                for service_name in self.services:
                    is_healthy = await self.check_service_health(service_name)

                    if (
                        not is_healthy
                        and self.services[service_name]["status"] == "crashed"
                    ):
                        # 서비스 크래시 감지 - 자동 재시작
                        restart_count = self.services[service_name]["restart_count"]

                        if restart_count < self.max_restart_count:
                            self.logger.warning(f"서비스 자동 재시작: {service_name}")
                            await self.restart_service(service_name)
                        else:
                            self.logger.error(
                                f"서비스 재시작 한도 초과: {service_name}"
                            )
                            await self.send_service_alert(
                                service_name, "failed_restart_limit"
                            )

                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                self.logger.error(f"헬스체크 루프 오류: {e}")
                await asyncio.sleep(60)

    async def run_orchestrator(self):
        """오케스트레이터 메인 실행 - 수정된 버전"""
        try:
            self.logger.info("오케스트레이터 시작")

            # 모든 서비스 시작 (순차적으로)
            await self.start_all_services()

            # 헬스체크 루프 시작
            health_check_task = asyncio.create_task(self.health_check_loop())

            # 스케줄링 루프 시작
            schedule_task = asyncio.create_task(self.schedule_loop())

            self.logger.info("모든 백그라운드 태스크 시작 완료")

            # 두 태스크를 동시에 실행
            await asyncio.gather(health_check_task, schedule_task)

        except Exception as e:
            self.logger.error(f"오케스트레이터 실행 에러: {e}")
        finally:
            # 서비스 정리
            self.logger.info("오케스트레이터 종료 - 모든 서비스 정리 중...")
            await self.stop_all_services()


# 글로벌 오케스트레이터 인스턴스
orchestrator = None


def get_orchestrator():
    """오케스트레이터 인스턴스 반환 (지연 초기화)"""
    global orchestrator
    if orchestrator is None:
        orchestrator = ServiceOrchestrator(get_config())
    return orchestrator


# FastAPI 엔드포인트
@app.get("/")
async def root():
    return {"message": "Stock Analysis Orchestrator", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/services")
async def get_services():
    """모든 서비스 상태 조회"""
    services_status = {}
    for name, service in get_orchestrator().services.items():
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
    return services_status


@app.post("/services/{service_name}/start")
async def start_service_endpoint(service_name: str):
    """서비스 시작"""
    success = await get_orchestrator().start_service(service_name)
    if success:
        return {"message": f"서비스 시작 완료: {service_name}"}
    else:
        raise HTTPException(status_code=500, detail=f"서비스 시작 실패: {service_name}")


@app.post("/services/{service_name}/stop")
async def stop_service_endpoint(service_name: str):
    """서비스 중단"""
    success = await get_orchestrator().stop_service(service_name)
    if success:
        return {"message": f"서비스 중단 완료: {service_name}"}
    else:
        raise HTTPException(status_code=500, detail=f"서비스 중단 실패: {service_name}")


@app.post("/services/{service_name}/restart")
async def restart_service_endpoint(service_name: str):
    """서비스 재시작"""
    success = await get_orchestrator().restart_service(service_name)
    if success:
        return {"message": f"서비스 재시작 완료: {service_name}"}
    else:
        raise HTTPException(
            status_code=500, detail=f"서비스 재시작 실패: {service_name}"
        )


@app.post("/services/start-all")
async def start_all_services_endpoint():
    """모든 서비스 시작"""
    await get_orchestrator().start_all_services()
    return {"message": "모든 서비스 시작 완료"}


@app.post("/services/stop-all")
async def stop_all_services_endpoint():
    """모든 서비스 중단"""
    await get_orchestrator().stop_all_services()
    return {"message": "모든 서비스 중단 완료"}


@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    # 백그라운드에서 오케스트레이터 실행
    asyncio.create_task(get_orchestrator().run_orchestrator())


def main():
    """메인 실행 함수"""
    try:
        # FastAPI 서버 실행
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("오케스트레이터 중단")
    except Exception as e:
        print(f"오케스트레이터 실행 실패: {e}")


if __name__ == "__main__":
    main()
