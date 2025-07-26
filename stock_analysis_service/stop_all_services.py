#!/usr/bin/env python3
"""
모든 서비스 한 번에 종료하는 스크립트
- 실행 중인 모든 서비스 프로세스 종료
- 포트별로 프로세스 찾아서 정리
- 안전한 종료 순서 적용
"""

import subprocess
import time
import sys
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

def kill_processes_by_port(port):
    """특정 포트를 사용하는 프로세스들 종료"""
    try:
        # lsof 명령으로 포트 사용 프로세스 찾기
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    # 정상 종료 신호 보내기 (SIGTERM)
                    subprocess.run(['kill', '-15', pid], check=True)
                    log_info(f"포트 {port} 프로세스 종료 신호 전송 (PID: {pid})")
                    time.sleep(2)
                    
                    # 프로세스가 아직 살아있는지 확인
                    try:
                        subprocess.run(['kill', '-0', pid], check=True)
                        # 아직 살아있으면 강제 종료
                        subprocess.run(['kill', '-9', pid], check=True)
                        log_warning(f"포트 {port} 프로세스 강제 종료 (PID: {pid})")
                    except subprocess.CalledProcessError:
                        # 프로세스가 이미 종료됨
                        log_success(f"포트 {port} 프로세스 정상 종료됨 (PID: {pid})")
                        
                except subprocess.CalledProcessError:
                    log_warning(f"프로세스 종료 실패 (PID: {pid})")
            return True
        else:
            log_info(f"포트 {port}에서 실행 중인 프로세스가 없습니다")
            return False
            
    except Exception as e:
        log_error(f"포트 {port} 프로세스 종료 중 오류: {e}")
        return False

def kill_processes_by_name(process_names):
    """프로세스 이름으로 종료"""
    for process_name in process_names:
        try:
            result = subprocess.run(
                ['pgrep', '-f', process_name],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        subprocess.run(['kill', '-15', pid], check=True)
                        log_info(f"{process_name} 프로세스 종료 신호 전송 (PID: {pid})")
                        time.sleep(1)
                        
                        # 강제 종료 확인
                        try:
                            subprocess.run(['kill', '-0', pid], check=True)
                            subprocess.run(['kill', '-9', pid], check=True)
                            log_warning(f"{process_name} 프로세스 강제 종료 (PID: {pid})")
                        except subprocess.CalledProcessError:
                            log_success(f"{process_name} 프로세스 정상 종료됨 (PID: {pid})")
                            
                    except subprocess.CalledProcessError:
                        log_warning(f"프로세스 종료 실패 (PID: {pid})")
        except Exception as e:
            log_error(f"{process_name} 프로세스 찾기 실패: {e}")

def cleanup_log_files():
    """로그 파일 정리 옵션"""
    log_files = list(PROJECT_ROOT.glob("*.log"))
    
    if log_files:
        log_info(f"발견된 로그 파일: {len(log_files)}개")
        
        response = input("로그 파일들을 삭제하시겠습니까? (y/N): ").strip().lower()
        
        if response == 'y':
            for log_file in log_files:
                try:
                    log_file.unlink()
                    log_success(f"로그 파일 삭제: {log_file.name}")
                except Exception as e:
                    log_error(f"로그 파일 삭제 실패 {log_file.name}: {e}")
        else:
            log_info("로그 파일을 보존합니다")
    else:
        log_info("삭제할 로그 파일이 없습니다")

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🛑 주식 분석 시스템 - 모든 서비스 종료")
    print("=" * 80)
    
    # 서비스 포트 목록
    service_ports = {
        8001: "News Service",
        8002: "Disclosure Service", 
        8003: "Chart Service",
        8004: "Report Service",
        8005: "API Gateway",
        8006: "User Service",
        8010: "Flow Analysis Service"
    }
    
    # 1. 포트별로 프로세스 종료
    log_info("포트별 서비스 프로세스 종료 중...")
    terminated_services = []
    
    for port, service_name in service_ports.items():
        log_info(f"{service_name} (포트 {port}) 종료 중...")
        if kill_processes_by_port(port):
            terminated_services.append(service_name)
        print("-" * 40)
    
    # 2. 스케줄러 및 기타 프로세스 종료
    log_info("스케줄러 및 관련 프로세스 종료 중...")
    scheduler_processes = [
        "scheduler.py",
        "orchestrator",
        "main.py"
    ]
    
    kill_processes_by_name(scheduler_processes)
    
    # 3. 추가 정리 - Python 프로세스 중 서비스 관련 것들
    log_info("남은 서비스 관련 프로세스 정리 중...")
    service_processes = [
        "news_service",
        "disclosure_service", 
        "chart_service",
        "report_service",
        "flow_analysis_service",
        "user_service",
        "api_gateway"
    ]
    
    kill_processes_by_name(service_processes)
    
    # 4. 최종 확인
    time.sleep(2)
    log_info("최종 확인 중...")
    
    still_running = []
    for port, service_name in service_ports.items():
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            still_running.append(f"{service_name} (포트 {port})")
    
    # 결과 출력
    print("=" * 80)
    print("🎯 종료 결과")
    print("=" * 80)
    
    if terminated_services:
        log_success(f"종료된 서비스: {len(terminated_services)}개")
        for service in terminated_services:
            print(f"   ✅ {service}")
    
    if still_running:
        log_warning("아직 실행 중인 서비스:")
        for service in still_running:
            print(f"   ⚠️ {service}")
        log_info("수동으로 종료하거나 시스템 재부팅을 고려하세요")
    else:
        log_success("모든 서비스가 성공적으로 종료되었습니다!")
    
    # 5. 로그 파일 정리 옵션
    print("\n" + "=" * 80)
    cleanup_log_files()
    
    print("\n🔧 유용한 명령어들:")
    print("   모든 서비스 시작: python start_all_services.py")
    print("   서비스 상태 확인: python test_api_gateway.py")
    print("   실행 중인 프로세스 확인: ps aux | grep python")

if __name__ == "__main__":
    main() 