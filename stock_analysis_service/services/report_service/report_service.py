"""
주간 보고서 서비스 (Report Service)
- 리서치 보고서 크롤링 (네이버 금융 PDF)
- 종합 분석 리포트 생성
- 핵심 키워드 추출 및 저장
- 매주 일요일 저녁 실행
"""
import nest_asyncio
import asyncio
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path
import sys
import PyPDF2
from textwrap import wrap
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from reportlab.lib.pagesizes import letter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from research_crawler import ResearchCrawler
from webdriver_manager.chrome import ChromeDriverManager
import hashlib
import time
import schedule

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.database.vector_db import VectorDBClient
from shared.llm.llm_manager import llm_manager
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config
from shared.user_config.user_config_manager import user_config_manager

# FastAPI 추가
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
import uvicorn

app = FastAPI(title="Weekly Report Service", version="1.0.0")

class ReportService:
    """주간 보고서 서비스 클래스"""

    def __init__(self):
        # 개발자 기본 설정 로드
        self.config = get_config()
        
        # 사용자 설정 관리자 초기화
        self.user_config_manager = user_config_manager
        self.current_user_id = "1"  # 기본 사용자 ID
        self.stocks_config = {}  # 사용자별 종목 설정 (MySQL에서 덮어쓰기)
        
        self.mysql_client = get_mysql_client()
        # ChromaDB 대시보드와 동일한 경로를 사용하도록 환경 변수 설정
        import os
        news_service_chroma_path = os.path.join(project_root, "services", "news_service", "data", "chroma")
        os.environ["CHROMADB_PERSIST_DIRECTORY"] = news_service_chroma_path
        self.vector_db = VectorDBClient()
        self.llm_manager = llm_manager
        self.telegram_bot = TelegramBotClient()
        self.research_crawler = ResearchCrawler()

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)
        
        # 사용자별 설정 로드 (MySQL에서 stock_code만 덮어쓰기)
        asyncio.create_task(self._load_user_settings())
        
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
                "005930": {"name": "삼성전자", "enabled": True},
                "000660": {"name": "SK하이닉스", "enabled": True}
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

    async def collect_weekly_market_data(self, stock_code: str) -> Dict: ############################################완료 
        """
        ChromaDB에서 지난 7일간의 리서치 보고서 텍스트와
        공시 DB에서 지난 7일간의 공시 요약을 수집하여 반환합니다.
        """
        weekly_news_by_date: Dict[str, str] = {}
        weekly_disclosure_by_date: Dict[str, str] = {}
        weekly_chart_data: List[Dict[str, Any]] = []

        # 1. 지난 7일간의 날짜 범위 계산
        today = datetime.now()
        seven_days_ago = today - timedelta(days=7)

        today_str = today.strftime('%Y-%m-%d')
        seven_days_ago_str = seven_days_ago.strftime('%Y-%m-%d')
        
        seven_days_ago_str_iso = seven_days_ago.strftime('%Y-%m-%dT%H:%M:%S')
        today_str_iso = today.strftime('%Y-%m-%dT%H:%M:%S')

        self.logger.info(f"Collecting weekly market data for {stock_code} from {seven_days_ago_str} to {today_str}...")

        # 2. ChromaDB에서 리서치 보고서 텍스트 조회 (뉴스/리서치 보고서로 간주)
        try:
            # self.vector_db의 collections 속성을 통해 특정 컬렉션을 쿼리합니다.
            # 'weekly_reports' 컬렉션이 메타데이터에 'publication_date' 및 'stock_code'를 포함한
            # 리서치 보고서 텍스트를 저장한다고 가정합니다.
            self.logger.info(f"DEBUG: ChromaDB 쿼리 시작. stock_code: {stock_code}")
            chroma_results = self.vector_db.collections["high_impact_news"].query(
                query_texts=[""], # 메타데이터 필터링을 위한 빈 쿼리 텍스트
                n_results=100, # 검색할 최대 문서 수
                where={
                    "stock_code": "006800"
                },
                include=['documents', 'metadatas'] # 문서 내용과 메타데이터를 함께 가져오도록 명시
            )
            self.logger.info(f"DEBUG: ChromaDB 쿼리 결과 (raw): {chroma_results}")
            if chroma_results and chroma_results.get('documents') and chroma_results.get('metadatas'):
                # ChromaDB의 documents와 metadatas는 리스트의 리스트 형태일 수 있으므로, 첫 번째 리스트를 확인
                if chroma_results['documents'] and chroma_results['documents'][0]:
                    self.logger.info(f"DEBUG: ChromaDB에서 {len(chroma_results['documents'][0])}개의 문서와 메타데이터를 가져왔습니다.")
                    # ChromaDB에서 가져온 데이터를 날짜 기준으로 필터링
                    for i, doc_content in enumerate(chroma_results['documents'][0]):
                        metadata = chroma_results['metadatas'][0][i]
                        publication_date_str = metadata.get('publication_date')
                        self.logger.info(f"DEBUG: 문서 {i} - publication_date_str: {publication_date_str}, metadata: {metadata}")
                        
                        if publication_date_str:
                            try:
                                # ISO 형식의 날짜 문자열을 datetime 객체로 변환
                                # publication_date가 datetime.date 객체일 수도 있으므로, fromisoformat 대신 strptime 사용
                                publication_date = datetime.strptime(publication_date_str.split('T')[0], '%Y-%m-%d').date()
                                self.logger.info(f"DEBUG: 파싱된 publication_date: {publication_date}")
                                self.logger.info(f"DEBUG: 날짜 범위: {seven_days_ago.date()} <= {publication_date} <= {today.date()}")
                                # 7일 범위 내에 있는지 확인
                                if seven_days_ago.date() <= publication_date <= today.date():
                                    self.logger.info(f"DEBUG: 날짜 조건 만족: {publication_date_str}")
                                    if publication_date_str not in weekly_news_by_date:
                                        weekly_news_by_date[publication_date_str] = ""
                                    weekly_news_by_date[publication_date_str] += doc_content + " "
                                    self.logger.info(f"DEBUG: weekly_news_by_date 업데이트됨. 현재 길이: {len(weekly_news_by_date)}")
                                else:
                                    self.logger.info(f"DEBUG: 날짜 조건 불만족: {publication_date_str}")
                            except ValueError:
                                self.logger.warning(f"잘못된 날짜 형식 또는 파싱 오류: {publication_date_str}")
                        else:
                            self.logger.info(f"DEBUG: publication_date_str이 없습니다.")

                self.logger.info(f"ChromaDB: 지난 7일간 {stock_code}에 대한 리서치 보고서 {len(weekly_news_by_date)}일치를 찾았습니다.")
            else:
                self.logger.info(f"ChromaDB: 지난 7일간 {stock_code}에 대한 리서치 보고서를 찾지 못했습니다. (chroma_results 비어있음)")

        except Exception as e:
            self.logger.error(f"ChromaDB 리서치 보고서 쿼리 중 오류 발생: {e}")


        # 3. 공시 DB에서 공시 요약 조회
        try:
            # 공시 데이터가 self.mysql_client를 통해 접근 가능한 MySQL 테이블에 있고,
            # 'rcept_dt' (접수일) 및 'summary' 컬럼을 가지고 있다고 가정합니다.
            disclosure_query = """
            SELECT rcept_dt, summary FROM disclosure_history
            WHERE stock_code = %s AND rcept_dt >= %s AND rcept_dt <= %s
            """
            disclosure_data = await self.mysql_client.fetch_all_async(
                disclosure_query, (stock_code, seven_days_ago_str, today_str)
            )
            if disclosure_data:
                for row in disclosure_data:
                    rcept_dt = row.get('rcept_dt')
                    summary = row.get('summary')
                    if rcept_dt and summary:
                        rcept_dt_str = rcept_dt.strftime('%Y-%m-%d') if isinstance(rcept_dt, datetime) else str(rcept_dt)
                        if rcept_dt_str not in weekly_disclosure_by_date:
                            weekly_disclosure_by_date[rcept_dt_str] = ""
                        weekly_disclosure_by_date[rcept_dt_str] += summary + " "

                self.logger.info(f"공시 DB: {stock_code}에 대한 공시 요약 {len(weekly_disclosure_by_date)}일치를 찾았습니다.")
            else:
                self.logger.info(f"공시 DB: 지난 7일간 {stock_code}에 대한 공시 요약을 찾지 못했습니다.")
        except Exception as e:
            self.logger.error(f"공시 DB 요약 쿼리 중 오류 발생: {e}")

        # 4. 차트 데이터 수집
        try:
            chart_query = """
            SELECT date, close_price, volume FROM chart_analysis_results
            WHERE stock_code = %s AND date >= %s AND date <= %s
            ORDER BY date ASC
            """
            chart_results = await self.mysql_client.fetch_all_async(
                chart_query, (stock_code, seven_days_ago_str, today_str)
            )
            if chart_results:
                for row in chart_results:
                    chart_date_str = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else str(row['date'])
                    weekly_chart_data.append({
                        "date": chart_date_str,
                        "close_price": float(row['close_price']),
                        "volume": int(row['volume'])
                    })
                self.logger.info(f"차트 DB: {stock_code}에 대한 차트 데이터 {len(weekly_chart_data)}개를 찾았습니다.")
            else:
                self.logger.info(f"차트 DB: 지난 7일간 {stock_code}에 대한 차트 데이터를 찾지 못했습니다.")
        except Exception as e:
            self.logger.error(f"차트 DB 쿼리 중 오류 발생: {e}")

        # 수집된 데이터를 요청된 형식으로 변환
        result_list = []

        if weekly_news_by_date:
            result_list.append({"impact_news": weekly_news_by_date})
        if weekly_disclosure_by_date:
            result_list.append({"disclosure": weekly_disclosure_by_date})
        if weekly_chart_data:
            result_list.append({"chart": weekly_chart_data})

        return result_list
    
    
   
   
    def _format_weekly_market_data_for_llm(self, weekly_market_data: List[Dict]) -> str:
        formatted_text = []
        for item in weekly_market_data:
            if "impact_news" in item:
                formatted_text.append("### 주간 뉴스:")
                for date_str, news_content in item["impact_news"].items():
                    formatted_text.append(f"- {date_str}: {news_content.strip()}")
            elif "disclosure" in item:
                formatted_text.append("### 주간 공시:")
                for date_str, disclosure_content in item["disclosure"].items():
                    formatted_text.append(f"- {date_str}: {disclosure_content.strip()}")
            elif "chart" in item:
                formatted_text.append("### 주간 차트 데이터:")
                for chart_entry in item["chart"]:
                    formatted_text.append(f"- 날짜: {chart_entry['date']}, 종가: {chart_entry['close_price']}, 거래량: {chart_entry['volume']}")
        return "\n".join(formatted_text)

    def _generate_pdf_report(self, report_text: str, stock_code: str) -> BytesIO:
        """리포트 텍스트를 PDF로 메모리에 생성"""
        try:
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)

            try:
                # static/fonts/NanumGothic.ttf 경로에서 폰트 로드
                font_path = Path(__file__).parent.parent.parent / "static" / "fonts" / "NanumGothic.ttf"
                if not font_path.exists():
                    raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")
                pdfmetrics.registerFont(TTFont('NanumGothic', str(font_path)))
                c.setFont('NanumGothic', 12)
            except Exception as e:
                self.logger.warning(f"나눔고딕 폰트 로드 실패: {e}. 기본 폰트로 대체합니다.")
                c.setFont('Helvetica', 12)

            textobject = c.beginText()
            textobject.setTextOrigin(50, 750)
            textobject.setLeading(14)

            wrapped_lines = []
            for line in report_text.split('\n'):
                # 긴 줄은 잘라서 wrap
                
                # ✅ 문단 구분용: * 로 시작하면 빈 줄 추가
                if line.startswith("*"):
                    wrapped_lines.append("")  # 문단 간 빈 줄
                    line = "• " + line.lstrip("*").strip()  # 보기 좋게 마크 달기 (★, • 등 취향)
                wrapped = wrap(line, width=50)  # width는 글자 수 기준
                wrapped_lines.extend(wrapped if wrapped else [""])  # 빈 줄도 유지

            for line in wrapped_lines:
                textobject.textLine(line)
            c.drawText(textobject)
            c.save()
            buffer.seek(0)
            return buffer

        except Exception as e:
            self.logger.error(f"PDF 생성 실패: {e}")
            return BytesIO()
        

   
    async def send_weekly_report_telegram(self, stock_code: str, pdf_buffer: BytesIO, keywords: List[str]):
        """PDF BytesIO 객체를 텔레그램으로 전송"""
        try:
            message = f"""
                📢 주간 리포트가 도착했어요!

                📅 **기간**: {datetime.now().strftime('%Y-%m-%d')} 기준 일주일  
                🏢 **종목**: {stock_code}  

                일주일간 차트, 공시, 주요 뉴스를 종합해서 리포트를 작성했어요!  
                자세한 내용은 첨부된 PDF를 참고해주세요.

                🔍 주요 키워드: {', '.join(keywords)}
                        """

            # 파일 이름은 텔레그램에 표시만 됨
            file_name = f"weekly_report_{stock_code}.pdf"

            success = self.telegram_bot.send_document_from_buffer(document=pdf_buffer, filename=file_name, caption=message)

            # 최근 알람 메시지 저장
            if success:
                await save_latest_signal(message)
            
            if success:
                self.logger.info(f"주간 보고서 텔레그램 전송 완료: {stock_code}")
            else:
                self.logger.error(f"주간 보고서 텔레그램 전송 실패: {stock_code}")

        except Exception as e:
            self.logger.error(f"텔레그램 전송 중 오류: {e}")

    async def save_keywords_to_vector_db(self, stock_code: str, keywords: List[str]):
        """주어진 키워드를 벡터 DB의 'weekly_keywords' 컬렉션에 저장합니다."""
        try:
            if not keywords:
                self.logger.info(f"{stock_code}에 대한 저장할 키워드가 없습니다.")
                return

            self.logger.info(f"{stock_code}에 대한 키워드를 벡터 DB에 저장 시작...")

            # 1. 날짜 및 시간 정보 생성
            now = datetime.now()
            week_start = now - timedelta(days=7)
            week_start_str = week_start.strftime('%Y-%m-%dT00:00:00')

            # 2. 중복 체크
            existing_keywords = self.vector_db.collections["keywords"].get(
                where={
                    "$and": [
                        {"stock_code": {"$eq": stock_code}},
                        {"week_start": {"$eq": week_start_str}}
                    ]
                },
                limit=1
            )

            if existing_keywords and len(existing_keywords['ids']) > 0:
                self.logger.warning(f"중복 키워드 발견 - 저장 건너뜀: {stock_code} {week_start_str}")
                return

            # 3. 종목 이름 조회
            try:
                with open(project_root / "config" / "stocks.json", "r", encoding="utf-8") as f:
                    stocks_config = json.load(f)
                stock_name = stocks_config.get(stock_code, {}).get("name", "Unknown")
            except Exception as e:
                self.logger.error(f"stocks.json 파일 로드 실패: {e}")
                stock_name = "Unknown"

            # 4. 고유 ID 생성
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            microseconds = int(time.time() * 1000000) % 1000000
            keywords_hash = hashlib.md5(",".join(keywords).encode('utf-8')).hexdigest()[:6]
            keyword_id = f"keyword_{stock_code}_{timestamp}_{microseconds:06d}_{keywords_hash}"

            # 5. 메타데이터 구성
            metadata = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "keywords_json": json.dumps(keywords, ensure_ascii=False),
                "keywords_text": ", ".join(keywords),
                "keywords_count": len(keywords),
                "importance_scores_json": json.dumps([]),  # null 대신 빈 리스트의 JSON 문자열
                "week_start": week_start_str,
                "week_end": now.strftime('%Y-%m-%dT00:00:00'),
                "type": "keywords",
                "created_at": now.isoformat(),
            }

            # 6. 벡터 DB에 저장할 문서(document) 생성 (임베딩될 실제 텍스트)
            document_for_embedding = ", ".join(keywords)

            # 7. 벡터 DB에 데이터 추가
            self.vector_db.add_documents(
                collection_name="keywords",
                documents=[document_for_embedding],
                metadatas=[metadata],
                ids=[keyword_id]
            )

            self.logger.info(f"{stock_code}에 대한 키워드를 벡터 DB에 성공적으로 저장했습니다. (ID: {keyword_id})")

        except Exception as e:
            self.logger.error(f"벡터 DB에 키워드 저장 실패: {e}")

    async def process_weekly_report(self, stock_code: str):
        """주간 보고서 처리"""
        try:
            self.logger.info(f"주간 보고서 처리 시작: {stock_code}")

            # 1. 리서치 보고서 크롤링
            research_report = await self.research_crawler.get_preprocessed_text_for_stock(stock_code) #리서치 text 반환

            # 2. 뉴스, 공시 ,차트 일주일간 데이터 수집 list 형태로 반환됨
            
            weekly_market_data = await self.collect_weekly_market_data(stock_code) 
            
            
            # 3. 종합보고서 및 키워드 생성 dict 형식으로 받기
            weekly_market_data = self._format_weekly_market_data_for_llm(weekly_market_data) # weekly_market_data를 텍스트 형태로 변환
            
            # 종합 보고서 및 키워드 생성 (기존 프롬프트 사용)
            prompt = f"""
            최신 리서치 보고서와 일주일치 뉴스, 공시, 차트 데이터를 보고 분석하여 최대한 자세하게 주간 리포트를 작성하시오.
            보고서에는 다음 내용을 포함해야 합니다:
            
            📌 다음 항목을 순서대로 포함하시오. 각 항목은 반드시 새로운 줄에 시작하며, **문단 시작을 '*'로 표시**하시오:
            *시장 전반에 대한 요약 및 주요 이슈
            *특정 종목에 대한 분석 (긍정적/부정적 요인, 투자 의견 등)
            *주요 뉴스 및 공시 내용 요약 (날짜별 구분)
            *차트 데이터 분석 (가격 변동, 거래량 추이 등)
            *향후 전망 및 투자 전략 제안
            *보고서의 핵심 키워드 (문단 맨 마지막에 표시)

            ---
            최신 리서치 보고서:
            {research_report}

            ---
            일주일치 시장 데이터:
            {weekly_market_data}

            ---
            **응답 결과는 반드시 다음 JSON 형태로 하나의 json 객체로 반환해야 합니다 (모든 key와 string은 큰따옴표 `"`로 둘러쌈)**:
            {{
            "report": "리포트 내용 여기에",
            "keywords": ["키워드1", "키워드2", "키워드3"]
            }}
            """
            
            report_response = await self.llm_manager.generate_response(self.current_user_id, prompt)
            
            # 응답 파싱
            try:
                import json
                comprehensive_report_data = json.loads(report_response)
            except:
                # 파싱 실패 시 기본값
                comprehensive_report_data = {
                    "report": "주간 보고서 생성 실패",
                    "keywords": ["보고서", "생성", "실패"]
                }
            
            
            
            # 4. 보고서 text만 텔레그램으로 전송 (pdf 형식으로)
            
            report_pdf= self._generate_pdf_report(
                comprehensive_report_data["report"], stock_code
            )
            
            await self.send_weekly_report_telegram(
                stock_code, report_pdf, comprehensive_report_data["keywords"]
            )
            
            # 5. 키워드 vector DB 저장
            await self.save_keywords_to_vector_db(
                stock_code, comprehensive_report_data["keywords"]
            )
            self.logger.info(f"주간 보고서 처리 완료: {stock_code}")
   

            

            self.logger.info(f"주간 보고서 처리 완료: {stock_code}")

        except Exception as e:
            self.logger.error(f"주간 보고서 처리 실패: {e}")


    async def run_service(self):
        """주간 보고서 서비스 실행"""
        try:
            self.logger.info("주간 보고서 서비스 시작")

            # 데이터베이스 초기화

            # 종목 정보 로드
            with open(
                project_root / "config" / "stocks.json", "r", encoding="utf-8"
            ) as f:
                stocks_config = json.load(f)

            # 스케줄 설정 - 매주 일요일 18:00
            def run_weekly_report():
                asyncio.run(self.process_all_stocks(stocks_config))
                #asyncio.create_task(self.process_all_stocks(stocks_config))

            schedule.every().sunday.at("18:00").do(run_weekly_report)

            # 실행 루프
            while True:
                try:
                    schedule.run_pending()

                    # 1시간마다 스케줄 체크
                    await asyncio.sleep(3600)

                except KeyboardInterrupt:
                    self.logger.info("서비스 중단 요청")
                    break
                except Exception as e:
                    self.logger.error(f"서비스 실행 오류: {e}")
                    await asyncio.sleep(60)

        except Exception as e:
            self.logger.error(f"주간 보고서 서비스 실행 실패: {e}")
            raise
        finally:
            # 리소스 정리
            self.mysql_client.close()
            self.close_driver()

    async def process_all_stocks(self, stocks_config: Dict):
        """모든 활성 종목 처리"""
        try:
            for stock_code, stock_info in stocks_config.items():
                if stock_info.get("active", False):
                    await self.process_weekly_report(stock_code)

        except Exception as e:
            self.logger.error(f"전체 종목 처리 실패: {e}")

