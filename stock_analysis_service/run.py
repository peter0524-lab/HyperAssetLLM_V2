#!/usr/bin/env python3
"""
주식 분석 서비스 메인 실행 파일
모든 마이크로서비스를 시작하고 관리하는 통합 런처
"""

import os
import sys
import time
import signal
import subprocess
import logging
from typing import Dict
from datetime import datetime
import psutil

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.env_local import (
    load_env_vars,
    get_env_var,
    get_int_env_var,
)

# 환경 변수 로드
load_env_vars()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("stock_analysis_service.log"),
    ],
)
logger = logging.getLogger(__name__)


class ServiceManager:
    """마이크로서비스 관리자"""

    def __init__(self):
        """서비스 매니저 초기화"""
        self.services = {}
        self.running = False

        # 서비스 설정
        self.service_configs = {
            "orchestrator": {
                "module": "services.orchestrator.main",
                "port": get_int_env_var("ORCHESTRATOR_PORT", 8000),
                "required": True,
                "description": "메인 오케스트레이터 서비스",
            },
            "news_service": {
                "module": "services.news_service.main",
                "port": get_int_env_var("NEWS_SERVICE_PORT", 8001),
                "required": True,
                "description": "뉴스 크롤링 서비스",
            },
            "disclosure_service": {
                "module": "services.disclosure_service.main",
                "port": get_int_env_var("DISCLOSURE_SERVICE_PORT", 8002),
                "required": True,
                "description": "공시 서비스",
            },
            "chart_service": {
                "module": "services.chart_service.main",
                "port": get_int_env_var("CHART_SERVICE_PORT", 8003),
                "required": True,
                "description": "차트 분석 서비스",
            },
            "notification_service": {
                "module": "services.notification_service.main",
                "port": get_int_env_var("NOTIFICATION_SERVICE_PORT", 8004),
                "required": True,
                "description": "알림 서비스",
            },
            "report_service": {
                "module": "services.report_service.main",
                "port": get_int_env_var("REPORT_SERVICE_PORT", 8005),
                "required": True,
                "description": "주간 보고서 서비스",
            },
            "analysis_service": {
                "module": "services.analysis_service.main",
                "port": get_int_env_var("ANALYSIS_SERVICE_PORT", 8006),
                "required": True,
                "description": "주가 원인 분석 서비스",
            },
            "monitoring_service": {
                "module": "services.monitoring_service.main",
                "port": get_int_env_var("MONITORING_SERVICE_PORT", 8007),
                "required": False,
                "description": "모니터링 대시보드",
            },
        }

    def check_prerequisites(self) -> bool:
        """서비스 실행 전 필수 조건 확인"""
        logger.info("=== 시스템 필수 조건 확인 중 ===")

        # Python 버전 확인
        python_version = sys.version_info
        if python_version.major < 3 or (
            python_version.major == 3 and python_version.minor < 8
        ):
            logger.error(
                f"Python 3.8 이상이 필요합니다. 현재: {python_version.major}.{python_version.minor}"
            )
            return False

        logger.info(
            f"✅ Python 버전: {python_version.major}.{python_version.minor}.{python_version.micro}"
        )

        # 필수 환경 변수 확인
        required_vars = [
            "TARGET_STOCK_CODE",
            "DATABASE_HOST",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "HYPERCLOVA_API_KEY",
            "DART_API_KEY",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
        ]

        missing_vars = []
        for var in required_vars:
            if not get_env_var(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(
                f"❌ 필수 환경 변수가 설정되지 않음: {', '.join(missing_vars)}"
            )
            return False

        logger.info("✅ 필수 환경 변수 확인 완료")

        # 포트 사용 가능 여부 확인
        for service_name, config in self.service_configs.items():
            port = config["port"]
            if self._is_port_in_use(port):
                logger.error(f"❌ 포트 {port}가 이미 사용 중입니다 ({service_name})")
                return False

        logger.info("✅ 포트 사용 가능 여부 확인 완료")

        # 데이터베이스 연결 확인
        try:
            from shared.database.mysql_client import mysql_client

            health = mysql_client.health_check()
            if health["status"] != "healthy":
                logger.error(
                    f"❌ MySQL 데이터베이스 연결 실패: {health.get('error', 'Unknown error')}"
                )
                return False
            logger.info("✅ MySQL 데이터베이스 연결 확인")
        except Exception as e:
            logger.error(f"❌ MySQL 데이터베이스 확인 실패: {e}")
            return False

        # 벡터 데이터베이스 확인
        try:
            from shared.database.vector_db import vector_db_client

            health = vector_db_client.health_check()
            if health["status"] != "healthy":
                logger.error(
                    f"❌ 벡터 데이터베이스 연결 실패: {health.get('error', 'Unknown error')}"
                )
                return False
            logger.info("✅ 벡터 데이터베이스 연결 확인")
        except Exception as e:
            logger.error(f"❌ 벡터 데이터베이스 확인 실패: {e}")
            return False

        # API 클라이언트 확인
        try:
            from shared.llm.hyperclova_client import hyperclova_client

            health = hyperclova_client.health_check()
            if health["status"] != "healthy":
                logger.warning(
                    f"⚠️ HyperCLOVA API 상태 불안정: {health.get('error', 'Unknown error')}"
                )
            else:
                logger.info("✅ HyperCLOVA API 연결 확인")
        except Exception as e:
            logger.warning(f"⚠️ HyperCLOVA API 확인 실패: {e}")

        logger.info("=== 시스템 필수 조건 확인 완료 ===\n")
        return True

    def _is_port_in_use(self, port: int) -> bool:
        """포트 사용 여부 확인"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False

    def start_service(self, service_name: str) -> bool:
        """개별 서비스 시작"""
        if service_name in self.services:
            logger.warning(f"서비스 {service_name}이 이미 실행 중입니다")
            return True

        config = self.service_configs[service_name]

        try:
            logger.info(f"🚀 서비스 시작: {service_name} ({config['description']})")

            # Python 모듈로 서비스 실행
            cmd = [
                sys.executable,
                "-m",
                config["module"],
                "--port",
                str(config["port"]),
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )

            # 서비스 시작 확인 (3초 대기)
            time.sleep(3)
            if process.poll() is None:
                self.services[service_name] = {
                    "process": process,
                    "config": config,
                    "start_time": datetime.now(),
                    "status": "running",
                }
                logger.info(
                    f"✅ 서비스 {service_name} 시작 완료 (PID: {process.pid}, PORT: {config['port']})"
                )
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ 서비스 {service_name} 시작 실패")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"❌ 서비스 {service_name} 시작 에러: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """개별 서비스 중지"""
        if service_name not in self.services:
            logger.warning(f"서비스 {service_name}이 실행 중이지 않습니다")
            return True

        try:
            service_info = self.services[service_name]
            process = service_info["process"]

            logger.info(f"🛑 서비스 중지: {service_name}")

            # 정상 종료 시도
            process.terminate()

            # 5초 대기 후 강제 종료
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"서비스 {service_name} 강제 종료")
                process.kill()
                process.wait()

            del self.services[service_name]
            logger.info(f"✅ 서비스 {service_name} 중지 완료")
            return True

        except Exception as e:
            logger.error(f"❌ 서비스 {service_name} 중지 에러: {e}")
            return False

    def start_all_services(self) -> bool:
        """모든 서비스 시작"""
        logger.info("=== 모든 서비스 시작 중 ===")

        # 서비스 시작 순서 (의존성 고려)
        start_order = [
            "orchestrator",  # 1. 메인 오케스트레이터 먼저
            "notification_service",  # 2. 알림 서비스
            "news_service",  # 3. 데이터 수집 서비스들
            "disclosure_service",
            "chart_service",
            "analysis_service",  # 4. 분석 서비스들
            "report_service",
            "monitoring_service",  # 5. 모니터링 (선택적)
        ]

        failed_services = []

        for service_name in start_order:
            if service_name in self.service_configs:
                success = self.start_service(service_name)
                if not success:
                    failed_services.append(service_name)
                    if self.service_configs[service_name]["required"]:
                        logger.error(f"필수 서비스 {service_name} 시작 실패")
                        return False

                # 서비스 간 시작 간격
                time.sleep(2)

        if failed_services:
            logger.warning(f"일부 서비스 시작 실패: {', '.join(failed_services)}")

        logger.info("=== 모든 서비스 시작 완료 ===\n")
        self.running = True
        return True

    def stop_all_services(self) -> None:
        """모든 서비스 중지"""
        logger.info("=== 모든 서비스 중지 중 ===")

        service_names = list(self.services.keys())
        for service_name in service_names:
            self.stop_service(service_name)

        self.running = False
        logger.info("=== 모든 서비스 중지 완료 ===")

    def get_status(self) -> Dict:
        """전체 시스템 상태 조회"""
        status = {
            "system": {
                "running": self.running,
                "total_services": len(self.service_configs),
                "running_services": len(self.services),
                "failed_services": len(self.service_configs) - len(self.services),
                "timestamp": datetime.now().isoformat(),
            },
            "services": {},
        }

        for service_name, config in self.service_configs.items():
            if service_name in self.services:
                service_info = self.services[service_name]
                process = service_info["process"]

                # 프로세스 상태 확인
                if process.poll() is None:
                    status["services"][service_name] = {
                        "status": "running",
                        "pid": process.pid,
                        "port": config["port"],
                        "start_time": service_info["start_time"].isoformat(),
                        "uptime_seconds": (
                            datetime.now() - service_info["start_time"]
                        ).total_seconds(),
                    }
                else:
                    status["services"][service_name] = {
                        "status": "stopped",
                        "pid": None,
                        "port": config["port"],
                        "error": "Process terminated",
                    }
            else:
                status["services"][service_name] = {
                    "status": "not_started",
                    "pid": None,
                    "port": config["port"],
                }

        return status

    def monitor_services(self) -> None:
        """서비스 모니터링 및 자동 재시작"""
        logger.info("서비스 모니터링 시작...")

        while self.running:
            try:
                # 각 서비스 상태 확인
                for service_name in list(self.services.keys()):
                    service_info = self.services[service_name]
                    process = service_info["process"]

                    # 프로세스가 종료되었는지 확인
                    if process.poll() is not None:
                        logger.error(
                            f"서비스 {service_name}이 예상치 못하게 종료됨 (PID: {process.pid})"
                        )

                        # 서비스 목록에서 제거
                        del self.services[service_name]

                        # 필수 서비스인 경우 재시작 시도
                        config = self.service_configs[service_name]
                        if config["required"]:
                            logger.info(f"필수 서비스 {service_name} 재시작 시도...")
                            self.start_service(service_name)

                # 30초마다 상태 확인
                time.sleep(30)

            except KeyboardInterrupt:
                logger.info("모니터링 중단 요청")
                break
            except Exception as e:
                logger.error(f"모니터링 에러: {e}")
                time.sleep(10)

    def signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 등)"""
        logger.info(f"시그널 {signum} 수신, 시스템 종료 중...")
        self.stop_all_services()
        sys.exit(0)


def main():
    """메인 함수"""
    print(
        """
    🚀 주식 분석 서비스 시작
    ========================
    """
    )

    # 서비스 매니저 초기화
    manager = ServiceManager()

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)

    try:
        # 1. 필수 조건 확인
        if not manager.check_prerequisites():
            logger.error("필수 조건을 만족하지 않습니다. 시스템을 확인해주세요.")
            sys.exit(1)

        # 2. 모든 서비스 시작
        if not manager.start_all_services():
            logger.error("서비스 시작에 실패했습니다.")
            manager.stop_all_services()
            sys.exit(1)

        # 3. 시스템 상태 출력
        status = manager.get_status()
        print(
            f"""
    ✅ 시스템 시작 완료!
    ==================
    실행 중인 서비스: {status['system']['running_services']}/{status['system']['total_services']}
    
    서비스 목록:"""
        )

        for service_name, service_status in status["services"].items():
            if service_status["status"] == "running":
                print(
                    f"    ✅ {service_name} (PID: {service_status['pid']}, PORT: {service_status['port']})"
                )
            else:
                print(f"    ❌ {service_name} (상태: {service_status['status']})")

        print(
            f"""
    🌐 모니터링 대시보드: http://localhost:{get_int_env_var('MONITORING_SERVICE_PORT', 8007)}
    🔧 오케스트레이터 API: http://localhost:{get_int_env_var('ORCHESTRATOR_PORT', 8000)}
    
    📝 로그는 'stock_analysis_service.log' 파일에서 확인할 수 있습니다.
    🛑 종료하려면 Ctrl+C를 누르세요.
    """
        )

        # 4. 서비스 모니터링 시작
        manager.monitor_services()

    except KeyboardInterrupt:
        logger.info("사용자 중단 요청")
    except Exception as e:
        logger.error(f"시스템 에러: {e}")
    finally:
        manager.stop_all_services()
        print("\n👋 주식 분석 서비스가 종료되었습니다.")


if __name__ == "__main__":
    main()
