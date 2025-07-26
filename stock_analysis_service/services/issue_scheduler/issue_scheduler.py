"""
Issue Scheduler Service Main Module
기업 이슈 일정 관리 서비스 - API 엔드포인트만 구현
"""

import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 공통 모듈 import
try:
    from shared.database.mysql_client import MySQLManager
    from shared.llm.llm_manager import LLMManager
    from shared.user_config.user_config_manager import UserConfigManager
except ImportError as e:
    print(f"Shared module import error: {e}")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/issue_scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Issue Scheduler Service",
    description="기업 이슈 일정 관리 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 매니저 인스턴스
mysql_manager = None
llm_manager = None
user_config_manager = None

class IssueSchedulerService:
    """이슈 스케줄러 서비스 클래스"""
    
    def __init__(self):
        self.mysql_manager = mysql_manager
        self.llm_manager = llm_manager
        self.user_config_manager = user_config_manager
        self.service_status = "ready"
        
    async def initialize(self):
        """서비스 초기화"""
        try:
            logger.info("Issue Scheduler Service 초기화 시작")
            self.service_status = "running"
            logger.info("Issue Scheduler Service 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"서비스 초기화 실패: {e}")
            self.service_status = "error"
            return False
    
    async def get_upcoming_issues(self, stock_codes: List[str], days_ahead: int = 30) -> Dict[str, Any]:
        """다가오는 기업 이슈 조회 (구현 예정)"""
        # TODO: FnGuide 캘린더 크롤링 구현
        return {
            "status": "success",
            "message": "다가오는 이슈 조회 기능 구현 예정",
            "stock_codes": stock_codes,
            "days_ahead": days_ahead,
            "issues": []
        }
    
    async def analyze_issue_importance(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """이슈 중요도 분석 (구현 예정)"""
        # TODO: LLM을 통한 이슈 중요도 분석 구현
        return {
            "status": "success",
            "message": "이슈 중요도 분석 기능 구현 예정",
            "issue": issue,
            "importance_score": 0.0
        }
    
    async def send_issue_alert(self, user_id: str, issue: Dict[str, Any]) -> Dict[str, Any]:
        """이슈 알림 전송 (구현 예정)"""
        # TODO: 텔레그램/푸시 알림 구현
        return {
            "status": "success",
            "message": "이슈 알림 전송 기능 구현 예정",
            "user_id": user_id,
            "issue": issue
        }

# 전역 서비스 인스턴스
issue_scheduler_service = IssueSchedulerService()

@app.on_event("startup")
async def startup_event():
    """서비스 시작 이벤트"""
    global mysql_manager, llm_manager, user_config_manager
    
    try:
        # 매니저 초기화
        mysql_manager = MySQLManager()
        llm_manager = LLMManager()
        user_config_manager = UserConfigManager(mysql_manager)
        
        # 서비스 초기화
        await issue_scheduler_service.initialize()
        logger.info("Issue Scheduler Service 시작 완료")
        
    except Exception as e:
        logger.error(f"서비스 시작 실패: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """서비스 종료 이벤트"""
    try:
        logger.info("Issue Scheduler Service 종료 중...")
        if mysql_manager:
            await mysql_manager.close()
        logger.info("Issue Scheduler Service 종료 완료")
    except Exception as e:
        logger.error(f"서비스 종료 중 오류: {e}")

# ===== API 엔드포인트 =====

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "Issue Scheduler Service",
        "version": "1.0.0",
        "status": issue_scheduler_service.service_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "issue_scheduler",
        "timestamp": datetime.now().isoformat(),
        "service_status": issue_scheduler_service.service_status,
        "version": "1.0.0"
    }

@app.post("/execute")
async def execute_issue_check(background_tasks: BackgroundTasks):
    """이슈 일정 확인 실행"""
    try:
        logger.info("이슈 일정 확인 실행 요청")
        
        # TODO: 실제 이슈 확인 로직 구현
        result = {
            "status": "success",
            "message": "이슈 일정 확인 완료",
            "timestamp": datetime.now().isoformat(),
            "issues_found": 0,
            "alerts_sent": 0
        }
        
        logger.info(f"이슈 일정 확인 완료: {result}")
        return result
        
    except Exception as e:
        logger.error(f"이슈 일정 확인 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/issues/upcoming")
async def get_upcoming_issues(stock_codes: str = None, days_ahead: int = 30):
    """다가오는 이슈 조회"""
    try:
        codes = stock_codes.split(',') if stock_codes else []
        result = await issue_scheduler_service.get_upcoming_issues(codes, days_ahead)
        return result
        
    except Exception as e:
        logger.error(f"다가오는 이슈 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/issues/analyze")
async def analyze_issue(issue_data: Dict[str, Any]):
    """이슈 중요도 분석"""
    try:
        result = await issue_scheduler_service.analyze_issue_importance(issue_data)
        return result
        
    except Exception as e:
        logger.error(f"이슈 중요도 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/send")
async def send_alert(user_id: str, issue_data: Dict[str, Any]):
    """이슈 알림 전송"""
    try:
        result = await issue_scheduler_service.send_issue_alert(user_id, issue_data)
        return result
        
    except Exception as e:
        logger.error(f"이슈 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/issues/calendar/{stock_code}")
async def get_stock_calendar(stock_code: str):
    """특정 종목의 이슈 캘린더 조회"""
    try:
        # TODO: 종목별 이슈 캘린더 구현
        return {
            "status": "success",
            "stock_code": stock_code,
            "calendar": [],
            "message": "종목별 이슈 캘린더 기능 구현 예정"
        }
        
    except Exception as e:
        logger.error(f"종목별 이슈 캘린더 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-user/{user_id}")
async def set_user_config(user_id: str, config_data: Dict[str, Any]):
    """사용자 설정"""
    try:
        logger.info(f"사용자 설정 요청: {user_id}")
        
        # TODO: 사용자별 이슈 알림 설정 구현
        result = {
            "status": "success",
            "message": "사용자 설정 완료",
            "user_id": user_id,
            "config": config_data
        }
        
        return result
        
    except Exception as e:
        logger.error(f"사용자 설정 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user-config/{user_id}")
async def get_user_config(user_id: str):
    """사용자 설정 조회"""
    try:
        # TODO: 사용자 설정 조회 구현
        return {
            "status": "success",
            "user_id": user_id,
            "config": {},
            "message": "사용자 설정 조회 기능 구현 예정"
        }
        
    except Exception as e:
        logger.error(f"사용자 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check-schedule")
async def check_schedule():
    """스케줄 확인"""
    try:
        return {
            "status": "success",
            "next_run": (datetime.now() + timedelta(hours=1)).isoformat(),
            "message": "스케줄 확인 기능 구현 예정"
        }
        
    except Exception as e:
        logger.error(f"스케줄 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_server():
    """서버 실행"""
    uvicorn.run(
        "issue_scheduler:app",
        host="0.0.0.0",
        port=8007,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    run_server() 