# 서비스 인스턴스 생성
report_service_instance = None
latest_signal_message = None  # 최근 알람 메시지 저장

def get_report_service():
    """보고서 서비스 인스턴스 반환"""
    global report_service_instance
    if report_service_instance is None:
        report_service_instance = ReportService()
    return report_service_instance

# === FastAPI 엔드포인트 ===
@app.post("/set-user/{user_id}")
async def set_user_id_endpoint(user_id: str):
    """사용자 ID 설정 엔드포인트"""
    try:
        report_service = get_report_service()
        await report_service.set_user_id(user_id)
        return {
            "success": True,
            "message": f"사용자 ID 설정 완료: {user_id}",
            "user_id": user_id
        }
    except Exception as e:
        logging.error(f"❌ 사용자 ID 설정 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 ID 설정에 실패했습니다")

@app.get("/user-config/{user_id}")
async def get_user_config_endpoint(user_id: str):
    """사용자 설정 조회 엔드포인트"""
    try:
        report_service = get_report_service()
        await report_service.set_user_id(user_id)
        
        # 사용자 설정 조회
        user_config = await report_service.user_config_manager.get_user_config(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "config": {
                "stocks": user_config.get("stocks", [])
            }
        }
    except Exception as e:
        logging.error(f"❌ 사용자 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 설정 조회에 실패했습니다")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/signal")
