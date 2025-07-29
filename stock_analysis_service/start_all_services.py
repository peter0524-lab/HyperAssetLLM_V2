#!/usr/bin/env python3
"""
모든 서비스 한 번에 시작하는 스크립트
- 의존성 순서에 맞춰 서비스 시작
- 각 서비스 시작 후 정상 동작 확인
- 로그 파일 자동 생성
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent

def log_info(message):
    """정보 로그 출력"""
    print(f"ℹ️ {message}")

def log_success(message):
    """성공 로그 출력"""
    print(f"✅ {message}")

def log_error(message):
    """에러 로그 출력"""
    print(f"❌ {message}")

def log_warning(message):
    """경고 로그 출력"""
    print(f"⚠️ {message}")

def check_port(port, timeout=10, service_name=""):
    """포트가 열렸는지 확인"""
    # news_service는 더 긴 타임아웃 적용
    if "News Service" in service_name:
        timeout = max(timeout, 60)  # 최소 60초
    
    for i in range(timeout):
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=3)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def start_service(service_name, command, port, wait_time=5):
    """서비스 시작"""
    log_info(f"{service_name} 시작 중...")
    
    # 로그 파일 경로
    log_file = PROJECT_ROOT / f"{service_name.lower()}.log"
    
    try:
        # 서비스 시작
        with open(log_file, 'w') as f:
            process = subprocess.Popen(
                command,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_ROOT
            )
        
        log_info(f"{service_name} 프로세스 시작됨 (PID: {process.pid})")
        log_info(f"로그 파일: {log_file}")
        
        # 시작 대기
        time.sleep(wait_time)
        
        # 포트 체크
        if check_port(port, timeout=15, service_name=service_name):
            log_success(f"{service_name} 정상 시작됨 (포트: {port})")
            return True
        else:
            log_error(f"{service_name} 시작 실패 - 포트 {port} 응답 없음")
            return False
            
    except Exception as e:
        log_error(f"{service_name} 시작 실패: {e}")
        return False

def kill_existing_services():
    """기존 실행 중인 서비스들 종료"""
    log_info("기존 실행 중인 서비스들 확인 및 종료...")
    
   # ports = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010]
    ports = [9998,8001,8002,8003,8004,8005,8006,8010]
    
    for port in ports:
        try:
            # Windows와 Unix 환경 모두 지원
            if os.name == 'nt':  # Windows
                result = subprocess.run(
                    ['netstat', '-ano', '|', 'findstr', f':{port}'],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if f':{port}' in line:
                            parts = line.split()
                            if len(parts) > 4:
                                pid = parts[-1]
                                try:
                                    subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                                    log_warning(f"포트 {port}의 기존 프로세스 종료됨 (PID: {pid})")
                                except:
                                    pass
            else:  # Unix/Linux/Mac
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            subprocess.run(['kill', '-9', pid], check=True)
                            log_warning(f"포트 {port}의 기존 프로세스 종료됨 (PID: {pid})")
                        except:
                            pass
        except:
            pass

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 주식 분석 시스템 - 모든 서비스 자동 시작")
    print("=" * 80)
    
    # venv 활성화 확인
    if 'VIRTUAL_ENV' not in os.environ:
        log_error("가상환경이 활성화되지 않았습니다!")
        log_info("다음 명령어로 가상환경을 활성화하세요:")
        log_info("source venv/bin/activate")
        sys.exit(1)
    
    log_success("가상환경 활성화 확인됨")
    
    # 기존 서비스 종료
    kill_existing_services()
    time.sleep(3)
    
    # 서비스 시작 순서 (의존성 기반)
    services = [
        {
            "name": "Simple Server Starter",
            "command": [sys.executable, "simple_server_starter.py"],
            "port": 9998,
            "wait_time": 5
        },
        {
            "name": "User Service",
            "command": [sys.executable, "services/user_service/user_service.py"],
            "port": 8006,
            "wait_time": 5
        },
        {
            "name": "News Service", 
            "command": [sys.executable, "services/news_service/main.py"],
            "port": 8001,
            "wait_time": 30  # Chrome Driver 및 임베딩 모델 초기화로 시간이 매우 오래 걸림
        },
        {
            "name": "Disclosure Service",
            "command": [sys.executable, "services/disclosure_service/disclosure_service.py"],
            "port": 8002,
            "wait_time": 8
        },
        {
            "name": "Chart Service",
            "command": [sys.executable, "services/chart_service/chart_service.py", "--mode", "api"],
            "port": 8003,
            "wait_time": 8
        },
        {
            "name": "Flow Analysis Service",
            "command": [sys.executable, "services/flow_analysis_service/flow_analysis_service.py"],
            "port": 8010,
            "wait_time": 8
        },
        {
            "name": "Report Service",
            "command": [sys.executable, "services/report_service/report_service.py"],
            "port": 8004,
            "wait_time": 8
        },
       # {
        #    "name": "Issue Scheduler Service",
        #        "command": [sys.executable, "services/issue_scheduler/issue_scheduler.py"],
        #        "port": 8007,
        #        "wait_time": 8
        #},
        #{
        #    "name": "Business Report Service",
        #    "command": [sys.executable, "services/business_report_service/business_report_service.py"],
        #    "port": 8008,
        #    "wait_time": 8
        #},
       # {
        #    "name": "Analysis Service",
        #    "command": [sys.executable, "services/analysis_service/analysis_service.py"],
        #    "port": 8009,
        #    "wait_time": 8
        #},
        {
            "name": "API Gateway",
            "command": [sys.executable, "services/api_gateway/main.py"],
            "port": 8005,
            "wait_time": 10
        }
    ]
    
    # 서비스별 시작
    success_count = 0
    total_count = len(services)
    
    for service in services:
        if start_service(
            service["name"],
            service["command"], 
            service["port"],
            service["wait_time"]
        ):
            success_count += 1
        else:
            log_warning(f"{service['name']} 시작에 실패했지만 계속 진행합니다...")
        
        print("-" * 60)
    
    # 스케줄러 시작
    log_info("오케스트레이터 스케줄러 시작 중...")
    try:
        log_file = PROJECT_ROOT / "scheduler.log"
        with open(log_file, 'w') as f:
            subprocess.Popen(
                [sys.executable, "services/orchestrator/scheduler.py"],
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_ROOT
            )
        log_success("스케줄러 시작됨")
        time.sleep(3)
    except Exception as e:
        log_error(f"스케줄러 시작 실패: {e}")
    
    # 최종 결과
    print("=" * 80)
    print("🎉 서비스 시작 완료!")
    print("=" * 80)
    
    log_info(f"성공: {success_count}/{total_count} 서비스")
    
    if success_count < total_count:
        log_warning("일부 서비스가 시작되지 않았습니다. 로그 파일을 확인하세요.")
    
    # 서비스 상태 확인
    print("\n📊 서비스 상태:")
    for service in services:
        try:
            response = requests.get(f"http://localhost:{service['port']}/health", timeout=2)
            if response.status_code == 200:
                print(f"   ✅ {service['name']} (포트: {service['port']}) - 정상")
            else:
                print(f"   ❌ {service['name']} (포트: {service['port']}) - 오류")
        except:
            print(f"   ❌ {service['name']} (포트: {service['port']}) - 연결 실패")
    
    print("\n📁 로그 파일들:")
    for log_file in PROJECT_ROOT.glob("*.log"):
        print(f"   📄 {log_file.name}")
    
    print("\n🔧 유용한 명령어들:")
    print("   서비스 상태 확인: python test_api_gateway.py")
    print("   모든 서비스 종료: python stop_all_services.py")
    print("   로그 실시간 확인: tail -f [서비스명].log")

if __name__ == "__main__":
    main() 