"""
공시 서비스 (Disclosure Service)
- DART API를 통한 공시 정보 수집
- 키워드 기반 필터링
- LLM 기반 공시 요약 및 분석
- 유사 과거 사례 검색
- 주가 영향 예측
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
# from services.disclosure_service.gemini_analyzer import GeminiDisclosureAnalyzer  # 더 이상 사용하지 않음
from services.chart_service.chart_service import ChartAnalysisService
from shared.database.mysql_client import get_mysql_client
#from shared.database.vector_db import VectorDBClient
from shared.llm.llm_manager import llm_manager
from shared.apis.dart_api import DARTAPIClient
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config
from shared.user_config.user_config_manager import user_config_manager
from shared.service_config.user_config_loader import get_config_loader

# FastAPI 추가
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
import uvicorn

# 주가 데이터 조회용
import yfinance as yf


logger = logging.getLogger(__name__)


app = FastAPI(title="Disclosure Service", version="1.0.0")

class DisclosureService:
    """공시 서비스 클래스"""

    def __init__(self):
        # 개발자 기본 설정 로드
        self.config = get_config()
        
        # 사용자 설정 관리자 초기화
        self.user_config_manager = user_config_manager
        self.current_user_id = os.environ.get('HYPERASSET_USER_ID', "1")  # 🔥 환경변수에서 사용자 ID 읽기
        self.stocks_config = {}  # 사용자별 종목 설정 (MySQL에서 덮어쓰기)
        
        # 사용자별 개인화 설정 로더
        self.user_config_loader = None  # 비동기로 초기화됨
        self.personalized_configs = {}  # 사용자별 개인화 설정 캐시
        
        self.mysql_client = get_mysql_client()
        #self.vector_db = VectorDBClient()
        self.llm_manager = llm_manager
        self.dart_client = DARTAPIClient()
        self.telegram_bot = TelegramBotClient()
        self.chart_service = ChartAnalysisService()
        
        # 사용자별 설정 로드 (MySQL에서 stock_code만 덮어쓰기)
        asyncio.create_task(self._load_user_settings())

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    async def _load_user_settings(self):
        """사용자별 설정 로드 (User Config Manager에서 중앙 집중식으로 가져오기)"""
        try:
            user_config = await self.user_config_manager.get_user_config(self.current_user_id)
            
            # 사용자 종목 설정으로 덮어쓰기
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
            # 실패시 기본 종목 설정
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

    async def check_processed_disclosure(self, rcept_no: str) -> bool:
        """공시가 이미 DB에 존재하는지 여부만 확인"""
        try:
            query = "SELECT 1 FROM disclosure_history WHERE rcept_no = %s LIMIT 1"
            result = await self.mysql_client.fetch_one_async(query, (rcept_no,))
            return result is not None #None이면 False, 있으면 True
        except Exception as e:
            self.logger.error(f"공시 처리 여부 확인 실패: {e}")
            return False

    async def fetch_disclosure_data(self, stock_code: str, days: int = 7) -> List[Dict]:
        """공시 데이터 가져오기"""
        try:
            self.logger.info(f"공시 데이터 조회 시작: {stock_code}")
            
            # DART API를 통해 공시 데이터 가져오기
            disclosures = self.dart_client.get_recent_disclosures_test(stock_code)
            #disclosures = self.dart_client.get_recent_disclosures(stock_code, days) #키워드 체크, 정정 체크, 중복체크 완료 해서 딕셔너리 리스트로 반환
            
            if not disclosures:
                self.logger.info(f"공시 데이터 없음: {stock_code}")
                return []
            
            self.logger.info(f"공시 데이터 조회 완료: {stock_code}, {len(disclosures)}건")
            return disclosures
            
        except Exception as e:
            self.logger.error(f"공시 데이터 조회 중 오류 발생: {e}")
            return []


    async def find_similar_cases_from_mysql(self, disclosure: Dict) -> Optional[Dict]:
        """
        현재 disclosure보다 5일 이전이고 report_nm이 동일한 가장 최근 공시 1건을 MySQL에서 조회
        """
        try:
            report_nm = disclosure.get("report_nm")
            rcept_dt_str = disclosure.get("rcept_dt")  # 예: '20240715'

            if not report_nm or not rcept_dt_str:
                self.logger.warning("report_nm 또는 rcept_dt 누락됨")
                return None

            # 날짜 문자열 파싱
            rcept_dt = datetime.strptime(rcept_dt_str, "%Y%m%d").date()
            cutoff_dt = rcept_dt - timedelta(days=5)

            query = """
                SELECT *
                FROM disclosure_history
                WHERE report_nm = %s
                AND rcept_dt <= %s
                ORDER BY rcept_dt DESC
                LIMIT 1
            """
            result = await self.mysql_client.fetch_one_async(query, (report_nm, cutoff_dt))

            if result:
                return result
            else:
                return None

        except Exception as e:
            self.logger.error(f"유사 공시 검색 실패: {e}")
            return None

    async def save_disclosure_data(
        self, disclosure: Dict, analysis: Dict, 
    ):
        """공시 데이터 저장 이게 메인"""
        try:
            # MySQL에 공시 데이터 저장
            insert_query = """
            INSERT INTO disclosure_history 
            (
                rcept_no, corp_name, corp_code, stock_code, report_nm, flr_nm, rcept_dt, rm,
                summary, impact_score, sentiment, sentiment_reason, expected_impact, impact_duration, keywords
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                summary = VALUES(summary),
                impact_score = VALUES(impact_score),
                sentiment = VALUES(sentiment),
                sentiment_reason = VALUES(sentiment_reason),
                expected_impact = VALUES(expected_impact),
                impact_duration = VALUES(impact_duration),
                keywords = VALUES(keywords);
            """

            await self.mysql_client.execute_query_async(
                insert_query,
                (
                    disclosure.get("rcept_no", ""),
                    disclosure.get("corp_name", ""),
                    disclosure.get("corp_code", ""),
                    disclosure.get("stock_code", ""),
                    disclosure.get("report_nm", ""),
                    disclosure.get("flr_nm", ""),
                    disclosure.get("rcept_dt", ""),
                    disclosure.get("rm", ""),
                    analysis.get("summary", ""),
                    analysis.get("impact_score", 0.0),
                    analysis.get("sentiment", ""),
                    analysis.get("sentiment_reason", ""),
                    analysis.get("expected_impact", ""),
                    analysis.get("impact_duration", ""),
                    ",".join(analysis.get("keywords", [])),
                ),
            )

            self.logger.info(f"공시 데이터 저장 완료: {disclosure.get('rcept_no', '')}")

        except Exception as e:
            self.logger.error(f"공시 데이터 저장 실패: {e}")
            raise

    async def get_stock_price_history(self, stock_code: str, days: int = 5) -> List[Dict]:
        """주가 추이 데이터 가져오기"""
        try:
            # 종목코드 포맷 조정
            symbol = f"{stock_code}.KS" if stock_code.startswith("0") else f"{stock_code}.KQ"
            
            # 주가 데이터 조회
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{days}d")
            
            price_history = []
            for date, row in hist.iterrows():
                price_history.append({
                    "date": str(date)[:10],  # YYYY-MM-DD 형식으로 변환
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"])
                })
            
            return price_history
            
        except Exception as e:
            self.logger.error(f"주가 데이터 조회 실패: {e}")
            return []

    async def send_disclosure_notification(self, disclosure: Dict, analysis: Dict, similar_cases: Optional[List[Dict]] = None):
        """강화된 공시 알림 전송"""
        try:
            # 높은 영향도 공시만 알림 전송
            if analysis.get("impact_score", 0.0) < 0.1:
                return

            stock_code = disclosure.get("stock_code", "")
            stock_name = disclosure.get("corp_name", "")
            
            # 알림 메시지 구성
            message = f"📢 <b>{stock_name}</b> 중요 공시! 📢\n"
            message += f"━━━━━━━━━━━━━━━━━━━\n"
            message += f"📋 <b>공시</b>: {disclosure.get('report_nm', '')}\n"
            message += f"🏢 <b>회사</b>: {stock_name} ({stock_code})\n"
            message += f"📅 <b>공시일</b>: {disclosure.get('rcept_dt', '')}\n\n"

            # 현재 주가 정보 조회 및 추가
            current_price_data = await self.get_stock_price_history(stock_code, days=1)
            if current_price_data:
                latest = current_price_data[-1]
                change_rate = ((latest['close'] - latest['open']) / latest['open'] * 100)
                
                message += f"📊 <b>현재 주가 정보</b>\n"
                message += f"├ <b>현재가</b>: {latest['close']:,.0f}원\n"
                message += f"├ <b>등락률</b>: {change_rate:+.2f}%\n"
                message += f"└ <b>거래량</b>: {latest['volume']:,}주\n\n"

            message += f"⭐ <b>영향 분석</b> (AI 기반)\n"
            message += f"├ <b>영향도</b>: {analysis.get('impact_score', 0.0):.1f}/1.0\n"
            message += f"├ <b>방향</b>: {analysis.get('sentiment', '중립')}\n"
            message += f"└ <b>기간</b>: {analysis.get('impact_duration', '단기')}\n\n"

            message += f"📝 <b>핵심 요약</b>\n"

            message += f"└ <i>{analysis.get('summary', '')}</i>\n\n"


            if analysis.get('keywords'):
                message += f"└ <b>주요 키워드</b>: {', '.join(analysis.get('keywords', []))}"


            else:
                message += f"└ <i>키워드 없음</i>\n"

            # 유사 사례 및 주가 변동 정보 추가
            if similar_cases:
                message += f"🔄 <b>과거 유사 사례 분석</b>\n"

                for i, case in enumerate(similar_cases[:1]): # 가장 최근 1건만 표시
                    case_date = case.get('rcept_dt', '')
                    is_last = i == len(similar_cases[:1]) - 1
                    
                    message += f"{'└' if is_last else '├'} 📜 <b>유사 공시</b>: {case.get('report_nm', '')}\n"

                    message += f"{'  ' if is_last else '│ '}  📅 <b>공시일</b>: {case_date}\n"

                    
                    case_summary = case.get('summary', '')
                    if case_summary:
                        message += f"{'  ' if is_last else '│ '}   <b>요약</b>: {case_summary[:200]}...\n"
                    else:
                        message += f"{'  ' if is_last else '│ '}   <i>요약 없음</i>\n"
                    
                    case_keywords = case.get('keywords')
                    if case_keywords:
                        message += f"{'  ' if is_last else '│ '}   <b>키워드</b>: {case_keywords}\n"
                    else:
                        message += f"{'  ' if is_last else '│ '}   <i>키워드 없음</i>\n"


                    # 주가 데이터 조회
                    five_day_prices = await self.chart_service.get_historical_prices(stock_code, case_date, 5)
                    
                    if five_day_prices:
                        message += f"{'  ' if is_last else '│ '}  📈 <b>이후 5일 주가</b>:\n"
                        
                        for j, price_data in enumerate(five_day_prices):
                            formatted_date = price_data["date"]
                            close_price = price_data["close"]
                            inner_prefix = "└" if j == len(five_day_prices) - 1 else "├"
                            message += f"{'  ' if is_last else '│ '}     {inner_prefix} <code>{formatted_date}</code>: <b>{close_price:,.0f}원</b>\n"

                        # 수익률 계산
                        if len(five_day_prices) >= 2:
                            first_price = five_day_prices[0]["close"]
                            last_price = five_day_prices[-1]["close"]
                            return_rate = ((last_price - first_price) / first_price) * 100
                            
                            if return_rate > 0:
                                message += f"{'  ' if is_last else '│ '}   <b>5일 수익률</b>: <code>+{return_rate:.2f}%</code> ⬆️\n"
                            elif return_rate < 0:
                                message += f"{'  ' if is_last else '│ '}   <b>5일 수익률</b>: <code>{return_rate:.2f}%</code> ⬇️\n"
                            else:
                                message += f"{'  ' if is_last else '│ '}   <b>5일 수익률</b>: <code>{return_rate:.2f}%</code> ➡️\n"
                    else:
                        message += f"{'  ' if is_last else '│ '}   <i>과거 참조 데이터 없음</i>\n"

            message += f"\n━━━━━━━━━━━━━━━━━━━\n"
            message += f"⚠️ <i>AI 분석 정보이며, 투자 참고용입니다.</i>"

            # 텔레그램 알림 전송
            await self.telegram_bot.send_message_async(message)
            
            # 최근 알람 메시지 저장
            await save_latest_signal(message)

            self.logger.info(f"공시 알림 전송 완료: {disclosure.get('rcept_no', '')}")

        except Exception as e:
            self.logger.error(f"공시 알림 전송 실패: {e}")

    
    def _create_disclosure_analysis_prompt(self, disclosure_content: str, stock_name: str) -> str:
        """공시 분석 프롬프트 생성 (gemini_analyzer.py 기반)"""
        return f"""
당신은 주식 투자 전문가입니다. 다음 공시가 {stock_name} 주식에 미치는 영향을 분석해주세요.

공시 내용:
{disclosure_content}

다음 분석 결과항목을 제공해주세요:

1. 공시 요약 (3줄 이내):
2. 영향도 점수 (0-1 사이, 0: 매우 부정적, 0.5: 중립, 1: 매우 긍정적):
3. "긍정"/"부정"/"중립" 세가지 중 판단 및 근거:
4. 주요 키워드 (콤마로 구분):
5. 예상 주가 영향 (상승/하락/보합):
6. 영향 지속 시간(단기, 중기, 장기):

다음 JSON 형식으로 **정확하게 JSON 객체 하나만** 출력하세요. 그 외 문장은 포함하지 마세요:

{{
    "summary": "",
    "impact_score": 0.0,
    "sentiment": "",
    "sentiment_reason": "",
    "keywords": ["", ""],
    "expected_impact": "",
    "impact_duration": ""
}}
        """

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """LLM 응답 텍스트를 파싱하여 표준 JSON 객체로 변환합니다. 오류 복구 및 유사 키워드 추출 지원."""

        def get_partial_key_value(d: dict, keyword: str):
            """사전에서 키워드를 포함하는 키의 값을 찾습니다."""
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
            self.logger.warning(f"JSON 파싱실패: {e}. ")

            # 자동 쉼표 삽입, 줄바꿈 오류 보정 등 단순 패턴 보정
            return {
            "summary": "공시 분석 실패",
            "impact_score": 0.5,
            "sentiment": "중립",
            "sentiment_reason": "",
            "keywords": [],
            "expected_impact": "보합",
            "impact_duration": "중기",
        }

        # 부분 키 매칭으로 필요한 값 추출
        return {
            "summary": get_partial_key_value(parsed_json, "summary") or "",
            "impact_score": get_partial_key_value(parsed_json, "impact_score") or 0.5,
            "sentiment": get_partial_key_value(parsed_json, "sentiment") or "중립",
            "sentiment_reason": get_partial_key_value(parsed_json, "sentiment_reason") or "",
            "keywords": get_partial_key_value(parsed_json, "keyword") or [],
            "expected_impact": get_partial_key_value(parsed_json, "expected_impact") or "보합",
            "impact_duration": get_partial_key_value(parsed_json, "impact_duration") or "중기",
        }
    def _get_default_analysis_result(self, reason: str) -> Dict:
        """기본 분석 결과 반환"""
        return {
            "summary": "공시 분석 실패",
            "impact_score": 0.5,
            "sentiment": "중립",
            "sentiment_reason": reason,
            "keywords": [],
            "expected_impact": "보합",
            "impact_duration": "중기",
        }
    
    async def analyze_disclosure(self, disclosure_detail: Dict, stock_name: str) -> Dict:
        """공시 내용 LLM 분석 (모든 모델 통합)"""
        try:
            # 공시 본문 추출
            disclosure_content = disclosure_detail.get("content", "")
            if not disclosure_content:
                return None

            # 통합 프롬프트 생성
            prompt = self._create_disclosure_analysis_prompt(disclosure_content, stock_name)
            
            # LLM 분석 수행 (사용자 선택 모델)
            analysis_response = await self.llm_manager.generate_response(self.current_user_id, prompt)
            
            if not analysis_response:
                self.logger.error("❌ LLM 응답이 없습니다")
                return self._get_default_analysis_result("LLM 응답 없음")
            
            # 응답 파싱
            analysis_result = self._parse_llm_response(analysis_response)
            
            self.logger.info(f"✅ 공시 LLM 분석 완료: {stock_name}")
            return analysis_result

        except Exception as e:
            self.logger.error(f"❌ 공시 LLM 분석 중 오류 발생: {e}")
            return self._get_default_analysis_result(f"분석 오류: {str(e)}")
        
    async def get_stock_name(self, stock_code: str) -> str:
        """종목 코드로 종목명 조회 (없으면 '미래에셋증권' 반환)"""
        try:
            query = "SELECT corp_name FROM disclosure_history WHERE stock_code = %s"
            result = await self.mysql_client.fetch_one_async(query, (stock_code,))
            
            if result and result['corp_name']:
                return result['corp_name']
            else:
                return "미래에셋증권"
            
        except Exception as e:
            self.logger.error(f"종목명 조회 중 오류 발생: {e}")
            return "미래에셋증권"
        
        
    def load_stock_codes(self):
        """종목 코드 로드"""
        try:
            # 여러 경로 시도
            possible_paths = [
                "config/stocks.json",
                "../../config/stocks.json",
                "../../../config/stocks.json",
                "stock_analysis_service/config/stocks.json"
            ]
            
            stocks_data = None
            used_path = None
            
            for path in possible_paths:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        stocks_data = json.load(f)
                        used_path = path
                        logger.debug(f"✅ 종목 코드 파일 로드 성공: {path}")
                        break
                except FileNotFoundError:
                    continue
                except Exception as e:
                    logger.debug(f"❌ 종목 코드 파일 로드 실패 [{path}]: {e}")
                    continue
            
            if stocks_data:
                self.stock_codes = [stock["code"] for stock in stocks_data["stocks"]]
                self.stock_names = {
                    stock["code"]: stock["name"] for stock in stocks_data["stocks"]
                }
                logger.info(f"✅ 종목 코드 로드 성공: {len(self.stock_codes)}개 종목 ({used_path})")
            else:
                raise FileNotFoundError("모든 경로에서 stocks.json 파일을 찾을 수 없습니다")
                
        except Exception as e:
            logger.error(f"❌ 종목 코드 로드 실패: {e}")
            logger.warning("⚠️ 기본 종목 코드 사용: 미래에셋증권")
            self.stock_codes = ["006800"]
            self.stock_names = {"006800": "미래에셋증권"}
        
        
    async def process_disclosure_pipeline_db(self, stock_code: str) -> None:
        """1년치 공시 처리 파이프라인 실행 db 저장용"""
        if not stock_code:
            self.logger.warning("stock_code가 제공되지 않았습니다. 기본값 '006800'으로 설정합니다.")
            stock_code = "006800"
        try:
            # 공시 데이터 가져오기 (1년치)
            disclosures = await self.fetch_disclosure_data(stock_code)
            if not disclosures:
                self.logger.info(f"공시 데이터 없음: {stock_code}")
                return

            # 공시 상세 정보 가져오기 및 LLM 분석
            for disclosure in disclosures:
                try:
                    rcept_no = disclosure.get("rcept_no")
                    
                    # DB에서 중복 확인
                    already_processed = await self.check_processed_disclosure(rcept_no)
                    if already_processed:
                        self.logger.info(f"이미 처리된 공시 건너뜀: {rcept_no}")
                        continue
                    
                    # 공시 상세 정보 가져오기
                    disclosure_detail = await self.dart_client.get_disclosure_detail(rcept_no)
                    if not disclosure_detail:
                        self.logger.warning(f"공시 상세 정보 조회 실패: {rcept_no}")
                        continue
                    
                    # LLM 분석 수행 (통합된 방식)
                    stock_name = await self.get_stock_name(stock_code)
                    llm_analysis = await self.analyze_disclosure(disclosure_detail, stock_name)
                    
                    if not llm_analysis or llm_analysis.get("summary") == "공시 분석 실패":
                        self.logger.error(f"❌ LLM 분석 실패: {rcept_no}")
                        continue  # 실패해도 다음 공시 계속 처리
                    """
                    # ✅ 유사사례 검색
                    similar_case = await self.find_similar_cases_from_mysql(disclosure)
                    similar_cases = [similar_case] if similar_case else []

                    # ✅ 알림 전송
                    await self.send_disclosure_notification(
                        disclosure=disclosure,
                        analysis=llm_analysis,
                        similar_cases=similar_cases
                    )
                    """

                    # 분석 결과 저장
                    await self.save_disclosure_data(disclosure, llm_analysis, similar_cases=[])
                    self.logger.info(f"공시 처리 완료: {rcept_no}")

                except Exception as e:
                    self.logger.error(f"공시 처리 중 오류 발생: {rcept_no}, 오류: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"공시 파이프라인 실행 중 오류 발생: {stock_code}, 오류: {e}")
    
    
    async def process_latest_disclosure_pipeline(self, stock_code: str) -> None:
        """가장 최신 공시만 처리하는 파이프라인 실행 excute 엔드포인트용 (중복 체크 건너뜀)"""
        if not stock_code:
            self.logger.warning("stock_code가 제공되지 않았습니다. 기본값 '006800'으로 설정합니다.")
            stock_code = "006800"
        try:
            # 공시 데이터 가져오기 (가장 최신 공시가 첫 번째에 있다고 가정)
            disclosures = await self.fetch_disclosure_data(stock_code)
            if not disclosures:
                self.logger.info(f"최신 공시 데이터 없음: {stock_code}")
                return

            # 가장 최신 공시 (첫 번째 항목)만 선택
            latest_disclosure = disclosures[0]

            try:
                rcept_no = latest_disclosure.get("rcept_no")
                self.logger.info(f"최신 공시 처리 시작: {rcept_no} (중복 체크 건너뜀)")

                # 처리된 공시인지 확인하는 단계 건너뜀

                # 공시 상세 정보 가져오기
                disclosure_detail = await self.dart_client.get_disclosure_detail(rcept_no)
                if not disclosure_detail:
                    self.logger.warning(f"최신 공시 상세 정보 조회 실패: {rcept_no}")
                    return
                
                # LLM 분석 수행 (통합된 방식)
                stock_name = await self.get_stock_name(stock_code)
                llm_analysis = await self.analyze_disclosure(disclosure_detail, stock_name)
                
                # 유사사례 검색
                similar_case = await self.find_similar_cases_from_mysql(latest_disclosure)
                similar_cases = [similar_case] if similar_case else []

                # 알림 전송
                await self.send_disclosure_notification(
                    disclosure=latest_disclosure,
                    analysis=llm_analysis,
                    similar_cases=similar_cases
                )
                
                # 분석 결과 저장
                await self.save_disclosure_data(latest_disclosure, llm_analysis)
                self.logger.info(f"최신 공시 처리 완료: {rcept_no}")

            except Exception as e:
                self.logger.error(f"최신 공시 처리 중 오류 발생: {rcept_no}, 오류: {e}")

        except Exception as e:
            self.logger.error(f"최신 공시 파이프라인 실행 중 오류 발생: {stock_code}, 오류: {e}")
        
    async def process_disclosure_pipeline(self, stock_code: str) -> None:
        """공시 처리 파이프라인 실행"""
        if not stock_code:
            self.logger.warning("stock_code가 제공되지 않았습니다. 기본값 '006800'으로 설정합니다.")
            stock_code = "006800"
        try:
            # 공시 데이터 가져오기
            disclosures = await self.fetch_disclosure_data(stock_code)
            if not disclosures:
                return


            # 공시 상세 정보 가져오기 및 LLM 분석
            for disclosure in disclosures:
                try:
                    # 이미 처리된 공시인지 확인
                    rcept_no = disclosure.get("rcept_no")
                    if await self.check_processed_disclosure(rcept_no):
                        self.logger.info(f"이미 처리된 공시 건너뜀: {rcept_no}")
                        continue

                    # 공시 상세 정보 가져오기
                    disclosure_detail = await self.dart_client.get_disclosure_detail(rcept_no)
                    if not disclosure_detail:
                        continue
                    
                    # LLM 분석 수행 (통합된 방식)
                    stock_name = await self.get_stock_name(stock_code)
                    llm_analysis = await self.analyze_disclosure(disclosure_detail, stock_name)
                    
                    # ✅ 유사사례 검색
                    similar_case = await self.find_similar_cases_from_mysql(disclosure)
                    similar_cases = [similar_case] if similar_case else []

                    # ✅ 알림 전송
                    
                    await self.send_disclosure_notification(
                        disclosure=disclosure,
                        analysis=llm_analysis,
                        similar_cases=similar_cases
                    )
                    

                    # 분석 결과 저장
                    await self.save_disclosure_data(disclosure, llm_analysis)

                except Exception as e:
                    self.logger.error(f"공시 처리 중 오류 발생: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"공시 파이프라인 실행 중 오류 발생: {e}")
        
        
    async def run_service_db(self):
        """공시 서비스 실행 (1년치 데이터 일괄 처리)"""
        try:
            self.logger.info("공시 서비스 시작")

            # 종목 정보 로드
            with open(project_root / "config" / "stocks.json", encoding="utf-8") as f:
                stocks_config = json.load(f)

            # 모든 종목에 대해 1년치 공시 처리
            for stock in stocks_config["stocks"]:
                stock_code = stock["code"]
                self.logger.info(f"종목 처리 시작: {stock_code}")
                await self.process_disclosure_pipeline_db(stock_code)
                self.logger.info(f"종목 처리 완료: {stock_code}")

            self.logger.info("모든 종목의 1년치 공시 처리 완료")

        except Exception as e:
            self.logger.error(f"공시 서비스 실행 실패: {e}")
            raise
        finally:
            # 리소스 정리
            self.mysql_client.close()

    async def run_service(self):
        """공시 서비스 실행"""
        try:
            self.logger.info("공시 서비스 시작")

            # 종목 정보 로드
            with open(project_root / "config" / "stocks.json", encoding="utf-8") as f:
                stocks_config = json.load(f)

            while True:
                try:
                    for stock in stocks_config["stocks"]:
                        stock_code = stock["code"]
                        await self.process_disclosure_pipeline(stock_code)
                    
                    # 30분 대기 후 다음 실행
                    await asyncio.sleep(1800)  # 30분 = 1800초
                
                except Exception as e:
                    self.logger.error(f"공시 처리 중 오류 발생: {e}")
                    # 오류 발생시 5분 대기 후 재시도
                    await asyncio.sleep(300)

        except Exception as e:
            self.logger.error(f"공시 서비스 실행 실패: {e}")
            raise
        finally:
            # 리소스 정리
            self.mysql_client.close()

# 서비스 인스턴스 생성 (지연 초기화)
disclosure_service = None
latest_signal_message = None  # 최근 알람 메시지 저장

def get_disclosure_service():
    """공시 서비스 인스턴스 반환 (지연 초기화)"""
    global disclosure_service
    if disclosure_service is None:
        disclosure_service = DisclosureService()
    return disclosure_service

# 독립적 스케줄링을 위한 마지막 실행 시간 추적
last_execution_time = None

async def save_latest_signal(message: str):
    """최근 알람 메시지 저장"""
    global latest_signal_message
    latest_signal_message = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "service": "disclosure"
    }

def should_execute_now() -> tuple[bool, str]:
    """현재 실행할 시간인지 판단 (1시간 간격)"""
    global last_execution_time
    
    now = datetime.now()
    
    # 첫 실행인 경우
    if last_execution_time is None:
        return True, "첫 실행"
    
    # 마지막 실행으로부터 경과 시간 계산 (1시간 = 3600초)
    time_diff = (now - last_execution_time).total_seconds()
    required_interval = 3600  # 1시간
    
    if time_diff >= required_interval:
        return True, f"1시간 간격 - 마지막 실행: {last_execution_time.strftime('%H:%M')}"
    else:
        remaining = int(required_interval - time_diff)
        remaining_minutes = remaining // 60
        return False, f"1시간 간격 - {remaining_minutes}분 후 실행 가능"

async def execute_disclosure_analysis() -> Dict:
    """공시 분석 실행"""
    global last_execution_time
    
    try:
        logger.info("🚀 공시 분석 실행 시작")
        
        # 공시 서비스 인스턴스 확인
        service = get_disclosure_service()
        if service is None:
            logger.error("❌ 공시 서비스 인스턴스가 초기화되지 않음")
            return {"success": False, "error": "서비스 인스턴스 없음"}
        
        # 종목 정보 로드
        with open(project_root / "config" / "stocks.json", encoding="utf-8") as f:
            stocks_config = json.load(f)

        total_disclosures = 0
        processed_stocks = []
        
        # 모든 종목에 대해 공시 분석 실행
        for stock in stocks_config["stocks"]:
            stock_code = stock["code"]
            
            try:
                logger.info(f"📋 {stock_code} 공시 분석 시작")
                
                # 종목별 공시 처리 파이프라인 실행
                await service.process_disclosure_pipeline(stock_code)
                
                processed_stocks.append(stock_code)
                logger.info(f"✅ {stock_code} 공시 분석 완료")
                
            except Exception as e:
                logger.error(f"❌ {stock_code} 공시 분석 실패: {e}")
                continue
        
        # 실행 시간 업데이트
        last_execution_time = datetime.now()
        
        result = {
            "success": True,
            "processed_stocks": len(processed_stocks),
            "total_disclosures": total_disclosures,
            "execution_time": last_execution_time.isoformat()
        }
        
        logger.info(f"✅ 공시 분석 완료: {len(processed_stocks)}개 종목")
        return result
        
    except Exception as e:
        logger.error(f"❌ 공시 분석 실행 실패: {e}")
        return {"success": False, "error": str(e)}
    

async def execute_disclosure_analysis_forexcute() -> Dict:
    """공시 분석 실행"""
    global last_execution_time
    global latest_signal_message # Add this line to access the global variable
    
    try:
        logger.info("🚀 공시 분석 실행 시작")
        
        # 공시 서비스 인스턴스 확인
        service = get_disclosure_service()
        if service is None:
            logger.error("❌ 공시 서비스 인스턴스가 초기화되지 않음")
            return {"success": False, "error": "서비스 인스턴스 없음"}
        
        # 종목 정보 로드
        with open(project_root / "config" / "stocks.json", encoding="utf-8") as f:
            stocks_config = json.load(f)

        total_disclosures = 0
        processed_stocks = []
        
        # 모든 종목에 대해 공시 분석 실행
        for stock in stocks_config["stocks"]:
            stock_code = stock["code"]
            
            try:
                logger.info(f"📋 {stock_code} 공시 분석 시작")
                
                # 종목별 공시 처리 파이프라인 실행
                await service.process_latest_disclosure_pipeline(stock_code)
                
                processed_stocks.append(stock_code)
                logger.info(f"✅ {stock_code} 공시 분석 완료")
                
            except Exception as e:
                logger.error(f"❌ {stock_code} 공시 분석 실패: {e}")
                continue
        
        # 실행 시간 업데이트
        last_execution_time = datetime.now()
        
        result = {
            "success": True,
            "processed_stocks": len(processed_stocks),
            "total_disclosures": total_disclosures,
            "execution_time": last_execution_time.isoformat(),
            "telegram_message": latest_signal_message.get("message") if latest_signal_message else None # Add this line
        }
        
        logger.info(f"✅ 공시 분석 완료: {len(processed_stocks)}개 종목")
        return result
        
    except Exception as e:
        logger.error(f"❌ 공시 분석 실행 실패: {e}")
        return {"success": False, "error": str(e), "telegram_message": None} # Add this line

# FastAPI 엔드포인트
@app.post("/set-user/{user_id}")
async def set_user_id_endpoint(user_id: str):
    """사용자 ID 설정 엔드포인트"""
    try:
        disclosure_service = get_disclosure_service()
        await disclosure_service.set_user_id(user_id)
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
    """사용자 설정 조회 엔드포인트"""
    try:
        disclosure_service = get_disclosure_service()
        await disclosure_service.set_user_id(user_id)
        
        # 사용자 설정 조회
        user_config = await disclosure_service.user_config_manager.get_user_config(user_id)
        
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
    """최근 알람 메시지 조회"""
    global latest_signal_message
    if latest_signal_message:
        return latest_signal_message
    else:
        return {
            "message": "아직 알람이 발생하지 않았습니다.",
            "timestamp": datetime.now().isoformat(),
            "service": "disclosure"
        }

@app.post("/execute")
async def execute_disclosure_analysis_endpoint(request: Request):
    """공시 분석 실행 - 사용자별 동적 처리"""
    try:
        # --- 로그 추가 ---
        print("="*50)
        print("DISCLOSURE LOG:   최종 목적지 도착!")
        print("DISCLOSURE LOG: 게이트웨이로부터 /execute 요청을 성공적으로 받았습니다.")
        print(f"DISCLOSURE LOG: 요청 헤더: {request.headers}")
        print("DISCLOSURE LOG: 지금부터 실제 공시 분석을 시작합니다...")
        print("="*50)
        # --- 로그 추가 끝 ---

        # Header에서 user_id 추출 (문자열로 처리)
        user_id = request.headers.get("X-User-ID", "1")
        
        # 서비스 인스턴스의 user_id 동적 업데이트
        service = get_disclosure_service()
        if service.current_user_id != user_id:
            await service.set_user_id(user_id)
            logger.info(f" 사용자 컨텍스트 변경: {user_id}")
        
        # 공시 분석 실행
        result = await execute_disclosure_analysis_forexcute()
        
        # --- 로그 추가 ---
        print("="*50)
        print("DISCLOSURE LOG:  분석 완료! 결과를 게이트웨이로 반환합니다.")
        print(f"DISCLOSURE LOG: 반환 결과: {result}")
        print("="*50)
        # --- 로그 추가 끝 ---
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 공시 분석 실행 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/check-schedule")
async def check_schedule():
    """오케스트레이터 체크 신호 수신 - 독립적으로 실행 시간 판단"""
    try:
        should_run, reason = should_execute_now()
        
        if should_run:
            # 실행 조건 만족 시 공시 분석 실행
            result = await execute_disclosure_analysis()
            
            if result["success"]:
                return {
                    "executed": True,
                    "message": f"공시 분석 실행 완료 - {reason}",
                    "details": result
                }
            else:
                return {
                    "executed": False,
                    "message": f"공시 분석 실행 실패 - {result.get('error', 'Unknown')}",
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

    # === 사용자별 개인화 기능 ===
    
    async def initialize_user_personalization(self):
        """사용자 개인화 설정 초기화"""
        try:
            self.user_config_loader = await get_config_loader()
            self.logger.info("✅ 사용자 개인화 로더 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 사용자 개인화 로더 초기화 실패: {e}")
            self.user_config_loader = None

    async def get_personalized_config(self, user_id: str) -> Dict[str, Any]:
        """사용자별 개인화 설정 조회"""
        try:
            if not self.user_config_loader:
                self.logger.warning("⚠️ 사용자 설정 로더가 초기화되지 않음 - 기본값 사용")
                return self._get_default_config()
            
            # 캐시에서 먼저 확인
            if user_id in self.personalized_configs:
                return self.personalized_configs[user_id]
            
            # API를 통해 사용자 설정 로드
            config = await self.user_config_loader.load_user_config(user_id)
            if config:
                # 공시 서비스에 특화된 설정 추출
                personalized_config = {
                    "user_id": user_id,
                    "stocks": [stock["stock_code"] for stock in config.get("stocks", [])],
                    "model_type": config.get("model_type", "hyperclova"),
                    "active_service": config.get("active_services", {}).get("disclosure_service", 0) == 1
                }
                
                # 캐시에 저장
                self.personalized_configs[user_id] = personalized_config
                self.logger.info(f"✅ 사용자 개인화 설정 로드 완료: {user_id}")
                return personalized_config
            else:
                self.logger.warning(f"⚠️ 사용자 설정을 찾을 수 없음: {user_id} - 기본값 사용")
                return self._get_default_config()
                
        except Exception as e:
            self.logger.error(f"❌ 사용자 개인화 설정 로드 실패: {user_id} - {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "user_id": "default",
            "stocks": ["005930", "000660"],  # 기본 종목: 삼성전자, SK하이닉스
            "model_type": "hyperclova",
            "active_service": True
        }

    async def should_analyze_for_user(self, user_id: str, stock_code: str) -> bool:
        """특정 사용자에 대해 해당 종목을 분석해야 하는지 확인"""
        try:
            config = await self.get_personalized_config(user_id)
            
            # 서비스가 비활성화된 경우
            if not config.get("active_service", True):
                return False
            
            # 사용자가 선택한 종목에 포함되지 않은 경우
            user_stocks = config.get("stocks", [])
            if stock_code not in user_stocks:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 사용자별 분석 필요성 확인 실패: {user_id}, {stock_code} - {e}")
            return True  # 오류 시 기본적으로 분석 진행

    async def get_user_analysis_model(self, user_id: str) -> str:
        """사용자가 선택한 AI 모델 반환"""
        try:
            config = await self.get_personalized_config(user_id)
            return config.get("model_type", "hyperclova")
        except Exception as e:
            self.logger.error(f"❌ 사용자 AI 모델 조회 실패: {user_id} - {e}")
            return "hyperclova"

    def clear_user_cache(self, user_id: Optional[str] = None):
        """사용자 설정 캐시 클리어"""
        if user_id:
            self.personalized_configs.pop(user_id, None)
            if self.user_config_loader:
                self.user_config_loader.clear_cache(user_id)
            self.logger.debug(f"🧹 사용자 설정 캐시 클리어: {user_id}")
        else:
            self.personalized_configs.clear()
            if self.user_config_loader:
                self.user_config_loader.clear_cache()
            self.logger.debug("🧹 모든 사용자 설정 캐시 클리어")

def main():
    """메인 실행 함수"""
    try:
        logger.info("🚀 공시 서비스 시작 (포트: 8002)")
        
        # FastAPI 서버 실행
        uvicorn.run(app, host="0.0.0.0", port=8002)

    except KeyboardInterrupt:
        print("서비스 중단")
    except Exception as e:
        print(f"서비스 실행 실패: {e}")

async def test_process_pipeline_function():
    """
    disclosure_service.py의 process_disclosure_pipeline 함수를 테스트하기 위한 함수입니다.
    """
    print("--- Disclosure Service 파이프라인 테스트 시작 ---")
    try:
        # DisclosureService 인스턴스 생성
        service = DisclosureService()
        
        # 테스트할 종목 코드 설정 (예: 미래에셋증권)
        test_stock_code = "006800" 
        print(f"테스트 대상 종목: {test_stock_code}")

        # 파이프라인 실행
        await service.process_latest_disclosure_pipeline(test_stock_code)

        print("--- 테스트가 성공적으로 완료되었습니다. ---")

    except Exception as e:
        print(f"--- 테스트 중 오류 발생: {e} ---")
    finally:
        # 리소스 정리 (필요한 경우)
        if 'service' in locals() and hasattr(service, 'mysql_client'):
            service.mysql_client.close()
        print("--- Disclosure Service 파이프라인 테스트 종료 ---")


if __name__ == "__main__":
    # --- process_disclosure_pipeline 테스트를 원할 경우 아래 코드의 주석을 해제하세요 ---
    #asyncio.run(test_process_pipeline_function())

    # --- execute_disclosure_analysis 테스트를 원할 경우 아래 코드의 주석을 해제하세요 ---
    # asyncio.run(test_single_function())

    # --- 원래 서버를 실행하려면 아래 코드의 주석을 해제하고 위 코드를 주석 처리하세요 ---
    main()