async def get_signal():
    return get_latest_signal()

async def save_latest_signal(message: str):
    """최근 알람 메시지 저장"""
    global latest_signal_message
    latest_signal_message = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "service": "report"
    }

# === FastAPI 엔드포인트 ===

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
            "service": "report"
        }

# === 스케줄링 관련 변수 ===
last_execution_time = None

def should_execute_now() -> Tuple[bool, str]:
    """현재 실행할 시간인지 판단 (주간 보고서 전용 로직)"""
    global last_execution_time
    
    now = datetime.now()
    current_weekday = now.weekday()  # 0=월요일, 6=일요일
    current_time = now.time()
    
    # 주간 보고서 실행 시간: 매주 일요일 저녁 8시 (20:00)
    target_weekday = 6  # 일요일
    target_time = datetime.strptime("20:00", "%H:%M").time()
    
    # 첫 실행인 경우
    if last_execution_time is None:
        # 일요일 저녁인지 확인
        if current_weekday == target_weekday and current_time >= target_time:
            return True, "첫 실행 - 일요일 저녁"
        else:
            return False, f"주간 보고서 대기 중 - 일요일 20:00 실행 예정 (현재: {now.strftime('%A %H:%M')})"
    
    # 마지막 실행으로부터 경과 시간 계산
    time_diff = (now - last_execution_time).total_seconds()
    
    # 주간 간격 체크 (7일 = 604800초)
    weekly_interval = 7 * 24 * 3600  # 7일
    
    # 일요일 저녁이고, 지난 실행으로부터 최소 6일이 지났는지 확인
    if (current_weekday == target_weekday and 
        current_time >= target_time and 
        time_diff >= (6 * 24 * 3600)):  # 최소 6일 간격
        return True, f"주간 보고서 실행 시간 - 마지막 실행: {last_execution_time.strftime('%Y-%m-%d %H:%M')}"
    else:
        if current_weekday != target_weekday:
            days_until_sunday = (6 - current_weekday) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            return False, f"주간 보고서 대기 중 - {days_until_sunday}일 후 일요일 실행"
        elif current_time < target_time:
            remaining_hours = (datetime.combine(now.date(), target_time) - now).total_seconds() / 3600
            return False, f"주간 보고서 대기 중 - {remaining_hours:.1f}시간 후 실행"
        else:
            remaining_days = 7 - (time_diff / (24 * 3600))
            return False, f"주간 보고서 대기 중 - {remaining_days:.1f}일 후 실행 가능"

