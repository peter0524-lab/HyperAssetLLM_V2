"""
사업보고서 서비스 (Business Report Service)
- DART API를 통한 사업보고서 정보 수집
- LLM 기반 사업보고서 요약 및 분석
- 유사 과거 사례 검색 (구현 예정)
- 주가 영향 예측 (구현 예정)
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import sys
import os
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.llm.llm_manager import llm_manager
from shared.apis.dart_api import DARTAPIClient
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config
from shared.user_config.user_config_manager import user_config_manager
from shared.service_config.user_config_loader import get_config_loader

# FastAPI 추가
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
import uvicorn

logger = logging.getLogger(__name__)

app = FastAPI(title="Business Report Service", version="1.0.0")

class BusinessReportService:
    """사업보고서 서비스 클래스"""

    def __init__(self):
        self.config = get_config()
        self.user_config_manager = user_config_manager
        self.current_user_id = os.environ.get('HYPERASSET_USER_ID', "1")
        self.stocks_config = {} # 사용자별 종목 설정 (MySQL에서 덮어쓰기)
        
        self.user_config_loader = None
        self.personalized_configs = {}
        
        self.mysql_client = get_mysql_client()
        self.llm_manager = llm_manager
        self.dart_client = DARTAPIClient()
        self.telegram_bot = TelegramBotClient()
        
        asyncio.create_task(self._load_user_settings())

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    async def _load_user_settings(self):
        """사용자별 설정 로드 (User Config Manager에서 중앙 집중식으로 가져오기)"""
        try:
            user_config = await self.user_config_manager.get_user_config(self.current_user_id)
            
            self.stocks_config = {}
            for stock in user_config.get("stocks", []):
                if stock.get("enabled", True):
                    self.stocks_config[stock["stock_code"]] = {
                        "name": stock["stock_name"],
                        "enabled": True
                    }
            
            self.logger.info(f"✅ 사용자 종목 설정 로드 완료: {len(self.stocks_config)}개 종목")
            
        except Exception as e:
            self.logger.error(f"❌ 사용자 설정 로드 실패 (기본값 유지): {e}")
            self.stocks_config = {
                "006800": {"name": "미래에셋증권", "enabled": True}
            }
    
    async def set_user_id(self, user_id):
        """사용자 ID 설정 및 설정 재로드"""
        try:
            self.current_user_id = user_id
            await self._load_user_settings()
            self.logger.info(f"✅ 사용자 ID 설정 및 설정 재로드 완료: {user_id}")
        except Exception as e:
            self.logger.error(f"❌ 사용자 ID 설정 실패: {e}")
            raise

    async def fetch_business_report_data(self, stock_code: str) :
        """사업보고서 데이터 가져오기 (구현 예정)"""
        self.logger.info(f"사업보고서 데이터 조회 시작: {stock_code}")
        rcept_no = self.dart_client.get_business(stock_code)
        
        if rcept_no:
            print(f"가장 최신 사업보고서의 rcept_no: {rcept_no}")
            
            # 2. rcept_no를 사용하여 '사업의 개요' 텍스트 가져오기
            business_overview_text = await self.dart_client.get_business_detail(rcept_no)
        else:
            print("최신 사업보고서를 찾을 수 없습니다.")
            
        return business_overview_text
        
        
    async def send_business_report_notification(self, report_txt: str, analysis: Dict):
        """사업보고서 알림 전송 (analysis: Dict, report_txt: str)"""
        try:
            analysis_text = analysis.get('analysis', '분석 내용 없음').strip()

            message = (
                "📢 <b>[AI 사업보고서 분석 알림]</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔍 <b>AI 분석 요약</b>\n"
                f"<i>{analysis_text}</i>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "📄 <b>보고서 내용 발췌</b>\n"
                "<pre><code>"
                f"{report_txt[:200].strip()}..."  # 보고서 일부 (최대 500자)
                "</code></pre>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ <i>본 분석은 AI에 의해 자동 생성되었으며,\n"
                "투자 판단의 참고 자료로만 활용하시기 바랍니다.</i>"
            )

            await self.telegram_bot.send_message_async(message)
            await save_latest_signal(message)
            self.logger.info("✅ 사업보고서 알림 전송 완료")

        except Exception as e:
            self.logger.error(f"❌ 사업보고서 알림 전송 실패: {analysis}")

    def _create_business_report_analysis_prompt(self, report_content: str, stock_name: str) -> str:
        """사업보고서 분석 프롬프트 생성"""
        return f"""
            당신은 기업 보고서의 분석 전문가입니다. 다음 {stock_name} 기업의 사업보고서 내용을 최대한 자세히 투자 관점에서 중요한 정보를 분석해주세요.

            사업보고서 내용:
            {report_content}

           
            다음 JSON 형식으로 **정확하게 JSON 객체 하나만** 출력하세요. 그 외 문장은 포함하지 마세요:

            {{
                "analysis":""
            }}
        """

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """LLM 응답 텍스트를 파싱하여 표준 JSON 객체로 변환합니다."""
        def get_partial_key_value(d: dict, keyword: str):
            for k, v in d.items():
                if keyword in k:
                    return v
            return None

        if not response_text:
            self.logger.error("❌ LLM 응답이 비어 있습니다.")
            return self._get_default_analysis_result("LLM 응답 없음")

        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON 파싱실패: {e}. 기본값 반환.")
            return self._get_default_analysis_result(f"JSON 파싱 오류: {e}")

        return {
            "analysis": get_partial_key_value(parsed_json, "analysis") or "",
        }

    def _get_default_analysis_result(self, reason: str) -> Dict:
        """기본 분석 결과 반환"""
        return {
            "analysis": "사업보고서 분석 실패",
        }
    
    async def analyze_business_report(self, report_txt: Dict, stock_name: str) -> Dict:
        """사업보고서 내용 LLM 분석"""
        try:
            prompt = self._create_business_report_analysis_prompt(report_txt, stock_name)
            analysis_response = await self.llm_manager.generate_response(self.current_user_id, prompt)
            if not analysis_response:
                self.logger.error("❌ LLM 응답이 없습니다")
                return self._get_default_analysis_result("LLM 응답 없음")
            
            analysis_result = self._parse_llm_response(analysis_response)
            
            self.logger.info(f"✅ 사업보고서 LLM 분석 완료: {stock_name}")
            return analysis_result

        except Exception as e:
            self.logger.error(f"❌ 사업보고서 LLM 분석 중 오류 발생: {e}")
            return self._get_default_analysis_result(f"분석 오류: {str(e)}")
        
    async def get_stock_name(self, stock_code: str) -> str:
        """종목 코드로 종목명 조회 (없으면 '미래에셋증권' 반환)"""
        # TODO: 실제 종목명 조회 로직 구현 (예: DB 또는 외부 API)
        return self.stocks_config.get(stock_code, {}).get("name", "미래에셋증권")
        
    async def process_business_report_pipeline(self, stock_code: str) -> None:
        """사업보고서 처리 파이프라인 실행"""
        if not stock_code:
            self.logger.warning("stock_code가 제공되지 않았습니다. 기본값 '006800'으로 설정합니다.")
            stock_code = "006800"
        try:
            report_txt = await self.fetch_business_report_data(stock_code)
            if not report_txt:
                self.logger.info(f"사업보고서 데이터 없음: {stock_code}")
                return

            
            stock_name = await self.get_stock_name(stock_code)
            llm_analysis = await self.analyze_business_report(report_txt, stock_name)
            #llm 분석
                    
            await self.send_business_report_notification(
                report_txt=report_txt,
                analysis=llm_analysis
            )
                    
  

        except Exception as e:
            self.logger.error(f"사업보고서 파이프라인 실행 중 오류 발생: {stock_code}, 오류: {e}")
        
    async def run_service(self):
        """사업보고서 서비스 실행"""
        try:
            self.logger.info("사업보고서 서비스 시작")

            # 사용자 설정에서 종목 정보 로드
            # self.stocks_config는 _load_user_settings에서 이미 로드됨

            while True:
                try:
                    for stock_code in self.stocks_config.keys():
                        await self.process_business_report_pipeline(stock_code)
                    
                    await asyncio.sleep(3600)  # 1시간 대기
                
                except Exception as e:
                    self.logger.error(f"사업보고서 처리 중 오류 발생: {e}")
                    await asyncio.sleep(300)

        except Exception as e:
            self.logger.error(f"사업보고서 서비스 실행 실패: {e}")
            raise
        finally:
            self.mysql_client.close()

business_report_service_instance = None
latest_signal_message = None

def get_business_report_service():
    global business_report_service_instance
    if business_report_service_instance is None:
        business_report_service_instance = BusinessReportService()
    return business_report_service_instance

last_execution_time = None

async def save_latest_signal(message: str):
    global latest_signal_message
    latest_signal_message = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "service": "business_report"
    }

def should_execute_now() -> tuple[bool, str]:
    global last_execution_time
    
    now = datetime.now()
    
    if last_execution_time is None:
        return True, "첫 실행"
    
    time_diff = (now - last_execution_time).total_seconds()
    required_interval = 3600  # 1시간
    
    if time_diff >= required_interval:
        return True, f"1시간 간격 - 마지막 실행: {last_execution_time.strftime('%H:%M')}"
    else:
        remaining = int(required_interval - time_diff)
        remaining_minutes = remaining // 60
        return False, f"1시간 간격 - {remaining_minutes}분 후 실행 가능"

async def execute_business_report_analysis() -> Dict:
    global last_execution_time
    global latest_signal_message
    
    try:
        logger.info("🚀 사업보고서 분석 실행 시작")
        
        service = get_business_report_service()
        if service is None:
            logger.error("❌ 사업보고서 서비스 인스턴스가 초기화되지 않음")
            return {"success": False, "error": "서비스 인스턴스 없음"}
        
        processed_stocks = []
        
        # 사용자 설정에서 활성화된 종목만 처리
        for stock_code in service.stocks_config.keys():
            try:
                logger.info(f"📋 {stock_code} 사업보고서 분석 시작")
                await service.process_business_report_pipeline(stock_code)
                processed_stocks.append(stock_code)
                logger.info(f"✅ {stock_code} 사업보고서 분석 완료")
                
            except Exception as e:
                logger.error(f"❌ {stock_code} 사업보고서 분석 실패: {e}")
                continue
        
        last_execution_time = datetime.now()
        
        result = {
            "success": True,
            "processed_stocks": len(processed_stocks),
            "execution_time": last_execution_time.isoformat(),
            "telegram_message": latest_signal_message.get("message") if latest_signal_message else None
        }
        
        logger.info(f"✅ 사업보고서 분석 완료: {len(processed_stocks)}개 종목")
        return result
        
    except Exception as e:
        logger.error(f"❌ 사업보고서 분석 실행 실패: {e}")
        return {"success": False, "error": str(e), "telegram_message": None}

# FastAPI 엔드포인트
@app.post("/set-user/{user_id}")
async def set_user_id_endpoint(user_id: str):
    try:
        service = get_business_report_service()
        await service.set_user_id(user_id)
        return {
            "success": True,
            "message": f"사용자 ID 설정 완료: {user_id}",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"❌ 사용자 ID 설정 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 ID 설정에 실패했습니다")

@app.get("/user-config/{user_id}")
async def get_user_config_endpoint(user_id: str):
    try:
        service = get_business_report_service()
        await service.set_user_id(user_id)
        
        user_config = await service.user_config_manager.get_user_config(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "config": {
                "stocks": user_config.get("stocks", [])
            }
        }
    except Exception as e:
        logger.error(f"❌ 사용자 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 설정 조회에 실패했습니다")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/signal")
async def get_latest_signal():
    global latest_signal_message
    if latest_signal_message:
        return latest_signal_message
    else:
        return {
            "message": "아직 알람이 발생하지 않았습니다.",
            "timestamp": datetime.now().isoformat(),
            "service": "business_report"
        }

@app.post("/execute")
async def execute_business_report_analysis_endpoint(request: Request):
    try:
        print("="*50)
        print("BUSINESS REPORT LOG: 최종 목적지 도착!")
        print("BUSINESS REPORT LOG: 게이트웨이로부터 /execute 요청을 성공적으로 받았습니다.")
        print(f"BUSINESS REPORT LOG: 요청 헤더: {request.headers}")
        print("BUSINESS REPORT LOG: 지금부터 실제 사업보고서 분석을 시작합니다...")
        print("="*50)

        user_id = request.headers.get("X-User-ID", "1")
        
        service = get_business_report_service()
        if service.current_user_id != user_id:
            await service.set_user_id(user_id)
            logger.info(f" 사용자 컨텍스트 변경: {user_id}")
        
        result = await execute_business_report_analysis()
        
        print("="*50)
        print("BUSINESS REPORT LOG: 분석 완료! 결과를 게이트웨이로 반환합니다.")
        print(f"BUSINESS REPORT LOG: 반환 결과: {result}")
        print("="*50)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 사업보고서 분석 실행 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/check-schedule")
async def check_schedule():
    try:
        should_run, reason = should_execute_now()
        
        if should_run:
            result = await execute_business_report_analysis()
            
            if result["success"]:
                return {
                    "executed": True,
                    "message": f"사업보고서 분석 실행 완료 - {reason}",
                    "details": result
                }
            else:
                return {
                    "executed": False,
                    "message": f"사업보고서 분석 실행 실패 - {result.get('error', 'Unknown')}",
                    "reason": reason
                }
        else:
            return {
                "executed": False,
                "message": reason,
                "next_execution": "1시간 간격"
            }
            
    except Exception as e:
        logger.error(f"❌ 스케줄 체크 실패: {e}")
        return {
            "executed": False,
            "message": f"스케줄 체크 오류: {str(e)}"
        }

def main():
    try:
        logger.info("🚀 사업보고서 서비스 시작 (포트: 8008)")
        uvicorn.run(app, host="0.0.0.0", port=8008)

    except KeyboardInterrupt:
        print("서비스 중단")
    except Exception as e:
        print(f"서비스 실행 실패: {e}")

async def test_process_business_report_pipeline_function():
    """
    business_report_service.py의 process_business_report_pipeline 함수를 테스트하기 위한 함수입니다.
    """
    print("--- Business Report Service 파이프라인 테스트 시작 ---")
    try:
        # BusinessReportService 인스턴스 생성
        service = BusinessReportService()
        
        # 테스트할 종목 코드 설정 (예: 삼성전자)
        test_stock_code = "006800" 
        print(f"테스트 대상 종목: {test_stock_code}")

        # 파이프라인 실행
        await service.process_business_report_pipeline(test_stock_code)

        print("--- 테스트가 성공적으로 완료되었습니다. ---")

    except Exception as e:
        print(f"--- 테스트 중 오류 발생: {e} ---")
    finally:
        # 리소스 정리 (필요한 경우)
        if 'service' in locals() and hasattr(service, 'mysql_client'):
            service.mysql_client.close()
        print("--- Business Report Service 파이프라인 테스트 종료 ---")


if __name__ == "__main__":
    # --- test_process_business_report_pipeline_function 테스트를 원할 경우 아래 코드의 주석을 해제하세요 ---
    asyncio.run(test_process_business_report_pipeline_function())

    # --- 원래 서버를 실행하려면 아래 코드의 주석을 해제하고 위 코드를 주석 처리하세요 ---
    #main()