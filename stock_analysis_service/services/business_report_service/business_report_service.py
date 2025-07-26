"""
Business Report Service Main Module
기업 사업보고서 AI 요약 서비스 - API 엔드포인트만 구현
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
    from shared.apis.dart_api import DartAPI
except ImportError as e:
    print(f"Shared module import error: {e}")
    sys.exit(1)

# 로깅 설정  
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/business_report_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Business Report Service",
    description="기업 사업보고서 AI 요약 서비스",
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
dart_api = None

class BusinessReportService:
    """사업보고서 요약 서비스 클래스"""
    
    def __init__(self):
        self.mysql_manager = mysql_manager
        self.llm_manager = llm_manager
        self.user_config_manager = user_config_manager
        self.dart_api = dart_api
        self.service_status = "ready"
        
    async def initialize(self):
        """서비스 초기화"""
        try:
            logger.info("Business Report Service 초기화 시작")
            self.service_status = "running"
            logger.info("Business Report Service 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"서비스 초기화 실패: {e}")
            self.service_status = "error"
            return False
    
    async def get_business_report(self, stock_code: str, report_type: str = "annual") -> Dict[str, Any]:
        """사업보고서 수집 (구현 예정)"""
        # TODO: DART API를 통한 사업보고서 수집 구현
        return {
            "status": "success",
            "message": "사업보고서 수집 기능 구현 예정",
            "stock_code": stock_code,
            "report_type": report_type,
            "report_data": {}
        }
    
    async def summarize_report(self, stock_code: str, report_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """사업보고서 투자 관점 요약 (구현 예정)"""
        # TODO: LLM을 통한 투자 관점 특화 요약 구현
        return {
            "status": "success",
            "message": "사업보고서 요약 기능 구현 예정",
            "stock_code": stock_code,
            "summary": {
                "major_clients": "주요 고객사 및 계약 정보 구현 예정",
                "new_business": "신규 사업 및 투자 정보 구현 예정",
                "risk_factors": "리스크 요인 분석 구현 예정",
                "future_plans": "향후 계획 및 실적 전망 구현 예정"
            },
            "user_id": user_id
        }
    
    async def generate_report_pdf(self, stock_code: str, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """사업보고서 요약 PDF 생성 (구현 예정)"""
        # TODO: PDF 생성 기능 구현
        return {
            "status": "success",
            "message": "PDF 생성 기능 구현 예정",
            "stock_code": stock_code,
            "pdf_path": f"/reports/{stock_code}_business_report.pdf"
        }
    
    async def get_report_history(self, user_id: str) -> Dict[str, Any]:
        """사용자의 사업보고서 요약 히스토리 조회 (구현 예정)"""
        # TODO: 사업보고서 요약 히스토리 구현
        return {
            "status": "success",
            "message": "사업보고서 히스토리 조회 기능 구현 예정",
            "user_id": user_id,
            "history": []
        }

# 전역 서비스 인스턴스
business_report_service = BusinessReportService()

@app.on_event("startup")
async def startup_event():
    """서비스 시작 이벤트"""
    global mysql_manager, llm_manager, user_config_manager, dart_api
    
    try:
        # 매니저 초기화
        mysql_manager = MySQLManager()
        llm_manager = LLMManager()
        user_config_manager = UserConfigManager(mysql_manager)
        dart_api = DartAPI()
        
        # 서비스 초기화
        await business_report_service.initialize()
        logger.info("Business Report Service 시작 완료")
        
    except Exception as e:
        logger.error(f"서비스 시작 실패: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """서비스 종료 이벤트"""
    try:
        logger.info("Business Report Service 종료 중...")
        if mysql_manager:
            await mysql_manager.close()
        logger.info("Business Report Service 종료 완료")
    except Exception as e:
        logger.error(f"서비스 종료 중 오류: {e}")

# ===== API 엔드포인트 =====

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "Business Report Service",
        "version": "1.0.0",
        "status": business_report_service.service_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "business_report",
        "timestamp": datetime.now().isoformat(),
        "service_status": business_report_service.service_status,
        "version": "1.0.0"
    }

@app.post("/execute")
async def execute_report_analysis(background_tasks: BackgroundTasks):
    """사업보고서 분석 실행"""
    try:
        logger.info("사업보고서 분석 실행 요청")
        
        # TODO: 실제 사업보고서 분석 로직 구현
        result = {
            "status": "success",
            "message": "사업보고서 분석 완료",
            "timestamp": datetime.now().isoformat(),
            "reports_analyzed": 0,
            "summaries_generated": 0
        }
        
        logger.info(f"사업보고서 분석 완료: {result}")
        return result
        
    except Exception as e:
        logger.error(f"사업보고서 분석 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reports/summarize/{stock_code}")
async def summarize_business_report(stock_code: str, user_id: str = None, report_type: str = "annual"):
    """특정 종목의 사업보고서 요약"""
    try:
        logger.info(f"사업보고서 요약 요청: {stock_code}")
        
        # 사업보고서 수집
        report_data = await business_report_service.get_business_report(stock_code, report_type)
        
        # 요약 생성
        summary = await business_report_service.summarize_report(stock_code, report_data, user_id)
        
        return summary
        
    except Exception as e:
        logger.error(f"사업보고서 요약 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/{stock_code}")
async def get_report(stock_code: str, report_type: str = "annual"):
    """사업보고서 원본 조회"""
    try:
        result = await business_report_service.get_business_report(stock_code, report_type)
        return result
        
    except Exception as e:
        logger.error(f"사업보고서 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reports/pdf/{stock_code}")
async def generate_pdf_report(stock_code: str, summary_data: Dict[str, Any]):
    """사업보고서 요약 PDF 생성"""
    try:
        result = await business_report_service.generate_report_pdf(stock_code, summary_data)
        return result
        
    except Exception as e:
        logger.error(f"PDF 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/history/{user_id}")
async def get_report_history(user_id: str):
    """사용자의 사업보고서 요약 히스토리"""
    try:
        result = await business_report_service.get_report_history(user_id)
        return result
        
    except Exception as e:
        logger.error(f"히스토리 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/available/{stock_code}")
async def get_available_reports(stock_code: str):
    """특정 종목의 사용 가능한 사업보고서 목록"""
    try:
        # TODO: 사용 가능한 보고서 목록 조회 구현
        return {
            "status": "success",
            "stock_code": stock_code,
            "available_reports": [],
            "message": "사용 가능한 보고서 목록 조회 기능 구현 예정"
        }
        
    except Exception as e:
        logger.error(f"사용 가능한 보고서 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-user/{user_id}")
async def set_user_config(user_id: str, config_data: Dict[str, Any]):
    """사용자 설정"""
    try:
        logger.info(f"사용자 설정 요청: {user_id}")
        
        # TODO: 사용자별 사업보고서 설정 구현
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
            "next_run": (datetime.now() + timedelta(hours=24)).isoformat(),
            "message": "스케줄 확인 기능 구현 예정"
        }
        
    except Exception as e:
        logger.error(f"스케줄 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_server():
    """서버 실행"""
    uvicorn.run(
        "business_report_service:app",
        host="0.0.0.0",
        port=8008,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    run_server() 