async def execute_weekly_report() -> Dict:
    """주간 보고서 실행 (오케스트레이터 호출용)"""
    global last_execution_time
    
    try:
        logging.info("🚀 오케스트레이터 신호로 주간 보고서 생성 시작")
        
        # 리포트 서비스 인스턴스 생성 또는 가져오기
        report_service = ReportService()
        
        # 주간 보고서 생성 실행
        # Note: 실제 주간 보고서 생성 로직은 ReportService 클래스 내부에 구현되어 있어야 함
        # 여기서는 기본적인 실행 프레임워크만 제공
        
        processed_stocks = []
        total_reports = 0
        
        # 사용자 설정된 종목들에 대해 보고서 생성
        for stock_code, stock_info in report_service.stocks_config.items():
            try:
                # 리서치 보고서 크롤링 (예시)
                logging.info(f"📊 {stock_code} 주간 보고서 생성 중...")
                
                # 실제 보고서 생성 로직은 ReportService 클래스의 메서드를 호출
                # 예: await report_service.generate_weekly_report(stock_code)
                
                processed_stocks.append(stock_code)
                total_reports += 1
                
                logging.info(f"✅ {stock_code} 주간 보고서 생성 완료")
                
            except Exception as e:
                logging.error(f"❌ {stock_code} 주간 보고서 생성 실패: {e}")
                continue
        
        # 실행 시간 업데이트
        last_execution_time = datetime.now()
        
        result = {
            "success": True,
            "processed_stocks": len(processed_stocks),
            "total_reports": total_reports,
            "execution_time": last_execution_time.isoformat(),
            "next_execution": "다음 주 일요일 20:00"
        }
        
        logging.info(f"✅ 주간 보고서 생성 완료: {len(processed_stocks)}개 종목, {total_reports}개 보고서")
        
        # 완료 알림 저장
        await save_latest_signal(f"📊 주간 보고서 생성 완료: {total_reports}개 보고서")
        
        return result
        
    except Exception as e:
        logging.error(f"❌ 주간 보고서 생성 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/execute")
