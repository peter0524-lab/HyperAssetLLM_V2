#!/usr/bin/env python3
"""
완전한 시스템 실행 스크립트
- 백엔드 서비스들 자동 시작
- 프론트엔드 자동 시작
- 모든 서비스 상태 모니터링
"""

import os
import sys
import time
import subprocess
import threading
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

def check_port(port, timeout=10):
    """포트가 열렸는지 확인"""
    for i in range(timeout):
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=3)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def start_backend_services():
    """백엔드 서비스들 시작"""
    log_info("🚀 백엔드 서비스들 시작 중...")
    
    try:
        # start_all_services.py 실행
        result = subprocess.run(
            [sys.executable, "start_all_services.py"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log_success("백엔드 서비스들 시작 완료!")
            return True
        else:
            log_error(f"백엔드 서비스 시작 실패: {result.stderr}")
            return False
            
    except Exception as e:
        log_error(f"백엔드 서비스 시작 중 오류: {e}")
        return False

def start_frontend():
    """프론트엔드 시작"""
    log_info("🌐 프론트엔드 시작 중...")
    
    frontend_dir = PROJECT_ROOT / "frontend"
    
    try:
        # npm run dev 실행
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # 프론트엔드 시작 대기
        time.sleep(10)
        
        if check_port(5173, timeout=30):
            log_success("프론트엔드 시작 완료! (http://localhost:5173)")
            return process
        else:
            log_error("프론트엔드 시작 실패")
            process.terminate()
            return None
            
    except Exception as e:
        log_error(f"프론트엔드 시작 중 오류: {e}")
        return None

def monitor_services():
    """서비스 상태 모니터링"""
    log_info("📊 서비스 상태 모니터링 시작...")
    
    services = {
        "Simple Server Starter": 9998,
        "API Gateway": 8005,
        "User Service": 8006,
        "News Service": 8001,
        "Disclosure Service": 8002,
        "Chart Service": 8003,
        "Report Service": 8004,
        "Flow Analysis Service": 8010,
        "Frontend": 5173
    }
    
    while True:
        print("\n" + "="*60)
        print("📊 서비스 상태 모니터링")
        print("="*60)
        
        all_healthy = True
        
        for service_name, port in services.items():
            if check_port(port, timeout=3):
                print(f"✅ {service_name} (포트: {port}) - 정상")
            else:
                print(f"❌ {service_name} (포트: {port}) - 오류")
                all_healthy = False
        
        if all_healthy:
            print("\n🎉 모든 서비스가 정상적으로 실행 중입니다!")
            print("🌐 프론트엔드: http://localhost:5173")
            print("🔧 API Gateway: http://localhost:8005")
            print("📡 Server Starter: http://localhost:9998")
        else:
            print("\n⚠️ 일부 서비스에 문제가 있습니다.")
        
        print("\n⏰ 30초 후 다시 확인합니다... (Ctrl+C로 종료)")
        time.sleep(30)

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 HyperAssetLLM 완전한 시스템 실행")
    print("=" * 80)
    
    # 가상환경 확인
    if 'VIRTUAL_ENV' not in os.environ:
        log_error("가상환경이 활성화되지 않았습니다!")
        log_info("다음 명령어로 가상환경을 활성화하세요:")
        log_info("Windows: venv\\Scripts\\activate")
        log_info("Mac/Linux: source venv/bin/activate")
        sys.exit(1)
    
    log_success("가상환경 활성화 확인됨")
    
    # 1단계: 백엔드 서비스 시작
    if not start_backend_services():
        log_error("백엔드 서비스 시작 실패로 종료합니다.")
        sys.exit(1)
    
    # 2단계: 프론트엔드 시작
    frontend_process = start_frontend()
    if not frontend_process:
        log_error("프론트엔드 시작 실패로 종료합니다.")
        sys.exit(1)
    
    # 3단계: 서비스 모니터링
    try:
        monitor_services()
    except KeyboardInterrupt:
        log_info("사용자에 의해 종료되었습니다.")
    finally:
        # 정리 작업
        log_info("시스템 종료 중...")
        if frontend_process:
            frontend_process.terminate()
        log_success("시스템이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    main() 