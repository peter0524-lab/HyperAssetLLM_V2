"""
주가 원인 분석 서비스 (Analysis Service)
- 주가 급등락 감지 (10% 이상 + 1000만주 이상)
- 원인 분석 및 과거 사례 검색
- 실시간 모니터링 및 알림
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.database.vector_db import VectorDBClient
from shared.llm.llm_manager import llm_manager
from shared.apis.kis_api import KISAPIClient
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config

# FastAPI 추가
from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn

app = FastAPI(title="Price Analysis Service", version="1.0.0")

class PriceAnalysisService:
    """주가 원인 분석 서비스 클래스"""

    def __init__(self):
        self.config = get_config()
        self.mysql_client = get_mysql_client()
        self.vector_db = VectorDBClient()
        self.llm_manager = llm_manager
        self.kis_client = KISAPIClient()
        self.telegram_bot = TelegramBotClient()

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # 분석 기준 설정
        self.price_change_threshold = 0.10  # 10%
        self.volume_threshold = 10000000  # 1천만주

    async def initialize_database(self):
        """데이터베이스 초기화"""
        try:
            # 주가 급등락 분석 테이블 생성
            create_price_analysis_table = """
            CREATE TABLE IF NOT EXISTS price_analysis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                company_name VARCHAR(200) NOT NULL,
                analysis_date DATE NOT NULL,
                price_before DECIMAL(10,2) NOT NULL,
                price_after DECIMAL(10,2) NOT NULL,
                change_rate DECIMAL(5,2) NOT NULL,
                volume BIGINT NOT NULL,
                analysis_type VARCHAR(20) NOT NULL,
                analysis_result TEXT,
                related_news TEXT,
                related_disclosures TEXT,
                similar_cases TEXT,
                confidence_score DECIMAL(3,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_stock_code (stock_code),
                INDEX idx_analysis_date (analysis_date),
                INDEX idx_change_rate (change_rate),
                INDEX idx_volume (volume)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """

            await self.mysql_client.execute_query_async(create_price_analysis_table)

            # 벡터 DB 컬렉션 생성
            self.vector_db.create_collection("price_analysis_vectors")

            self.logger.info("주가 원인 분석 서비스 데이터베이스 초기화 완료")

        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    async def get_current_price_data(self, stock_code: str) -> Dict:
        """현재 주가 정보 조회"""
        try:
            # KIS API를 통한 현재가 조회
            price_data = self.kis_client.get_current_price(stock_code)

            if not price_data:
                self.logger.warning(f"주가 정보 없음: {stock_code}")
                return {}

            return {
                "current_price": price_data.get("stck_prpr", 0),
                "prev_close": price_data.get("stck_sdpr", 0),
                "change_rate": price_data.get("prdy_ctrt", 0),
                "volume": price_data.get("acml_vol", 0),
                "high": price_data.get("stck_hgpr", 0),
                "low": price_data.get("stck_lwpr", 0),
            }

        except Exception as e:
            self.logger.error(f"현재가 조회 실패: {e}")
            return {}

    async def detect_significant_price_change(self, stock_code: str) -> Optional[Dict]:
        """주가 급등락 감지"""
        try:
            # 현재 주가 정보 조회
            price_data = await self.get_current_price_data(stock_code)

            if not price_data:
                return None

            change_rate = float(price_data.get("change_rate", 0)) / 100
            volume = int(price_data.get("volume", 0))

            # 급등락 조건 확인
            significant_change = abs(change_rate) >= self.price_change_threshold
            high_volume = volume >= self.volume_threshold

            if significant_change and high_volume:
                return {
                    "stock_code": stock_code,
                    "current_price": float(price_data.get("current_price", 0)),
                    "prev_close": float(price_data.get("prev_close", 0)),
                    "change_rate": change_rate,
                    "volume": volume,
                    "high": float(price_data.get("high", 0)),
                    "low": float(price_data.get("low", 0)),
                    "analysis_type": "급등" if change_rate > 0 else "급락",
                    "detected_at": datetime.now().isoformat(),
                }

            return None

        except Exception as e:
            self.logger.error(f"급등락 감지 실패: {e}")
            return None

    async def search_related_news(
        self, stock_code: str, target_date: str
    ) -> List[Dict]:
        """관련 뉴스 검색"""
        try:
            # 당일 및 전일 뉴스 검색
            search_date = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = search_date - timedelta(days=1)

            news_query = """
            SELECT title, content, summary, impact_score, created_at
            FROM news 
            WHERE stock_code = %s 
            AND DATE(created_at) BETWEEN %s AND %s
            ORDER BY impact_score DESC, created_at DESC
            LIMIT 5
            """

            news_data = await self.mysql_client.fetch_all_async(
                news_query, (stock_code, start_date.strftime("%Y-%m-%d"), target_date)
            )

            return news_data

        except Exception as e:
            self.logger.error(f"관련 뉴스 검색 실패: {e}")
            return []

    async def search_related_disclosures(
        self, stock_code: str, target_date: str
    ) -> List[Dict]:
        """관련 공시 검색"""
        try:
            # 당일 및 전일 공시 검색
            search_date = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = search_date - timedelta(days=1)

            disclosure_query = """
            SELECT report_nm, summary, impact_score, rcept_dt
            FROM disclosure_data 
            WHERE stock_code = %s 
            AND rcept_dt BETWEEN %s AND %s
            ORDER BY impact_score DESC, rcept_dt DESC
            LIMIT 5
            """

            disclosure_data = await self.mysql_client.fetch_all_async(
                disclosure_query,
                (stock_code, start_date.strftime("%Y-%m-%d"), target_date),
            )

            return disclosure_data

        except Exception as e:
            self.logger.error(f"관련 공시 검색 실패: {e}")
            return []

    async def search_similar_cases(
        self, stock_code: str, change_rate: float, volume: int
    ) -> List[Dict]:
        """유사 과거 사례 검색"""
        try:
            # 유사한 변동률과 거래량 조건으로 검색
            change_rate_min = change_rate - 0.05  # ±5% 범위
            change_rate_max = change_rate + 0.05
            volume_min = volume * 0.5  # 50% 이상

            similar_query = """
            SELECT * FROM price_analysis 
            WHERE stock_code = %s 
            AND change_rate BETWEEN %s AND %s
            AND volume >= %s
            AND analysis_date < CURDATE()
            ORDER BY ABS(change_rate - %s) ASC
            LIMIT 5
            """

            similar_cases = await self.mysql_client.fetch_all_async(
                similar_query,
                (stock_code, change_rate_min, change_rate_max, volume_min, change_rate),
            )

            # 벡터 DB에서도 유사 사례 검색
            search_text = f"주가 {abs(change_rate)*100:.1f}% {'상승' if change_rate > 0 else '하락'} 거래량 {volume:,}주"

            vector_results = self.vector_db.search_similar_documents(
                query=search_text,
                collection_name="price_analysis_vectors",
                top_k=3
            )

            return similar_cases

        except Exception as e:
            self.logger.error(f"유사 사례 검색 실패: {e}")
            return []

    async def analyze_price_change_with_llm(
        self,
        price_data: Dict,
        news_data: List[Dict],
        disclosure_data: List[Dict],
        similar_cases: List[Dict],
    ) -> Dict:
        """LLM을 활용한 주가 변동 원인 분석"""
        try:
            # 분석용 데이터 구성
            analysis_context = f"""
            주가 변동 정보:
            - 종목: {price_data.get('stock_code')}
            - 변동률: {price_data.get('change_rate', 0)*100:.2f}%
            - 거래량: {price_data.get('volume', 0):,}주
            - 현재가: {price_data.get('current_price', 0):,}원
            - 전일대비: {price_data.get('current_price', 0) - price_data.get('prev_close', 0):,}원
            
            관련 뉴스:
            """

            for news in news_data:
                analysis_context += (
                    f"- {news.get('title', '')}\n  요약: {news.get('summary', '')}\n"
                )

            analysis_context += "\n관련 공시:\n"
            for disclosure in disclosure_data:
                analysis_context += f"- {disclosure.get('report_nm', '')}\n  요약: {disclosure.get('summary', '')}\n"

            analysis_context += "\n유사 과거 사례:\n"
            for case in similar_cases:
                analysis_context += f"- {case.get('analysis_date', '')}: {case.get('change_rate', 0)*100:.1f}% 변동\n"

            # 분석 프롬프트 구성
            analysis_prompt = f"""
            다음 주가 급등락 상황을 분석하여 원인을 파악해주세요:

            {analysis_context}

            분석 요청사항:
            1. 주가 변동의 주요 원인 분석
            2. 각 원인의 영향도 평가 (1-10점)
            3. 향후 주가 전망 (단기/중기)
            4. 투자자 주의사항
            5. 분석 신뢰도 (0.0-1.0)

            응답 형식:
            {{
                "main_causes": [
                    {{"cause": "원인1", "impact": 8, "description": "상세 설명"}},
                    {{"cause": "원인2", "impact": 6, "description": "상세 설명"}}
                ],
                "future_outlook": "향후 전망",
                "investor_notes": "투자자 주의사항",
                "confidence_score": 0.8
            }}
            """

            # LLM 분석 요청 (사용자 선택 모델)
            analysis_result = await self.llm_manager.generate_text(
                user_id=1,  # 기본 사용자 ID (추후 동적 설정 가능)
                prompt=analysis_prompt, 
                max_tokens=1500
            )

            # 결과 파싱
            try:
                analysis_data = json.loads(analysis_result)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값 설정
                analysis_data = {
                    "main_causes": [
                        {
                            "cause": "분석 실패",
                            "impact": 0,
                            "description": "분석 결과를 파싱할 수 없습니다.",
                        }
                    ],
                    "future_outlook": "분석 불가",
                    "investor_notes": "분석 실패로 인한 주의사항 없음",
                    "confidence_score": 0.0,
                }

            return analysis_data

        except Exception as e:
            self.logger.error(f"LLM 주가 분석 실패: {e}")
            return {
                "main_causes": [
                    {"cause": "분석 오류", "impact": 0, "description": str(e)}
                ],
                "future_outlook": "분석 오류",
                "investor_notes": "분석 오류 발생",
                "confidence_score": 0.0,
            }

    async def save_analysis_result(
        self,
        price_data: Dict,
        analysis_result: Dict,
        news_data: List[Dict],
        disclosure_data: List[Dict],
        similar_cases: List[Dict],
    ):
        """분석 결과 저장"""
        try:
            # 종목 이름 조회
            with open(
                project_root / "config" / "stocks.json", "r", encoding="utf-8"
            ) as f:
                stocks_config = json.load(f)

            company_name = stocks_config.get(price_data.get("stock_code"), {}).get(
                "name", ""
            )

            # MySQL에 저장
            insert_query = """
            INSERT INTO price_analysis 
            (stock_code, company_name, analysis_date, price_before, price_after, 
             change_rate, volume, analysis_type, analysis_result, related_news, 
             related_disclosures, similar_cases, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            await self.mysql_client.execute_query_async(
                insert_query,
                (
                    price_data.get("stock_code"),
                    company_name,
                    datetime.now().strftime("%Y-%m-%d"),
                    price_data.get("prev_close", 0),
                    price_data.get("current_price", 0),
                    price_data.get("change_rate", 0),
                    price_data.get("volume", 0),
                    price_data.get("analysis_type", ""),
                    json.dumps(analysis_result, ensure_ascii=False),
                    json.dumps(news_data, ensure_ascii=False),
                    json.dumps(disclosure_data, ensure_ascii=False),
                    json.dumps(similar_cases, ensure_ascii=False),
                    analysis_result.get("confidence_score", 0.0),
                ),
            )

            # 벡터 DB에 저장
            document_text = f"""
            {price_data.get('stock_code')} 주가 {price_data.get('analysis_type')} 
            변동률: {price_data.get('change_rate', 0)*100:.2f}%
            거래량: {price_data.get('volume', 0):,}주
            주요 원인: {' '.join([cause.get('cause', '') for cause in analysis_result.get('main_causes', [])])}
            """

            self.vector_db.add_documents(
                collection_name="price_analysis_vectors",
                documents=[document_text],
                metadatas=[
                    {
                        "stock_code": price_data.get("stock_code"),
                        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                        "change_rate": price_data.get("change_rate", 0),
                        "volume": price_data.get("volume", 0),
                        "analysis_type": price_data.get("analysis_type", ""),
                        "confidence_score": analysis_result.get(
                            "confidence_score", 0.0
                        ),
                    }
                ],
            )

            self.logger.info(f"분석 결과 저장 완료: {price_data.get('stock_code')}")

        except Exception as e:
            self.logger.error(f"분석 결과 저장 실패: {e}")

    async def send_analysis_notification(self, price_data: Dict, analysis_result: Dict):
        """분석 결과 알림 전송"""
        try:
            # 알림 메시지 구성
            message = f"""
🔍 **주가 급등락 원인 분석**

🏷️ **종목**: {price_data.get('stock_code')}
📊 **변동률**: {price_data.get('change_rate', 0)*100:.2f}%
💰 **현재가**: {price_data.get('current_price', 0):,}원
📈 **거래량**: {price_data.get('volume', 0):,}주
📊 **분석 유형**: {price_data.get('analysis_type', '')}
⭐ **신뢰도**: {analysis_result.get('confidence_score', 0.0):.1f}/1.0

🔍 **주요 원인**:
"""

            # 주요 원인 추가
            for cause in analysis_result.get("main_causes", []):
                message += f"• {cause.get('cause', '')}: {cause.get('description', '')} (영향도: {cause.get('impact', 0)}/10)\n"

            message += f"""
📈 **향후 전망**:
{analysis_result.get('future_outlook', '')}

⚠️ **투자자 주의사항**:
{analysis_result.get('investor_notes', '')}

⏰ **분석 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            # 텔레그램 알림 전송
            self.telegram_bot.send_message(message)

            self.logger.info(f"분석 알림 전송 완료: {price_data.get('stock_code')}")

        except Exception as e:
            self.logger.error(f"분석 알림 전송 실패: {e}")

    async def process_price_analysis(self, stock_code: str):
        """주가 분석 처리"""
        try:
            # 1. 급등락 감지
            price_data = await self.detect_significant_price_change(stock_code)

            if not price_data:
                return  # 급등락 조건 미충족

            self.logger.info(
                f"급등락 감지: {stock_code}, {price_data.get('change_rate', 0)*100:.2f}%"
            )

            # 2. 관련 데이터 수집
            target_date = datetime.now().strftime("%Y-%m-%d")

            news_data = await self.search_related_news(stock_code, target_date)
            disclosure_data = await self.search_related_disclosures(
                stock_code, target_date
            )
            similar_cases = await self.search_similar_cases(
                stock_code,
                price_data.get("change_rate", 0),
                price_data.get("volume", 0),
            )

            # 3. LLM 분석
            analysis_result = await self.analyze_price_change_with_llm(
                price_data, news_data, disclosure_data, similar_cases
            )

            # 4. 결과 저장
            await self.save_analysis_result(
                price_data, analysis_result, news_data, disclosure_data, similar_cases
            )

            # 5. 알림 전송
            await self.send_analysis_notification(price_data, analysis_result)

            self.logger.info(f"주가 분석 완료: {stock_code}")

        except Exception as e:
            self.logger.error(f"주가 분석 처리 실패: {e}")

    async def run_service(self):
        """주가 원인 분석 서비스 실행"""
        try:
            self.logger.info("주가 원인 분석 서비스 시작")

            # 데이터베이스 초기화
            await self.initialize_database()

            # 종목 정보 로드
            with open(
                project_root / "config" / "stocks.json", "r", encoding="utf-8"
            ) as f:
                stocks_config = json.load(f)

            # 실행 루프
            while True:
                try:
                    # 장시간 체크 (09:00-15:30)
                    current_time = datetime.now().time()
                    market_open = datetime.strptime("09:00", "%H:%M").time()
                    market_close = datetime.strptime("15:30", "%H:%M").time()

                    if market_open <= current_time <= market_close:
                        # 장중: 활성 종목에 대해 급등락 분석
                        for stock_code, stock_info in stocks_config.items():
                            if stock_info.get("active", False):
                                await self.process_price_analysis(stock_code)

                        # 10분 대기
                        await asyncio.sleep(600)
                    else:
                        # 장외: 1시간 대기
                        self.logger.info("장외 시간 - 대기 중")
                        await asyncio.sleep(3600)

                except KeyboardInterrupt:
                    self.logger.info("서비스 중단 요청")
                    break
                except Exception as e:
                    self.logger.error(f"서비스 실행 오류: {e}")
                    await asyncio.sleep(60)  # 1분 대기 후 재시도

        except Exception as e:
            self.logger.error(f"주가 원인 분석 서비스 실행 실패: {e}")
            raise
        finally:
            # 리소스 정리
            self.mysql_client.close()
            self.vector_db.close()

# 서비스 인스턴스 생성 (지연 초기화)
analysis_service = None


def get_analysis_service():
    """주가 분석 서비스 인스턴스 반환 (지연 초기화)"""
    global analysis_service
    if analysis_service is None:
        analysis_service = PriceAnalysisService()
    return analysis_service

# FastAPI 엔드포인트
@app.get("/")
async def root():
    return {"message": "Price Analysis Service", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/analyze/{stock_code}")
async def analyze_stock_price(stock_code: str, background_tasks: BackgroundTasks):
    """특정 종목의 주가 분석 수동 실행"""
    background_tasks.add_task(get_analysis_service().process_price_analysis, stock_code)
    return {"message": f"Price analysis started for {stock_code}"}

@app.get("/stats")
async def get_analysis_stats():
    """주가 분석 통계"""
    try:
        today_count = await get_analysis_service().mysql_client.fetch_one_async(
            "SELECT COUNT(*) as count FROM price_analysis WHERE DATE(created_at) = CURDATE()"
        )
        
        high_change_count = await get_analysis_service().mysql_client.fetch_one_async(
            "SELECT COUNT(*) as count FROM price_analysis WHERE ABS(change_rate) >= 0.10"
        )
        
        return {
            "today_analysis_count": today_count["count"] if today_count else 0,
            "high_change_analysis_count": high_change_count["count"] if high_change_count else 0,
            "service_status": "running"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/{stock_code}")
async def get_stock_analysis(stock_code: str, limit: int = 10):
    """특정 종목의 분석 기록 조회"""
    try:
        analyses = await get_analysis_service().mysql_client.fetch_all_async(
            """
            SELECT analysis_date, change_rate, volume, analysis_type, confidence_score
            FROM price_analysis 
            WHERE stock_code = %s 
            ORDER BY analysis_date DESC 
            LIMIT %s
            """,
            (stock_code, limit)
        )
        
        return {
            "stock_code": stock_code,
            "analyses": analyses
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/current/{stock_code}")
async def get_current_price(stock_code: str):
    """현재 주가 정보 조회"""
    try:
        price_data = await get_analysis_service().get_current_price_data(stock_code)
        return {
            "stock_code": stock_code,
            "price_data": price_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def main():
    """메인 실행 함수"""
    try:
        # 주가 원인 분석 서비스를 백그라운드에서 실행
        import threading
        
        async def run_analysis_service():
            await get_analysis_service().run_service()
        
        # 서비스 스레드 시작
        service_thread = threading.Thread(target=lambda: asyncio.run(run_analysis_service()), daemon=True)
        service_thread.start()
        
        # FastAPI 서버 실행
        uvicorn.run(app, host="0.0.0.0", port=8005)

    except KeyboardInterrupt:
        print("서비스 중단")
    except Exception as e:
        print(f"서비스 실행 실패: {e}")


if __name__ == "__main__":
    asyncio.run(main())
