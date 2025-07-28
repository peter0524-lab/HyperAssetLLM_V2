#!/usr/bin/env python3
"""
간단한 서버 시작용 HTTP 서버
- 포트 9998에서 실행
- /start-servers 엔드포인트로 모든 서버 시작
- 브라우저에서 직접 호출 가능
"""

import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent

class ServerStarterHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS 프리플라이트 요청 처리"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """POST 요청 처리"""
        if self.path == '/start-servers':
            self.start_all_servers()
        else:
            self.send_error(404, "Not Found")

    def do_GET(self):
        """GET 요청 처리"""
        if self.path == '/health':
            self.send_health_check()
        else:
            self.send_error(404, "Not Found")

    def send_health_check(self):
        """헬스체크 응답"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "service": "simple_server_starter",
            "status": "healthy",
            "message": "서버 시작 서비스 준비됨"
        }
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

    def start_all_servers(self):
        """모든 서버를 시작하는 함수"""
        try:
            logger.info("🚀 서버 시작 프로세스 시작")
            
            # 응답 먼저 보내기
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "success": True,
                "message": "서버 시작 중...",
                "status": "starting"
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
            # 백그라운드에서 서버 시작
            threading.Thread(target=self._start_servers_background, daemon=True).start()
            
        except Exception as e:
            logger.error(f"서버 시작 에러: {e}")
            self.send_error(500, f"Server Start Error: {str(e)}")

    def _start_servers_background(self):
        """백그라운드에서 서버들을 시작"""
        try:
            logger.info("📡 Server Starter 시작 중...")
            self._start_server_starter()
            
            time.sleep(3)  # Server Starter가 완전히 시작될 때까지 대기
            
            logger.info("🌐 API Gateway 시작 중...")
            self._start_api_gateway()
            
            time.sleep(2)  # API Gateway가 시작될 때까지 대기
            
            logger.info("👤 User Service 시작 중...")
            self._start_user_service()
            
            logger.info("✅ 모든 서버 시작 완료!")
            
        except Exception as e:
            logger.error(f"백그라운드 서버 시작 에러: {e}")

    def _start_server_starter(self):
        """Server Starter 시작"""
        cmd = [
            sys.executable, 
            str(PROJECT_ROOT / "server_starter.py")
        ]
        
        subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info("📡 Server Starter 시작됨")

    def _start_api_gateway(self):
        """API Gateway 시작"""
        cmd = [
            sys.executable, 
            str(PROJECT_ROOT / "services" / "api_gateway" / "run.py")
        ]
        
        subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT / "services" / "api_gateway",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info("🌐 API Gateway 시작됨")

    def _start_user_service(self):
        """User Service 시작"""
        cmd = [
            sys.executable, 
            str(PROJECT_ROOT / "services" / "user_service" / "user_service.py")
        ]
        
        subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT / "services" / "user_service",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info("👤 User Service 시작됨")

def run_server(port=9998):
    """HTTP 서버 실행"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ServerStarterHandler)
    
    logger.info(f"🚀 Simple Server Starter 시작 - 포트 {port}")
    logger.info(f"📡 서버 시작: POST http://localhost:{port}/start-servers")
    logger.info(f"🔍 헬스체크: GET http://localhost:{port}/health")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 서버 종료")
        httpd.shutdown()

if __name__ == "__main__":
    run_server() 