async def execute_report_generation(request: Request):
    """리포트 생성 실행 - 사용자별 동적 처리"""
    try:
        # Header에서 user_id 추출 (문자열로 처리)
        user_id = request.headers.get("X-User-ID", "1")
        
        # 서비스 인스턴스의 user_id 동적 업데이트
        service = get_report_service()
        if service.current_user_id != user_id:
            await service.set_user_id(user_id)
            logging.info(f"🔄 사용자 컨텍스트 변경: {user_id}")
        
        # 주간 보고서 생성 실행
        result = await execute_weekly_report()
        return result
        
    except Exception as e:
        logging.error(f"❌ 리포트 생성 실행 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/check-schedule")
async def check_schedule():
    """오케스트레이터 체크 신호 수신 - 독립적으로 실행 시간 판단"""
    try:
        should_run, reason = should_execute_now()
        
        if should_run:
            # 실행 조건 만족 시 주간 보고서 생성 실행
            result = await execute_weekly_report()
            
            if result["success"]:
                return {
                    "executed": True,
                    "message": f"주간 보고서 생성 완료 - {reason}",
                    "details": result
                }
            else:
                return {
                    "executed": False,
                    "message": f"주간 보고서 생성 실패 - {result.get('error', 'Unknown')}",
                    "reason": reason
                }
        else:
            return {
                "executed": False,
                "message": reason,
                "next_execution": "매주 일요일 20:00"
            }
        
    except Exception as e:
        logging.error(f"❌ 스케줄 체크 실패: {e}")
        return {
            "executed": False,
            "message": f"스케줄 체크 오류: {str(e)}"
        }

def main():
    """메인 실행 함수"""
    try:
        print("🚀 리포트 서비스 시작 (포트: 8004)")
        
        # FastAPI 서버 실행
        uvicorn.run(app, host="0.0.0.0", port=8004)
    
    except KeyboardInterrupt:
        print("서비스 중단")
    except Exception as e:
        print(f"서비스 실행 실패: {e}")


if __name__ == "__main__":
    main()
