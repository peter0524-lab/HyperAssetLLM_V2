#!/usr/bin/env python3
"""
HyperAsset Service Manager
서비스들을 안전하게 시작/중지/모니터링하는 매니저
"""

import os
import sys
import time
import json
import signal
import sqlite3
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('service_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.services_dir = self.base_dir / "services"
        self.processes: Dict[str, subprocess.Popen] = {}
        self.service_status_db = self.base_dir / "service_status.db"
        self.running = False
        
        # 서비스 정의 (포트와 실행 파일)
        self.service_definitions = {
            "api_gateway": {
                "port": 8005,
                "script": "services/api_gateway/run.py",
                "description": "API Gateway Service",
                "dependencies": []
            },
            "user_service": {
                "port": 8006,
                "script": "services/user_service/user_service.py",
                "description": "User Management Service",
                "dependencies": []
            },
            "news_service": {
                "port": 8001,
                "script": "services/news_service/main.py",
                "description": "News Analysis Service",
                "dependencies": ["user_service"]
            },
            "disclosure_service": {
                "port": 8002,
                "script": "services/disclosure_service/disclosure_service.py",
                "description": "Disclosure Analysis Service",
                "dependencies": ["user_service"]
            },
            "report_service": {
                "port": 8004,
                "script": "services/report_service/report_service.py",
                "description": "Report Analysis Service",
                "dependencies": ["user_service"]
            },
            "chart_service": {
                "port": 8003,
                "script": "services/chart_service/chart_service.py",
                "description": "Chart Analysis Service",
                "dependencies": ["user_service"]
            },
            "flow_service": {
                "port": 8010,
                "script": "services/flow_analysis_service/flow_analysis_service.py",
                "description": "Flow Analysis Service",
                "dependencies": ["user_service"]
            },
            "orchestrator": {
                "port": 8000,
                "script": "services/orchestrator/main.py",
                "description": "Task Orchestrator Service",
                "dependencies": ["user_service"]
            }
        }
        
        self.init_status_db()
        
    def init_status_db(self):
        """서비스 상태 추적 DB 초기화"""
        try:
            conn = sqlite3.connect(self.service_status_db)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS service_status (
                    service_name TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    port INTEGER,
                    pid INTEGER,
                    started_at TEXT,
                    last_health_check TEXT,
                    error_count INTEGER DEFAULT 0,
                    description TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("Service status DB initialized")
        except Exception as e:
            logger.error(f"Failed to init status DB: {e}")
    
    def update_service_status(self, service_name: str, status: str, pid: int = None):
        """서비스 상태 업데이트"""
        try:
            conn = sqlite3.connect(self.service_status_db)
            service_def = self.service_definitions.get(service_name, {})
            
            conn.execute('''
                INSERT OR REPLACE INTO service_status 
                (service_name, status, port, pid, started_at, last_health_check, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                service_name,
                status,
                service_def.get('port'),
                pid,
                datetime.now().isoformat() if status == 'running' else None,
                datetime.now().isoformat(),
                service_def.get('description', '')
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update status for {service_name}: {e}")
    
    def is_port_available(self, port: int) -> bool:
        """포트 사용 가능 여부 확인"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0
        except Exception:
            return True
    
    def start_service(self, service_name: str, user_id: str = None) -> bool:
        """개별 서비스 시작"""
        if service_name not in self.service_definitions:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        service_def = self.service_definitions[service_name]
        
        # 이미 실행 중인지 확인
        if service_name in self.processes and self.processes[service_name].poll() is None:
            logger.info(f"Service {service_name} is already running")
            return True
        
        # 포트 사용 가능 여부 확인
        if not self.is_port_available(service_def['port']):
            logger.warning(f"Port {service_def['port']} is already in use for {service_name}")
            # 포트가 사용 중이어도 서비스가 이미 실행 중일 수 있으므로 성공으로 처리
            self.update_service_status(service_name, 'running')
            return True
        
        # 의존성 확인
        for dep in service_def.get('dependencies', []):
            if not self.is_service_running(dep):
                logger.info(f"Starting dependency {dep} for {service_name}")
                if not self.start_service(dep, user_id):
                    logger.error(f"Failed to start dependency {dep}")
                    return False
                time.sleep(2)  # 의존성 서비스 시작 대기
        
        # 스크립트 경로 확인
        script_path = self.base_dir / service_def['script']
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            self.update_service_status(service_name, 'error')
            return False
        
        try:
            # 서비스 시작
            logger.info(f"Starting service: {service_name} on port {service_def['port']}")
            
            # Python 환경 설정
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.base_dir)
            
            # 🔥 사용자 ID 환경변수로 전달
            if user_id:
                env['HYPERASSET_USER_ID'] = user_id
                logger.info(f"Starting service {service_name} with user_id: {user_id}")
            
            # 프로세스 시작
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(self.base_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            self.processes[service_name] = process
            self.update_service_status(service_name, 'starting', process.pid)
            
            # 서비스 시작 확인 (최대 10초 대기)
            for i in range(10):
                if not self.is_port_available(service_def['port']):
                    self.update_service_status(service_name, 'running', process.pid)
                    logger.info(f"Service {service_name} started successfully on port {service_def['port']}")
                    return True
                time.sleep(1)
            
            # 시작 실패
            logger.error(f"Service {service_name} failed to start within 10 seconds")
            self.update_service_status(service_name, 'failed')
            return False
            
        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {e}")
            self.update_service_status(service_name, 'error')
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """개별 서비스 중지"""
        if service_name not in self.processes:
            logger.info(f"Service {service_name} is not running")
            return True
        
        try:
            process = self.processes[service_name]
            if process.poll() is None:  # 프로세스가 실행 중
                logger.info(f"Stopping service: {service_name}")
                process.terminate()
                
                # 정상 종료 대기 (5초)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing service: {service_name}")
                    process.kill()
                    process.wait()
            
            del self.processes[service_name]
            self.update_service_status(service_name, 'stopped')
            logger.info(f"Service {service_name} stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {e}")
            return False
    
    def is_service_running(self, service_name: str) -> bool:
        """서비스 실행 상태 확인"""
        if service_name not in self.service_definitions:
            return False
        
        # 프로세스 확인
        if service_name in self.processes:
            if self.processes[service_name].poll() is None:
                return True
        
        # 포트 확인
        port = self.service_definitions[service_name]['port']
        return not self.is_port_available(port)
    
    def start_core_services(self, user_id: str = None) -> bool:
        """핵심 서비스들 시작 (API Gateway, User Service)"""
        core_services = ["user_service", "api_gateway"]
        
        logger.info("Starting core services...")
        for service in core_services:
            if not self.start_service(service, user_id):
                logger.error(f"Failed to start core service: {service}")
                return False
            time.sleep(2)  # 서비스 간 시작 간격
        
        logger.info("Core services started successfully")
        return True
    
    def start_selected_services(self, service_list: List[str], user_id: str = None) -> bool:
        """선택된 서비스들 시작"""
        logger.info(f"Starting selected services: {service_list} for user: {user_id}")
        
        # 핵심 서비스 먼저 시작
        if not self.start_core_services(user_id):
            return False
        
        # 선택된 서비스들 시작
        for service in service_list:
            if service not in ["user_service", "api_gateway"]:  # 핵심 서비스는 이미 시작됨
                if not self.start_service(service, user_id):
                    logger.error(f"Failed to start service: {service}")
                    return False
                time.sleep(2)
        
        return True
    
    def get_service_status(self) -> Dict:
        """모든 서비스 상태 조회"""
        try:
            conn = sqlite3.connect(self.service_status_db)
            cursor = conn.execute('SELECT * FROM service_status')
            
            status = {}
            for row in cursor.fetchall():
                service_name = row[0]
                status[service_name] = {
                    'status': row[1],
                    'port': row[2],
                    'pid': row[3],
                    'started_at': row[4],
                    'last_health_check': row[5],
                    'error_count': row[6],
                    'description': row[7],
                    'is_running': self.is_service_running(service_name)
                }
            
            conn.close()
            return status
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {}
    
    def health_check(self):
        """서비스 상태 주기적 확인"""
        while self.running:
            try:
                for service_name in self.service_definitions:
                    is_running = self.is_service_running(service_name)
                    status = 'running' if is_running else 'stopped'
                    self.update_service_status(service_name, status)
                
                time.sleep(30)  # 30초마다 확인
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(30)
    
    def signal_handler(self, signum, frame):
        """신호 처리 (Ctrl+C 등)"""
        logger.info("Received shutdown signal")
        self.shutdown()
    
    def shutdown(self):
        """모든 서비스 종료"""
        logger.info("Shutting down all services...")
        self.running = False
        
        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)
        
        logger.info("Service manager shutdown complete")

# CLI 인터페이스
if __name__ == "__main__":
    manager = ServiceManager()
    
    # 신호 처리기 등록
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    if len(sys.argv) < 2:
        print("Usage: python service_manager.py [start-core|start-all|stop|status|start-services service1,service2,...]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "start-core":
        manager.running = True
        if manager.start_core_services():
            print("Core services started successfully")
            # 헬스체크 스레드 시작
            health_thread = threading.Thread(target=manager.health_check, daemon=True)
            health_thread.start()
            
            try:
                while manager.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("Failed to start core services")
            sys.exit(1)
    
    elif command == "start-services" and len(sys.argv) > 2:
        services = sys.argv[2].split(',')
        manager.running = True
        if manager.start_selected_services(services):
            print(f"Selected services started: {services}")
            # 헬스체크 스레드 시작
            health_thread = threading.Thread(target=manager.health_check, daemon=True)
            health_thread.start()
            
            try:
                while manager.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("Failed to start selected services")
            sys.exit(1)
    
    elif command == "status":
        status = manager.get_service_status()
        print(json.dumps(status, indent=2))
    
    elif command == "stop":
        manager.shutdown()
        print("All services stopped")
    
    else:
        print("Invalid command")
        sys.exit(1) 