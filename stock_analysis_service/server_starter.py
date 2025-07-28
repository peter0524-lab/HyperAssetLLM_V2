#!/usr/bin/env python3
"""
서버 시작용 HTTP 서버
- 포트 9999에서 실행
- /start-core 엔드포인트로 API Gateway와 User Service 시작
- 프론트엔드에서 호출 가능
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# CORS 설정 추가 - 프론트엔드에서 접근 허용
CORS(app, origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:5173"])
PROJECT_ROOT = Path(__file__).parent

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

def start_service(service_name, script_path, port, timeout=30):
    """개별 서비스 시작"""
    logger.info(f"🚀 {service_name} 시작 중...")
    
    # 이미 실행 중인지 확인
    if check_port(port, timeout=3):
        logger.info(f"✅ {service_name}는 이미 실행 중입니다")
        return True
    
    try:
        # 서비스 시작
        cmd = f"cd {PROJECT_ROOT} && nohup python3 {script_path} > logs/{service_name.lower().replace(' ', '_')}.log 2>&1 &"
        subprocess.run(cmd, shell=True, check=True)
        
        # 서비스 시작 대기
        if check_port(port, timeout):
            logger.info(f"✅ {service_name} 시작 완료 (포트: {port})")
            return True
        else:
            logger.error(f"❌ {service_name} 시작 실패 - 타임아웃")
            return False
            
    except Exception as e:
        logger.error(f"❌ {service_name} 시작 중 오류: {e}")
        return False

@app.route('/health')
def health():
    """헬스체크"""
    return jsonify({"status": "healthy", "service": "server_starter"})

@app.route('/start-core')
def start_core_services():
    """핵심 서비스 시작 (API Gateway, User Service)"""
    try:
        logger.info("🚀 핵심 서비스 시작 요청 받음")
        
        # logs 디렉토리 생성
        os.makedirs(PROJECT_ROOT / "logs", exist_ok=True)
        
        # User Service 시작
        user_service_success = start_service(
            "User Service",
            "services/user_service/user_service.py",
            8006,
            timeout=20
        )
        
        if not user_service_success:
            return jsonify({
                "success": False,
                "message": "User Service 시작 실패"
            }), 500
        
        # API Gateway 시작
        api_gateway_success = start_service(
            "API Gateway",
            "services/api_gateway/run.py",
            8005,
            timeout=20
        )
        
        if not api_gateway_success:
            return jsonify({
                "success": False,
                "message": "API Gateway 시작 실패"
            }), 500
        
        logger.info("✅ 모든 핵심 서비스 시작 완료")
        return jsonify({
            "success": True,
            "message": "핵심 서비스 시작 완료",
            "services": {
                "user_service": {"port": 8006, "status": "running"},
                "api_gateway": {"port": 8005, "status": "running"}
            }
        })
        
    except Exception as e:
        logger.error(f"❌ 핵심 서비스 시작 중 오류: {e}")
        return jsonify({
            "success": False,
            "message": f"서비스 시작 중 오류 발생: {str(e)}"
        }), 500

@app.route('/status')
def get_status():
    """서비스 상태 확인"""
    services = {
        "user_service": {"port": 8006, "running": check_port(8006, timeout=3)},
        "api_gateway": {"port": 8005, "running": check_port(8005, timeout=3)},
        "news_service": {"port": 8001, "running": check_port(8001, timeout=3)},
        "chart_service": {"port": 8003, "running": check_port(8003, timeout=3)},
        "orchestrator": {"port": 8000, "running": check_port(8000, timeout=3)}
    }
    
    return jsonify({
        "success": True,
        "services": services
    })

if __name__ == "__main__":
    logger.info("🚀 Server Starter 시작 (포트: 9999)")
    logger.info("📋 사용 가능한 엔드포인트:")
    logger.info("   - GET  /health      : 헬스체크")
    logger.info("   - GET  /start-core  : 핵심 서비스 시작")
    logger.info("   - GET  /status      : 서비스 상태 확인")
    
    app.run(host='0.0.0.0', port=9999, debug=False) 