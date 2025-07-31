"""
뉴스 서비스 메인 모듈
- 뉴스 크롤링 및 분석
- 3단계 필터링 시스템 (SimHash → 종목관련성 → 벡터유사도)
- 고영향도 뉴스 감지 및 알림
- SkillStack 통합 완료
"""

import asyncio
import csv
import hashlib
import json
import logging
import os
import re
import time
import traceback
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path

import numpy as np
import requests
import schedule
import simhash
import uvicorn
# yfinance 제거 - pykrx로 대체
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sentence_transformers import SentenceTransformer
from webdriver_manager.chrome import ChromeDriverManager

# 프로젝트 모듈 import
import sys
import os

# Windows 유니코드 인코딩 설정
if os.name == 'nt':  # Windows
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 및 서비스 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
services_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, services_path)

from config.env_local import get_config, get_env_var, get_int_env_var
from shared.user_config.user_config_manager import user_config_manager
from shared.database.mysql_client import get_mysql_client
from shared.database.vector_db import VectorDBClient
from shared.llm.llm_manager import llm_manager
from shared.apis.telegram_api import TelegramBotClient
from shared.service_config.user_config_loader import get_config_loader

# 로컬 SimHash 모듈 import
try:
    from .enhanced_simhash import EnhancedSimHashFilter
except ImportError:
    # 직접 실행 시 절대 import 사용
    try:
        from enhanced_simhash import EnhancedSimHashFilter
    except ImportError:
        print("경고: EnhancedSimHashFilter를 찾을 수 없습니다.")
        EnhancedSimHashFilter = None

# 주가 추이 분석 서비스 import
try:
    from stock_trend_service import StockTrendService
except ImportError:
    try:
        from ..stock_trend_service import StockTrendService  
    except ImportError as e:
        print(f"경고: StockTrendService import 실패: {e}")
        StockTrendService = None

# 통계 모듈 import 제거됨

# 로깅 설정
# 🔧 수정: 로그 파일 경로를 절대 경로로 수정하고 더 안정적인 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(current_dir, 'logs')

# 로그 디렉토리 생성 (권한 문제 방지)
try:
    os.makedirs(log_dir, exist_ok=True)
    print(f"📁 로그 디렉토리 생성/확인: {log_dir}")
except Exception as e:
    print(f"⚠️ 로그 디렉토리 생성 실패: {e}")
    # 백업: 현재 디렉토리에 logs 폴더 생성
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    print(f"📁 백업 로그 디렉토리 사용: {log_dir}")

log_file_path = os.path.join(log_dir, 'news_service.log')

# 기존 핸들러 제거 (중복 방지)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ],
    force=True  # 기존 설정 덮어쓰기
)

logger = logging.getLogger(__name__)

# 로그 파일 경로 확인 및 출력
logger.info(f"📁 로그 파일 경로: {log_file_path}")
logger.info(f"📁 로그 디렉토리: {log_dir}")
logger.info(f"📁 로그 파일 존재 여부: {os.path.exists(log_file_path)}")

# 테스트 로그 메시지
logger.info("🚀 뉴스 서비스 로깅 시스템 초기화 완료")

# 글로벌 변수
app = FastAPI(title="News Crawling Service", version="1.0.0")

# 서비스 인스턴스 관리
news_service_instance = None
latest_signal_message = None  # 최근 알람 메시지 저장

# 독립적 스케줄링을 위한 마지막 실행 시간 추적
last_execution_time = None


def log_error_with_traceback(message: str, error: Exception, extra_info: Optional[Dict] = None):
    """에러와 함께 상세한 트레이스백 로깅"""
    error_details = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    if extra_info:
        error_details.update(extra_info)
    
    logger.error(f"{message}: {error_details}")

    
def log_performance(func_name: str, start_time: float, end_time: float, extra_info: Optional[Dict] = None):
    """성능 로깅"""
    duration = end_time - start_time
    perf_info = {
        "function": func_name,
        "duration_seconds": round(duration, 3),
        "timestamp": datetime.now().isoformat()
    }
    
    if extra_info:
        perf_info.update(extra_info)
    
    logger.debug(f"🚀 성능: {perf_info}")


class NaverStockAPI:
    """pykrx 기반 주식 정보 API (안전하고 빠른 버전)"""
    
    def __init__(self):
        try:
            from pykrx import stock
            self.stock = stock
            logger.info("✅ pykrx 라이브러리 로드 성공")
        except ImportError:
            logger.error("❌ pykrx 라이브러리가 설치되지 않았습니다. pip install pykrx를 실행하세요.")
            raise ImportError("pykrx 라이브러리가 필요합니다.")
        
    def get_stock_info(self, stock_code: str) -> Dict:
        """단일 종목의 주식 정보 조회 (pykrx 기반)"""
        try:
            logger.info(f"📊 pykrx로 주식 정보 조회 시작: {stock_code}")
            
            # 오늘 날짜
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            
            # 종목명 조회
            stock_name = self.stock.get_market_ticker_name(stock_code)
            if not stock_name:
                logger.warning(f"⚠️ 종목명을 찾을 수 없습니다: {stock_code}")
                stock_name = "알 수 없음"
            
            # 오늘 OHLCV 데이터 조회
            df = self.stock.get_market_ohlcv(today, today, stock_code)
            
            if df.empty:
                logger.warning(f"⚠️ 오늘 데이터가 없습니다. 어제 데이터로 대체: {stock_code}")
                # 어제 날짜로 재시도
                from datetime import timedelta
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                df = self.stock.get_market_ohlcv(yesterday, yesterday, stock_code)
                
                if df.empty:
                    logger.warning(f"⚠️ 어제 데이터도 없습니다: {stock_code}")
                    # 기본값 반환
                    return self._get_default_stock_info(stock_code, stock_name)
            
            # 데이터 추출
            row = df.iloc[0]
            
            # 현재가 계산 (종가 기준)
            current_price = int(row['종가'])
            
            # 등락률 계산
            change_rate = float(row['등락률'])
            
            # 전일 종가 계산
            prev_close = int(current_price / (1 + change_rate / 100))
            
            # 거래량 (거래대금은 별도 계산 필요)
            volume = int(row['거래량'])
            # 거래대금 = 거래량 * 종가 (근사값)
            trading_value = volume * current_price
            
            # 시가총액 조회 (전체 시장에서 필터링)
            try:
                # 전체 시장 시가총액 조회 후 해당 종목 필터링
                cap_df = self.stock.get_market_cap(today)
                if not cap_df.empty and stock_code in cap_df.index:
                    market_cap = int(cap_df.loc[stock_code, '시가총액'])
                    market_cap_formatted = self._format_market_cap(market_cap)
                else:
                    # 대안: 전체 시장에서 종목명으로 검색
                    stock_name_search = self.stock.get_market_ticker_name(stock_code)
                    if stock_name_search and not cap_df.empty:
                        # 종목명으로 검색
                        matching_rows = cap_df[cap_df.index.str.contains(stock_name_search, na=False)]
                        if not matching_rows.empty:
                            market_cap = int(matching_rows.iloc[0]['시가총액'])
                            market_cap_formatted = self._format_market_cap(market_cap)
                        else:
                            market_cap_formatted = "N/A"
                    else:
                        market_cap_formatted = "N/A"
            except Exception as e:
                logger.warning(f"⚠️ 시가총액 조회 실패: {e}")
                market_cap_formatted = "N/A"
            
            # PER 조회 (전체 시장에서 필터링)
            try:
                # 전체 시장 PER 조회 후 해당 종목 필터링
                fundamental_df = self.stock.get_market_fundamental(today)
                if not fundamental_df.empty and stock_code in fundamental_df.index:
                    per = float(fundamental_df.loc[stock_code, 'PER'])
                    per_formatted = f"{per:.2f}" if per > 0 else "N/A"
                else:
                    # 대안: 전체 시장에서 종목명으로 검색
                    stock_name_search = self.stock.get_market_ticker_name(stock_code)
                    if stock_name_search and not fundamental_df.empty:
                        # 종목명으로 검색
                        matching_rows = fundamental_df[fundamental_df.index.str.contains(stock_name_search, na=False)]
                        if not matching_rows.empty:
                            per = float(matching_rows.iloc[0]['PER'])
                            per_formatted = f"{per:.2f}" if per > 0 else "N/A"
                        else:
                            per_formatted = "N/A"
                    else:
                        per_formatted = "N/A"
            except Exception as e:
                logger.warning(f"⚠️ PER 조회 실패: {e}")
                per_formatted = "N/A"
            
            # 결과 구성
            stock_info = {
                "종목명": stock_name,
                "현재가": f"{current_price:,}",
                "등락률": f"{change_rate:+.2f}%",
                "전일": f"{prev_close:,}",
                "시가": f"{int(row['시가']):,}",
                "고가": f"{int(row['고가']):,}",
                "거래량": f"{volume:,}",
                "거래대금": f"{trading_value:,}",
                "시가총액": market_cap_formatted,
                "PER": per_formatted
            }
            
            logger.info(f"✅ 주식 정보 조회 완료: {stock_name} ({stock_code})")
            logger.debug(f"📊 조회된 정보: {stock_info}")
            
            return stock_info
            
        except Exception as e:
            logger.error(f"❌ pykrx 주식 정보 조회 실패: {e}")
            log_error_with_traceback("pykrx 주식 정보 조회 실패", e, {"stock_code": stock_code})
            return self._get_default_stock_info(stock_code, "알 수 없음")
    
    def _get_default_stock_info(self, stock_code: str, stock_name: str) -> Dict:
        """기본 주식 정보 반환"""
        return {
            "종목명": stock_name,
            "현재가": "N/A",
            "등락률": "N/A",
            "전일": "N/A",
            "시가": "N/A",
            "고가": "N/A",
            "거래량": "N/A",
            "거래대금": "N/A",
            "시가총액": "N/A",
            "PER": "N/A"
        }

    def _format_market_cap(self, market_cap: int) -> str:
        """시가총액 포맷팅"""
        if market_cap >= 1_000_000_000_000:  # 1조 이상
            return f"{market_cap / 1_000_000_000_000:.1f}조원"
        elif market_cap >= 1_000_000_000:  # 10억 이상
            return f"{market_cap / 1_000_000_000:.1f}억원"
        else:
            return f"{market_cap:,}원"
    
    def create_chrome_driver(self, headless: bool = True) -> None:
        """pykrx는 Selenium이 필요 없으므로 빈 메서드"""
        logger.debug("🔧 pykrx는 Selenium이 필요하지 않습니다.")
        pass


class NewsService:
    """뉴스 서비스 메인 클래스"""
    
    def __init__(self):
        """뉴스 서비스 초기화"""
        logger.info("🚀 NewsService 초기화 시작")
        
        try:
            # 설정 로드 (개발자 기본값)
            logger.debug("📋 설정 로드 중...")
            self.config = get_config()
            
            # 사용자 설정 관리자 초기화
            self.user_config_manager = user_config_manager
            self.current_user_id = os.environ.get('HYPERASSET_USER_ID', "1")  # 🔥 환경변수에서 사용자 ID 읽기
            
            # 사용자별 개인화 설정 로더 초기화
            self.user_config_loader = None  # 비동기로 초기화됨
            self.personalized_configs = {}  # 사용자별 개인화 설정 캐시
            logger.debug("✅ 설정 로드 완료")
            
            # HyperCLOVA API 키 읽기 및 LLM 클라이언트에 전달
            hyperclova_api_key = None
            hyperclova_api_url = None
            try:
                hyperclova_config = self.config.get("hyperclova", {})
                hyperclova_api_key = hyperclova_config.get("api_key")
                hyperclova_api_url = hyperclova_config.get("api_url")
                
                if not hyperclova_api_key:
                    logger.warning("⚠️ HyperCLOVA API 키가 설정에 없습니다. LLM 기능이 제한됩니다.")
                else:
                    logger.info(f"✅ HyperCLOVA API 키 로드 완료: {hyperclova_api_key[:10]}...")
                    logger.info(f"✅ HyperCLOVA API URL: {hyperclova_api_url}")
                    
            except Exception as e:
                logger.warning(f"⚠️ HyperCLOVA API 키 로드 실패: {e}")
                hyperclova_api_key = None
                hyperclova_api_url = None
            
            # 데이터베이스 클라이언트 초기화
            logger.debug("🗄️ MySQL 클라이언트 초기화 중...")
            self.mysql_client = get_mysql_client()
            logger.debug("✅ MySQL 클라이언트 초기화 완료")
            
            # Vector DB 클라이언트 초기화 (news_service 전용 경로 사용)
            logger.debug("🔍 Vector DB 클라이언트 초기화 중...")
            
            # news_service 전용 ChromaDB 경로 설정
            self.news_service_path = os.path.join(os.path.dirname(__file__), "data", "chroma")
            os.makedirs(self.news_service_path, exist_ok=True)
            
            # 환경변수 임시 설정
            original_chroma_path = os.environ.get("CHROMADB_PERSIST_DIRECTORY", None)
            os.environ["CHROMADB_PERSIST_DIRECTORY"] = self.news_service_path
            
            try:
                self.vector_db = VectorDBClient()
                logger.debug(f"✅ Vector DB 클라이언트 초기화 완료: {self.news_service_path}")
            finally:
                # 원래 환경변수 복원
                if original_chroma_path:
                    os.environ["CHROMADB_PERSIST_DIRECTORY"] = original_chroma_path
                elif "CHROMADB_PERSIST_DIRECTORY" in os.environ:
                    del os.environ["CHROMADB_PERSIST_DIRECTORY"]
            
            logger.debug("🤖 LLM 매니저 초기화 중...")
            self.llm_manager = llm_manager
            logger.debug("✅ LLM 매니저 초기화 완료")
            
            logger.debug("📱 Telegram Bot 클라이언트 초기화 중...")
            self.telegram_bot = TelegramBotClient()
            logger.debug("✅ Telegram Bot 클라이언트 초기화 완료")

            # 임베딩 모델 로드
            logger.debug("🧠 임베딩 모델 로드 중...")
            self.embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
            logger.debug("✅ 임베딩 모델 로드 완료")

            # Chrome Driver 관리
            logger.debug("🌐 Chrome Driver 설정 중...")
            self.driver = None
            self.driver_lock = Lock()
            self.driver_retry_count = 0
            self.max_driver_retries = 3
            self.chrome_options = None
            
            try:
                self.setup_chrome_driver()
                logger.debug("✅ Chrome Driver 설정 완료")
            except Exception as e:
                logger.warning(f"⚠️ Chrome Driver 설정 실패: {e}")
                # 기본 설정으로 재시도
                try:
                    self.chrome_options = Options()
                    self.chrome_options.add_argument("--headless")
                    self.chrome_options.add_argument("--no-sandbox")
                    self.chrome_options.add_argument("--disable-dev-shm-usage")
                    logger.info("✅ 기본 Chrome Driver 설정으로 재시도 완료")
                except Exception as e2:
                    logger.error(f"❌ 기본 Chrome Driver 설정도 실패: {e2}")
                    self.chrome_options = None

            # 크롤링 설정
            self.news_sources = [
                "https://finance.naver.com/news/news_list.naver?mode=LSS2&section_id=101&section_id2=258",
                "https://news.naver.com/main/list.naver?mode=LSD&mid=sec&sid1=101",
            ]

            # 중복 제거 임계값 (개발자 기본값)
            self.simhash_threshold = 3
            self.vector_similarity_threshold = self.config.get("NEWS_SIMILARITY_THRESHOLD", 1.1)
            self.impact_threshold = self.config.get("NEWS_IMPACT_THRESHOLD", 0.5)
            self.relevance_threshold = self.config.get("NEWS_RELEVANCE_THRESHOLD", 0.6)
            self.past_events_similarity_threshold = 0.5  # 과거 사례 유사도 임계값
            
            # 사용자별 설정 로드 (MySQL에서 덮어쓰기)
            # asyncio.create_task(self._load_user_settings())  # 이벤트 루프 실행 후 호출
            
            # 향상된 SimHash 필터 초기화
            logger.debug("🔧 SimHash 필터 초기화 중...")
            # SkillStack 중복 제거 필터 초기화
            try:
                if EnhancedSimHashFilter is not None:
                    self.simhash_filter = EnhancedSimHashFilter()
                    logger.info("✅ SkillStack SimHash 필터 초기화 완료")
                else:
                    logger.warning("⚠️ EnhancedSimHashFilter 클래스를 찾을 수 없음")
                    self.simhash_filter = None
            except Exception as e:
                logger.error(f"❌ SkillStack SimHash 필터 초기화 실패: {e}")
                self.simhash_filter = None

            # 종목 목록 로드
            logger.debug("📊 종목 목록 로드 중...")
            self.load_stock_codes()
            logger.debug("✅ 종목 목록 로드 완료")
            
            # 종목 정보 API 초기화
            logger.debug("📈 종목 정보 API 초기화 중...")
            self.stock_api = NaverStockAPI()
            logger.debug("✅ 종목 정보 API 초기화 완료")
            
            # 주가 추이 분석 서비스 초기화
            logger.debug("📊 주가 추이 분석 서비스 초기화 중...")
            if StockTrendService is not None:
                try:
                    self.stock_trend_service = StockTrendService()
                    logger.debug("✅ 주가 추이 분석 서비스 초기화 완료")
                except Exception as e:
                    logger.error(f"❌ 주가 추이 분석 서비스 초기화 실패: {e}")
                    self.stock_trend_service = None
            else:
                logger.warning("⚠️ StockTrendService import 실패로 주가 추이 분석 기능 비활성화")
                self.stock_trend_service = None

            # 성능 최적화를 위한 캐시 시스템
            self.embedding_cache = {}  # 임베딩 캐시
            self.similarity_cache = {}  # 유사도 캐시
            self.news_cache = []  # 현재 세션 뉴스 캐시
            self.cache_lock = Lock()

            # 통계 수집 시스템 초기화 제거됨

            # 데이터베이스 초기화
            logger.debug("🗄️ 데이터베이스 초기화 중...")
            self.init_database()
            logger.debug("✅ 데이터베이스 초기화 완료")
            
            # CSV 저장 설정
            logger.debug("📊 CSV 출력 시스템 초기화 중...")
            self.csv_output_dir = Path("output/csv")
            self.csv_output_dir.mkdir(parents=True, exist_ok=True)
            
            # CSV 파일 헤더
            self.csv_headers = [
                "timestamp", "stock_code", "stock_name", "title", "content", 
                "url", "source", "published_at", "impact_score", "reasoning",
                "relevance_score", "similarity_score", "filter_stage", 
                "current_price", "change_rate", "telegram_sent", "processing_time"
            ]
            
            # 일일 CSV 파일 초기화
            self.daily_csv_file = self.csv_output_dir / f"news_results_{datetime.now().strftime('%Y%m%d')}.csv"
            self.init_daily_csv()
            logger.debug("✅ CSV 출력 시스템 초기화 완료")
            
            logger.info("✅ NewsService 초기화 완료")
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ NewsService 초기화 실패 [{error_type}]: {e}")
            log_error_with_traceback("NewsService 초기화 실패", e)
            raise RuntimeError(f"NewsService 초기화 실패: {error_type} - {e}")

    async def _load_user_settings(self):
        """사용자별 설정 로드 (User Config Manager에서 중앙 집중식으로 가져오기)"""
        try:
            user_config = await self.user_config_manager.get_user_config(self.current_user_id)
            
            # 사용자별 임계값으로 덮어쓰기 (기본값은 config에서 유지)
            self.vector_similarity_threshold = user_config.get("news_similarity_threshold", self.vector_similarity_threshold)
            self.impact_threshold = user_config.get("news_impact_threshold", self.impact_threshold)
            
            # 사용자 종목 설정으로 덮어쓰기
            self.stocks_config = {}
            for stock in user_config.get("stocks", []):
                if stock.get("enabled", True):
                    self.stocks_config[stock["stock_code"]] = {
                        "name": stock["stock_name"],
                        "enabled": True
                    }
            
            logger.info(f"✅ 사용자 설정 로드 완료: {len(self.stocks_config)}개 종목, "
                       f"유사도임계값={self.vector_similarity_threshold}, "
                       f"영향도임계값={self.impact_threshold}")
            
        except Exception as e:
            logger.error(f"❌ 사용자 설정 로드 실패 (기본값 유지): {e}")
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
            logger.info(f"✅ 사용자 ID 설정 및 설정 재로드 완료: {user_id}")
        except Exception as e:
            logger.error(f"❌ 사용자 ID 설정 실패: {e}")
            raise

    def setup_chrome_driver(self):
        """Chrome Driver 설정 - 개선된 안정 버전"""
        try:
            self.chrome_options = Options()
            
            # 기본 안정성 옵션
            self.chrome_options.add_argument("--headless")
            self.chrome_options.add_argument("--no-sandbox")
            self.chrome_options.add_argument("--disable-dev-shm-usage")
            self.chrome_options.add_argument("--disable-gpu")
            self.chrome_options.add_argument("--window-size=1920,1080")
            self.chrome_options.add_argument("--disable-web-security")
            self.chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            self.chrome_options.add_argument("--disable-extensions")
            self.chrome_options.add_argument("--disable-plugins")
            self.chrome_options.add_argument("--disable-images")
            
            # 추가 안정성 옵션
            self.chrome_options.add_argument("--disable-background-timer-throttling")
            self.chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            self.chrome_options.add_argument("--disable-renderer-backgrounding")
            self.chrome_options.add_argument("--disable-ipc-flooding-protection")
            self.chrome_options.add_argument("--disable-default-apps")
            self.chrome_options.add_argument("--disable-sync")
            self.chrome_options.add_argument("--disable-translate")
            self.chrome_options.add_argument("--disable-logging")
            self.chrome_options.add_argument("--disable-notifications")
            self.chrome_options.add_argument("--disable-popup-blocking")
            
            # 메모리 최적화
            self.chrome_options.add_argument("--memory-pressure-off")
            self.chrome_options.add_argument("--max_old_space_size=4096")
            self.chrome_options.add_argument("--disable-javascript")
            
            # User Agent 설정
            self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # 자동화 감지 방지
            self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            self.chrome_options.add_experimental_option('useAutomationExtension', False)
            
            logger.info("✅ Chrome Driver 설정 완료")
            
        except Exception as e:
            logger.error(f"❌ Chrome Driver 설정 실패: {e}")
            # 기본 옵션으로 재시도
            try:
                self.chrome_options = Options()
                self.chrome_options.add_argument("--headless")
                self.chrome_options.add_argument("--no-sandbox")
                self.chrome_options.add_argument("--disable-dev-shm-usage")
                logger.info("✅ 기본 Chrome Driver 설정으로 재시도 완료")
            except Exception as e2:
                logger.error(f"❌ 기본 Chrome Driver 설정도 실패: {e2}")

    def get_driver(self):
        """Chrome Driver 인스턴스 가져오기 (재시도 로직 포함)"""
        with self.driver_lock:
            if self.driver is None or not self._is_driver_alive():
                try:
                    if self.driver:
                        try:
                            self.driver.quit()
                        except:
                            pass
                    
                    # ChromeDriverManager 설정 개선
                    try:
                        # chrome_options가 None인 경우 기본 설정 생성
                        if self.chrome_options is None:
                            self.chrome_options = Options()
                            self.chrome_options.add_argument("--headless")
                            self.chrome_options.add_argument("--no-sandbox")
                            self.chrome_options.add_argument("--disable-dev-shm-usage")
                            logger.info("✅ 기본 Chrome 옵션 생성")
                        
                        # 더 안정적인 드라이버 설치
                        driver_path = ChromeDriverManager().install()
                        logger.info(f"✅ Chrome Driver 설치 완료: {driver_path}")
                        
                        service = Service(driver_path)
                        
                        # Chrome 옵션 추가 개선 - 더 안정적인 설정
                        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                        self.chrome_options.add_argument("--disable-web-security")
                        self.chrome_options.add_argument("--allow-running-insecure-content")
                        self.chrome_options.add_argument("--disable-features=TranslateUI")
                        self.chrome_options.add_argument("--disable-ipc-flooding-protection")
                        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                        self.chrome_options.add_experimental_option('useAutomationExtension', False)
                        
                        # 메모리 사용량 최적화
                        self.chrome_options.add_argument("--memory-pressure-off")
                        self.chrome_options.add_argument("--max_old_space_size=4096")
                        
                        # 추가 안정성 옵션
                        self.chrome_options.add_argument("--disable-background-timer-throttling")
                        self.chrome_options.add_argument("--disable-backgrounding-occluded-windows")
                        self.chrome_options.add_argument("--disable-renderer-backgrounding")
                        
                        # Chrome Driver 생성 시 더 긴 타임아웃 설정
                        self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
                        self.driver.set_page_load_timeout(60)  # 30초 → 60초로 증가
                        self.driver.implicitly_wait(15)        # 10초 → 15초로 증가
                        
                        # 브라우저 창 크기 설정
                        self.driver.set_window_size(1920, 1080)
                        
                        # 자동화 감지 방지
                        try:
                            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        except Exception as e:
                            logger.debug(f"자동화 감지 방지 스크립트 실행 실패: {e}")
                        
                        self.driver_retry_count = 0
                        logger.info("✅ Chrome Driver 생성 완료")
                        
                    except Exception as e:
                        logger.error(f"❌ ChromeDriverManager 설치 실패: {e}")
                        
                        # 대안: 시스템에 설치된 Chrome 드라이버 사용
                        try:
                            logger.info("🔄 시스템 Chrome 드라이버 사용 시도...")
                            self.driver = webdriver.Chrome(options=self.chrome_options)
                            self.driver.set_page_load_timeout(30)
                            self.driver.implicitly_wait(10)
                            self.driver_retry_count = 0
                            logger.info("✅ 시스템 Chrome 드라이버 사용 성공")
                        except Exception as e2:
                            logger.error(f"❌ 시스템 Chrome 드라이버도 실패: {e2}")
                            raise e2
                    
                except Exception as e:
                    self.driver_retry_count += 1
                    logger.error(f"❌ Chrome Driver 생성 실패 ({self.driver_retry_count}/{self.max_driver_retries}): {e}")
                    
                    # 상세 오류 정보 로깅
                    error_msg = str(e).lower()
                    if "can not connect to the service" in error_msg:
                        logger.error("🔧 해결방법: Chrome 브라우저를 업데이트하거나 시스템을 재부팅해보세요")
                    elif "permission denied" in error_msg:
                        logger.error("🔧 해결방법: Chrome Driver 실행 권한을 확인하세요")
                    elif "chromedriver" in error_msg:
                        logger.error("🔧 해결방법: ChromeDriver를 수동으로 설치하거나 PATH에 추가하세요")
                    elif "session not created" in error_msg:
                        logger.error("🔧 해결방법: Chrome 브라우저 버전과 드라이버 버전이 일치하지 않습니다")
                    elif "no such file or directory" in error_msg:
                        logger.error("🔧 해결방법: Chrome 브라우저가 설치되어 있는지 확인하세요")
                    elif "timeout" in error_msg:
                        logger.error("🔧 해결방법: 네트워크 연결을 확인하고 다시 시도해보세요")
                    else:
                        logger.error(f"🔧 알 수 없는 Chrome Driver 오류: {e}")
                    
                    if self.driver_retry_count >= self.max_driver_retries:
                        logger.error("❌ Chrome Driver 생성 최대 재시도 횟수 초과 - requests 기반 크롤링으로 대체")
                        # 크롬드라이버 관련 변수 정리
                        self.driver = None
                        self.chrome_options = None
                        return None
                    
                    # 재시도 전 대기 (지수 백오프)
                    wait_time = min(2 ** self.driver_retry_count, 30)  # 최대 30초로 제한
                    logger.info(f"⏳ {wait_time}초 후 재시도...")
                    time.sleep(wait_time)
                    return self.get_driver()
            
            return self.driver

    def _is_driver_alive(self):
        """Chrome Driver 생존 여부 확인 (개선된 버전)"""
        try:
            if self.driver:
                # 간단한 명령으로 드라이버 상태 확인
                self.driver.current_url
                return True
        except (WebDriverException, Exception) as e:
            logger.debug(f"Chrome Driver 상태 확인 실패: {e}")
            return False
        return False

    def close_driver(self):
        """Chrome Driver 종료 (개선된 버전)"""
        with self.driver_lock:
            if self.driver:
                try:
                    # 모든 창 닫기
                    self.driver.quit()
                    logger.info("✅ Chrome Driver 종료 완료")
                except Exception as e:
                    logger.warning(f"⚠️ Chrome Driver 종료 중 오류: {e}")
                    try:
                        # 강제 종료 시도
                        self.driver.close()
                    except:
                        pass
                finally:
                    self.driver = None
                    self.driver_retry_count = 0

    def init_database(self):
        """데이터베이스 초기화"""
        try:
            # 벡터 DB 상태 확인 (컬렉션은 VectorDBClient에서 이미 생성됨)
            health_status = self.vector_db.health_check()
            
            if health_status["status"] == "healthy":
                logger.info("✅ 벡터 DB 상태 확인 완료")
                for collection_name, status in health_status["collections"].items():
                    if status["status"] == "healthy":
                        logger.debug(f"✅ 컬렉션 '{collection_name}' 정상 (문서 {status['count']}개)")
                    else:
                        logger.warning(f"⚠️ 컬렉션 '{collection_name}' 상태 이상: {status.get('error', 'Unknown')}")
            else:
                logger.error(f"❌ 벡터 DB 상태 이상: {health_status.get('error', 'Unknown')}")
            
            logger.info("✅ 뉴스 서비스 데이터베이스 초기화 완료")

        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 실패: {e}")

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

    def is_market_open(self) -> bool:
        """장중 여부 확인"""
        now = datetime.now()
        if now.weekday() >= 5:
            return False

        market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

        return market_open <= now <= market_close

    def get_cached_embedding(self, text: str) -> Optional[np.ndarray]:
        """캐시된 임베딩 조회"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        with self.cache_lock:
            return self.embedding_cache.get(text_hash)

    def cache_embedding(self, text: str, embedding: np.ndarray):
        """임베딩 캐시 저장"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        with self.cache_lock:
            self.embedding_cache[text_hash] = embedding
            
            # 캐시 크기 제한 (1000개)
            if len(self.embedding_cache) > 1000:
                # 가장 오래된 항목 삭제
                oldest_key = next(iter(self.embedding_cache))
                del self.embedding_cache[oldest_key]

    def calculate_simhash(self, text: str) -> int:
        """SimHash 계산"""
        try:
            tokens = text.split()
            token_hashes = []
            for token in tokens:
                hash_value = int(hashlib.md5(token.encode()).hexdigest(), 16)
                token_hashes.append(hash_value)

            if token_hashes:
                simhash_obj = simhash.Simhash(token_hashes)
                return int(simhash_obj.value) if simhash_obj.value is not None else 0

        except Exception as e:
            logger.error(f"SimHash 계산 실패: {e}")

        return 0

    def build_news_url(self, item: Dict) -> str:
        """뉴스 URL 생성 (SkillStack 방식)"""
        # linkUrl 우선, 없으면 officeId/articleId 조합
        if item.get("linkUrl"):
            return item["linkUrl"]
        if item.get("url"):
            return item["url"]
        if item.get("officeId") and item.get("articleId"):
            return f"https://n.news.naver.com/article/{item['officeId']}/{item['articleId']}"
        return ""
    
    def format_news_date(self, dt: str) -> datetime:
        """뉴스 날짜 포맷팅 (SkillStack 방식)"""
        try:
            return datetime.strptime(dt, "%Y%m%d%H%M")
        except Exception:
            return datetime.now()
    
    def get_stock_info_for_code(self, stock_code: str) -> Dict:
        """종목 정보 수집 (SkillStack 방식) - 4단계 준비"""
        try:
            logger.debug(f"📊 종목 정보 수집 시작: {stock_code}")
            
            stock_info = self.stock_api.get_stock_info(stock_code)
            stock_info["종목코드"] = stock_code
            
            if stock_info.get("종목명"):
                # 상세 정보 로깅
                stock_name = stock_info.get("종목명", "")
                current_price = stock_info.get("현재가", "")
                change_rate = stock_info.get("등락률", "")
                trading_volume = stock_info.get("거래량", "")
                trading_value = stock_info.get("거래대금", "")
                market_cap = stock_info.get("시가총액", "")
                per_ratio = stock_info.get("PER", "")
                
                logger.debug(f"📈 기본정보: {stock_name} ({stock_code})")
                logger.debug(f"💰 가격정보: 현재가={current_price}, 등락률={change_rate}")
                logger.debug(f"📊 거래정보: 거래량={trading_volume}, 거래대금={trading_value}")
                logger.debug(f"📊 기업정보: 시가총액={market_cap}, PER={per_ratio}")
                
                logger.info(f"✅ 종목 정보 수집 완료: {stock_name} - 현재가: {current_price}")
                logger.debug(f"🔮 4단계 준비: 종목 정보 완전 수집 완료 - DB 저장 준비됨")
            else:
                logger.warning(f"⚠️ 종목 정보 수집 부분 실패: {stock_code}")
                logger.debug(f"🔮 4단계 준비: 종목 정보 부분 실패 - 기본값으로 처리")
                
            return stock_info
            
        except Exception as e:
            logger.error(f"❌ 종목 정보 수집 실패: {e}")
            log_error_with_traceback("종목 정보 수집 실패", e, {"stock_code": stock_code})
            logger.debug(f"🔮 4단계 준비: 종목 정보 수집 실패 - 에러 처리 및 기본값 반환")
            return {
                "종목코드": stock_code,
                "종목명": "", "현재가": "", "등락률": "", "전일": "", "시가": "", "고가": "",
                "거래량": "", "거래대금": "", "시가총액": "", "PER": ""
            }
    
    async def check_three_stage_filtering(self, news_item: Dict) -> Tuple[bool, str, Dict]:
        """3단계 필터링 시스템 (SimHash → 종목관련성 → 벡터유사도)"""
        start_time = time.time()
        filter_result = {
            "stage1_simhash": False,
            "stage2_relevance": False,
            "stage3_vector": False,
            "final_pass": False,
            "details": {}
        }
        
        try:
            # 1단계: SimHash 기반 중복 제거 (SkillStack 방식)
            if self.simhash_filter:
                # SimHash 계산 및 중복 검사
                title_content = f"{news_item.get('title', '')} {news_item.get('content', '')}"
                is_duplicate = self.simhash_filter.is_duplicate(title_content)
                
                if is_duplicate:
                    logger.debug(f"🔄 SimHash 중복 뉴스 필터링: {news_item.get('title', '')[:50]}...")
                    return False, "SimHash 중복", {"simhash_duplicate": True}
                
                logger.debug("✅ SimHash 중복 검사 통과")
            else:
                logger.debug("⚠️ SimHash 필터 비활성화 상태")
            
            # 2단계: 종목 관련성 평가 (비활성화 - 모든 뉴스 통과)
            logger.debug(f"🔍 2단계: 종목 관련성 검사 (비활성화됨 - 모든 뉴스 통과)")
            
            # 관련성 계산 스킵 - 항상 통과 처리
            relevance_score = 1.0
            reasoning = "관련성 검사 비활성화됨"
            
            filter_result["details"]["relevance_score"] = relevance_score
            filter_result["details"]["relevance_reasoning"] = reasoning
            
            logger.debug(f"✅ 2단계 자동 통과: 종목 관련성 검사 스킵됨")
            
            # === 3단계: 벡터 유사도 중복 검사 ===
            logger.debug(f"🔍 3단계: 벡터 유사도 중복 검사 시작")
            is_vector_duplicate, similarity_score, similar_news = self.check_vector_similarity(news_item)
            
            filter_result["details"]["vector_similarity"] = similarity_score
            filter_result["details"]["similar_news"] = similar_news
            
            if is_vector_duplicate:
                logger.info(f"❌ 3단계 필터링: 벡터 유사도 중복 감지 - '{news_item['title'][:50]}...' (유사도: {similarity_score:.3f})")
                filter_result["stage3_vector"] = True
                return True, "vector_duplicate", filter_result
            
            logger.debug(f"✅ 3단계 통과: 벡터 유사도 중복 없음")
            
            # === 모든 단계 통과 ===
            filter_result["final_pass"] = True
            self.news_cache.append(news_item)
            
            log_performance("check_three_stage_filtering", start_time, time.time(), {
                "news_title": news_item["title"][:50],
                "relevance_score": relevance_score,
                "vector_similarity": similarity_score,
                "cache_size": len(self.news_cache)
            })
            
            logger.info(f"✅ 모든 단계 통과: '{news_item['title'][:50]}...' (관련성: {relevance_score:.3f})")
            return False, "passed", filter_result
            
        except Exception as e:
            log_error_with_traceback("3단계 필터링 시스템 실패", e, {
                "news_title": news_item.get("title", "Unknown"),
                "news_url": news_item.get("url", "Unknown"),
                "filter_result": filter_result
            })
            return False, "error", filter_result
    
    async def _call_llm_with_retry(self, prompt: str, max_retries: int = 3, base_delay: float = 2.0) -> Optional[str]:
        """LLM API 호출 재시도 로직"""
        for attempt in range(max_retries):
            try:
                logger.debug(f"🤖 LLM API 호출 시도 {attempt + 1}/{max_retries}")
                
                response = await self.llm_manager.generate_response(self.current_user_id, prompt)
                
                if response and response.strip():
                    logger.debug(f"✅ LLM API 호출 성공 (시도 {attempt + 1})")
                    return response
                else:
                    logger.warning(f"⚠️ LLM API 응답이 비어있음 (시도 {attempt + 1})")
                    
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"⚠️ LLM API 호출 실패 (시도 {attempt + 1}): {e}")
                
                # 호출 제한 관련 오류인지 확인
                is_rate_limit = any(keyword in error_msg for keyword in [
                    'rate limit', 'too many requests', '429', 'quota exceeded', 
                    'limit exceeded', 'throttle', 'throttling'
                ])
                
                if is_rate_limit:
                    # 지수 백오프로 대기 시간 계산
                    wait_time = base_delay * (2 ** attempt)
                    logger.info(f"⏳ 호출 제한 감지. {wait_time}초 대기 후 재시도...")
                    await asyncio.sleep(wait_time)
                else:
                    # 일반 오류는 짧은 대기 후 재시도
                    wait_time = base_delay * (1.5 ** attempt)
                    logger.info(f"⏳ 일반 오류. {wait_time}초 대기 후 재시도...")
                    await asyncio.sleep(wait_time)
                
                if attempt == max_retries - 1:
                    logger.error(f"❌ LLM API 최대 재시도 횟수 초과")
                    return None
        
        return None

    async def evaluate_stock_relevance(self, news_item: Dict) -> Tuple[bool, float, str]:
        """종목 관련성 평가 (LLM 기반)"""
        try:
            title = news_item.get('title', '')
            content = news_item.get('content', '')[:1000]  # 1000자로 제한
            stock_code = news_item.get('stock_code', '')
            stock_name = self.stock_names.get(stock_code, stock_code)
            
            if not stock_name or not title.strip():
                return True, 1.0, "종목명 또는 제목 정보 없음"
            
            prompt = f"""
당신은 한국 증권시장 전문가입니다. 
다음 뉴스가 해당 종목과 관련이 있는지 평가해주세요.
반드시 분석 대상 종목과 관련성을 고려하세요.

분석 대상 종목: {stock_name} (종목코드: {stock_code})

뉴스 제목: {title}
뉴스 본문: {content}

평가 기준:
1. 기업명 직접 언급: 해당 종목이 직접 언급되는가?
2. 업종 관련성: 해당 종목의 주요 사업 분야와 관련이 있는가?
3. 계열사/자회사: 해당 종목의 계열사나 자회사 관련 뉴스인가?
4. 시장 영향: 해당 종목에 직간접적 영향을 미칠 수 있는가?

관련성 점수: 0.0~1.0 (0.0=완전 무관, 0.5=간접 관련, 1.0=직접 관련)
판단 기준: 0.5 이상이면 관련, 미만이면 무관

응답 형식:
관련성: 0.XX
판단근거: 한 줄 설명
"""
            
            response = await self._call_llm_with_retry(prompt)
            
            # 기본값 설정
            relevance_score = 0.5
            reasoning = "평가 실패"
            
            # 응답 파싱
            if response:
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('관련성:'):
                        try:
                            score_match = re.search(r'[\d.]+', line)
                            if score_match:
                                relevance_score = float(score_match.group())
                                relevance_score = max(0.0, min(1.0, relevance_score))
                        except (ValueError, AttributeError):
                            pass
                    elif line.startswith('판단근거:'):
                        reasoning = line.replace('판단근거:', '').strip() or "평가 실패"
            
            # 관련성 점수 기반 최종 판단
            is_relevant = relevance_score >= self.relevance_threshold
            
            return is_relevant, relevance_score, reasoning
            
        except Exception as e:
            logger.error(f"종목 관련성 평가 실패: {e}")
            log_error_with_traceback("종목 관련성 평가 실패", e, {
                "stock_code": stock_code,
                "title": title[:50] if title else "No title"
            })
            return True, 0.5, f"평가 실패: {str(e)}"
    
    def check_vector_similarity(self, news_item: Dict) -> Tuple[bool, float, Optional[str]]:
        """벡터 유사도 중복 검사"""
        try:
            current_text = news_item.get("title", "") + " " + news_item.get("content", "")
            
            if not current_text.strip():
                logger.warning("뉴스 텍스트가 비어있음")
                return False, 0.0, None
            
            # 1. 세션 캐시와 비교
            current_embedding = self.get_cached_embedding(current_text)
            if current_embedding is None:
                current_embedding = self.embedding_model.encode([current_text])[0]
                self.cache_embedding(current_text, current_embedding)
            
            max_similarity = 0.0
            similar_news_title: Optional[str] = None
            
            # 캐시된 뉴스와 비교
            for cached_news in self.news_cache:
                cached_title = cached_news.get("title", "")
                cached_content = cached_news.get("content", "")
                cached_text = cached_title + " " + cached_content
                
                if not cached_text.strip():
                    continue
                    
                cached_embedding = self.get_cached_embedding(cached_text)
                
                if cached_embedding is None:
                    cached_embedding = self.embedding_model.encode([cached_text])[0]
                    self.cache_embedding(cached_text, cached_embedding)
                
                # 코사인 유사도 계산
                similarity = np.dot(current_embedding, cached_embedding) / (
                    np.linalg.norm(current_embedding) * np.linalg.norm(cached_embedding)
                )
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    similar_news_title = cached_title
                
                if similarity >= self.vector_similarity_threshold:
                    return True, similarity, cached_title
            
            # 2. 데이터베이스와 비교
            db_duplicate, db_similarity, db_title = False, 0.0, None  # ❌ MySQL 복잡한 중복 체크 제거
            if db_duplicate:
                return True, db_similarity, db_title
            
            return False, max_similarity, similar_news_title
            
        except Exception as e:
            logger.error(f"벡터 유사도 검사 실패: {e}")
            log_error_with_traceback("벡터 유사도 검사 실패", e, {
                "news_title": news_item.get("title", "")[:50]
            })
            return False, 0.0, None
    
    def check_database_duplicate(self, news_item: Dict) -> Tuple[bool, float, Optional[str]]:
        """❌ 단순화: 복잡한 MySQL 중복 검사 제거 - ChromaDB 벡터 유사도로 대체"""
        return False, 0.0, None

    def crawl_naver_finance_news(self, stock_code: str, pages: int = 1, size: int = 3) -> List[Dict]:
        """네이버 모바일 API를 통한 뉴스 크롤링 (SkillStack 완전 통합 방식)"""
        news_list = []
        start_time = time.time()
        
        try:
            logger.info(f"🚀 네이버 모바일 API 뉴스 크롤링 시작: {stock_code} (최대 {pages}페이지, 페이지당 {size}개)")
            
            # 모바일 API URL 구성
            api_url = f"https://m.stock.naver.com/api/news/stock/{stock_code}"
            
            # 헤더 설정 (SkillStack 방식)
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': f'https://m.stock.naver.com/domestic/stock/{stock_code}/news',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            total_available = None
            
            # 페이지별 크롤링
            for page in range(1, pages + 1):
                max_retries = 3  # 최대 재시도 횟수
                retry_delay = 2   # 재시도 간격 (초)
                
                for retry in range(max_retries):
                    try:
                        logger.info(f"📄 페이지 {page}/{pages} 크롤링 중... (시도 {retry + 1}/{max_retries})")
                        
                        # API 요청 파라미터
                        params = {
                            'page': page,
                            'size': size
                        }
                        
                        # API 호출 (재시도 로직 포함)
                        response = requests.get(api_url, headers=headers, params=params, timeout=10)
                        
                        # HTTP 상태 코드 확인
                        if response.status_code == 429:  # Too Many Requests
                            wait_time = retry_delay * (2 ** retry)  # 지수 백오프
                            logger.warning(f"⚠️ API 호출 제한 감지 (429). {wait_time}초 대기 후 재시도...")
                            time.sleep(wait_time)
                            continue
                        elif response.status_code == 403:  # Forbidden
                            wait_time = retry_delay * (2 ** retry) + 5  # 추가 대기
                            logger.warning(f"⚠️ API 접근 거부 (403). {wait_time}초 대기 후 재시도...")
                            time.sleep(wait_time)
                            continue
                        elif response.status_code != 200:
                            logger.error(f"❌ API 응답 오류: {response.status_code}")
                            if retry < max_retries - 1:
                                time.sleep(retry_delay)
                                continue
                            else:
                                break
                        
                        response.raise_for_status()
                        data = response.json()
                        page_news_count = 0
                        
                        # API 응답 구조 분석 및 처리
                        logger.debug(f"🔍 API 응답 구조 분석: {type(data)}")
                        
                        # 다양한 응답 구조 처리
                        items = []
                        total_count = "알 수 없음"
                        
                        if isinstance(data, list):
                            # 리스트 형태 응답 처리
                            logger.debug(f"📋 리스트 형태 응답: 길이 {len(data)}")
                            for entry in data:
                                if isinstance(entry, dict):
                                    # 첫 번째 페이지에서 총 개수 정보 추출
                                    if page == 1 and total_available is None:
                                        total_count = entry.get("totalCount", entry.get("total", "알 수 없음"))
                                        total_available = total_count
                                        current_items = entry.get("items", [])
                                        logger.info(f"📈 API 정보: 총 {total_count}개 뉴스 | 현재 페이지: {len(current_items)}개")
                                    
                                    # items 추출
                                    entry_items = entry.get("items", [])
                                    if entry_items:
                                        items.extend(entry_items)
                        elif isinstance(data, dict):
                            # 딕셔너리 형태 응답 처리
                            logger.debug(f"📋 딕셔너리 형태 응답: 키 {list(data.keys())}")
                            
                            # 첫 번째 페이지에서 총 개수 정보 추출
                            if page == 1 and total_available is None:
                                total_count = data.get("totalCount", data.get("total", "알 수 없음"))
                                total_available = total_count
                                current_items = data.get("items", [])
                                logger.info(f"📈 API 정보: 총 {total_count}개 뉴스 | 현재 페이지: {len(current_items)}개")
                            
                            # items 추출
                            items = data.get("items", [])
                        else:
                            logger.error(f"❌ 예상치 못한 API 응답 구조: {type(data)}")
                            continue
                        
                        # size 파라미터에 따라 아이템 수 제한
                        if size and len(items) > size:
                            items = items[:size]
                            logger.info(f"📊 요청된 크기({size}개)에 맞춰 {len(items)}개로 제한")
                        
                        # 뉴스 아이템 처리
                        for item in items:
                            if not isinstance(item, dict):
                                logger.debug(f"⏭️ 유효하지 않은 아이템 타입: {type(item)}")
                                continue
                                
                            # type 필드 확인 (1: 일반 기사, 2: 공시 등)
                            item_type = item.get("type", 1)
                            if item_type != 1:  # 일반 기사만
                                logger.debug(f"⏭️ 일반 기사가 아님 (type: {item_type}), 건너뜀")
                                continue
                            
                            page_news_count += 1
                            
                            # URL 생성 (SkillStack 방식)
                            url = self.build_news_url(item)
                            if not url:
                                logger.debug(f"⏭️ URL 생성 실패, 건너뜀")
                                continue
                            
                            # 날짜 포맷팅 (SkillStack 방식)
                            published_at = self.format_news_date(item.get("datetime", ""))
                            
                            title = item.get("title", "").strip()
                            if not title:
                                logger.debug(f"⏭️ 제목 없음, 건너뜀")
                                continue
                            
                            logger.debug(f"📰 뉴스 발견: '{title[:50]}...' -> {url}")
                            
                            # 뉴스 아이템 생성 (SkillStack 방식)
                            news_item = {
                                "title": title,
                                "url": url,
                                "published_at": published_at,
                                "stock_code": stock_code,
                                "source": item.get("source", ""),
                                "summary": item.get("summary", ""),
                                "content": "",  # 나중에 별도로 추출
                                "simhash": 0,
                                "created_at": datetime.now()
                            }
                            
                            news_list.append(news_item)
                            
                            # 본문 추출 (선택적)
                            content = self.get_news_content(url)
                            if content:
                                news_item["content"] = content
                            
                            time.sleep(0.5)  # 본문 추출 간격
                            
                        logger.info(f"✅ 페이지 {page} 완료: {page_news_count}개 수집 (누적: {len(news_list)}개)")
                        time.sleep(0.2)  # API 호출 간격
                        break  # 성공 시 재시도 루프 종료
                        
                    except requests.exceptions.RequestException as e:
                        logger.error(f"❌ API 요청 실패 (페이지 {page}, 시도 {retry + 1}): {e}")
                        if retry < max_retries - 1:
                            wait_time = retry_delay * (2 ** retry)
                            logger.info(f"⏳ {wait_time}초 후 재시도...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"❌ 페이지 {page} 최대 재시도 횟수 초과")
                    except Exception as e:
                        logger.error(f"❌ 페이지 {page} 처리 실패 (시도 {retry + 1}): {e}")
                        if retry < max_retries - 1:
                            wait_time = retry_delay * (2 ** retry)
                            logger.info(f"⏳ {wait_time}초 후 재시도...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"❌ 페이지 {page} 최대 재시도 횟수 초과")
                            break

        except Exception as e:
            logger.error(f"❌ 네이버 모바일 API 뉴스 크롤링 실패: {e}")
            log_error_with_traceback("네이버 모바일 API 뉴스 크롤링 실패", e, {
                "stock_code": stock_code,
                "api_url": api_url
            })
        
        processing_time = time.time() - start_time
        logger.info(f"🏁 종목 {stock_code} API 크롤링 완료: {len(news_list)}개 수집 (처리시간: {processing_time:.2f}초)")
        return news_list

    def get_news_content(self, url: str) -> Optional[str]:
        """뉴스 상세 내용 가져오기 (Chrome Driver + Requests 이중화)"""
        if not url:
            return None
        
        try:
            start_time = time.time()
            
            # 1차 시도: Chrome Driver 방식
            try:
                driver = self.get_driver()
                if driver:
                    content = self._get_content_with_chrome(driver, url, start_time)
                    if content:
                        return content
                    logger.warning("Chrome Driver로 본문 추출 실패, requests로 시도...")
                else:
                    logger.warning("Chrome Driver 초기화 실패, requests로 직접 시도...")
            except Exception as e:
                logger.warning(f"Chrome Driver 사용 중 오류 발생: {e}, requests로 전환...")
            
            # 2차 시도: Requests 기반 방식 (Chrome Driver 실패 시)
            try:
                return self._get_content_with_requests(url, start_time)
            except Exception as e:
                logger.error(f"❌ Requests 기반 본문 추출도 실패: {e}")
                return None
            
        except Exception as e:
            logger.error(f"❌ 뉴스 본문 추출 완전 실패: {e}")
            return None

    def _get_content_with_chrome(self, driver, url: str, start_time: float) -> Optional[str]:
        """Chrome Driver를 사용한 본문 추출 (개선된 버전)"""
        try:
            logger.debug(f"📄 Chrome Driver 본문 추출 시작: {url[:80]}...")
            
            # 페이지 접근 시도
            try:
                driver.get(url)
            except Exception as e:
                logger.warning(f"❌ Chrome Driver 페이지 접근 실패: {e}")
                return None
            
            # 페이지 로딩 대기 (더 안정적인 방식)
            try:
                # 먼저 body 요소가 있는지 확인
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 추가로 페이지가 완전히 로드될 때까지 대기
                WebDriverWait(driver, 5).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                logger.debug("✅ Chrome Driver 페이지 로딩 완료")
            except TimeoutException:
                logger.warning(f"⏰ Chrome Driver 페이지 로딩 시간 초과: {url}")
                # 로딩이 실패해도 계속 진행 (일부 내용이라도 추출)
                pass

            # 추가 렌더링 대기
            time.sleep(2)
            
            # 네이버 뉴스 본문 추출을 위한 선택자들 (확장)
            selectors = [
                "div#newsct_article .newsct_article._article_body",
                "article#dic_area.go_trans._article_content", 
                "div#articleBodyContents",
                "div#newsct_article",
                ".article_body",
                "#content",
                ".article-content",
                ".news-content",
                ".content",
                "div.article_body",
                "div.article-content",
                "div.content",
                "article",
                "div[class*='article']",
                "div[class*='content']",
                "div[class*='news']"
            ]
            
            # 각 선택자로 본문 추출 시도
            for i, selector in enumerate(selectors):
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element and element.text.strip():
                            text = self._clean_news_text(element.text.strip())
                            
                            if len(text) > 30:  # 더 짧은 텍스트도 허용
                                processing_time = time.time() - start_time
                                logger.debug(f"✅ Chrome Driver 본문 추출 성공: 길이 {len(text)}자, 처리시간 {processing_time:.2f}초")
                                return text[:10000]
                            
                except (NoSuchElementException, TimeoutException):
                    continue
                except Exception as e:
                    logger.debug(f"Chrome Driver 선택자 {i+1}번 오류: {e}")
                    continue
            
            # 마지막 시도: 전체 body 텍스트에서 추출
            try:
                body_element = driver.find_element(By.TAG_NAME, "body")
                if body_element and body_element.text.strip():
                    text = self._clean_news_text(body_element.text.strip())
                    if len(text) > 100:  # body 텍스트는 더 긴 경우만
                        processing_time = time.time() - start_time
                        logger.debug(f"✅ Chrome Driver body 텍스트 추출 성공: 길이 {len(text)}자, 처리시간 {processing_time:.2f}초")
                        return text[:10000]
            except Exception as e:
                logger.debug(f"Chrome Driver body 텍스트 추출 실패: {e}")
            
            return None
            
        except Exception as e:
            logger.warning(f"Chrome Driver 본문 추출 실패: {e}")
            return None

    def _get_content_with_requests(self, url: str, start_time: float) -> Optional[str]:
        """Requests를 사용한 본문 추출 (Chrome Driver 대체)"""
        try:
            logger.debug(f"📄 Requests 본문 추출 시작: {url[:80]}...")
            
            # Requests 기반 크롤링 헤더
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            }
            
            # HTTP 요청
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 인코딩 설정
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                response.encoding = 'utf-8'
            
            html_content = response.text
            
            # BeautifulSoup 사용하여 본문 추출
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 네이버 뉴스 및 일반 뉴스 선택자들
            selectors = [
                {'selector': 'div#newsct_article', 'attr': 'text'},
                {'selector': 'article#dic_area', 'attr': 'text'},
                {'selector': 'div#articleBodyContents', 'attr': 'text'},
                {'selector': '.article_body', 'attr': 'text'},
                {'selector': '.article-content', 'attr': 'text'},
                {'selector': '.news-content', 'attr': 'text'},
                {'selector': '#content', 'attr': 'text'}
            ]
            
            # 각 선택자로 본문 추출 시도
            for i, sel_info in enumerate(selectors):
                try:
                    element = soup.select_one(sel_info['selector'])
                    if element:
                        # 스크립트, 스타일 태그 제거
                        for script in element(["script", "style", "nav", "header", "footer", "aside"]):
                            script.decompose()
                        
                        text = element.get_text(strip=True)
                        if text:
                            text = self._clean_news_text(text)
                            
                            if len(text) > 50:
                                processing_time = time.time() - start_time
                                logger.debug(f"✅ Requests 본문 추출 성공: 길이 {len(text)}자, 처리시간 {processing_time:.2f}초")
                                return text[:10000]
                                
                except Exception as e:
                    logger.debug(f"Requests 선택자 {i+1}번 오류: {e}")
                    continue
            
            # 마지막 시도: 모든 p 태그 수집
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                if text:
                    text = self._clean_news_text(text)
                    if len(text) > 50:
                        processing_time = time.time() - start_time
                        logger.debug(f"✅ Requests p태그 본문 추출 성공: 길이 {len(text)}자, 처리시간 {processing_time:.2f}초")
                        return text[:10000]
            
            logger.warning(f"Requests로 본문 추출 실패: {url}")
            return None
            
        except Exception as e:
            logger.warning(f"Requests 본문 추출 실패: {e}")
            return None

    def _clean_news_text(self, text: str) -> str:
        """뉴스 텍스트 정리"""
        if not text:
            return ""
        
        # 불필요한 텍스트 제거
        text = re.sub(r'^\s*\[.*?\]\s*', '', text)  # [기자명] 제거
        text = re.sub(r'(기자|편집자|특파원).*?=\s*', '', text)  # 기자 정보 제거
        text = re.sub(r'\s+', ' ', text)  # 연속 공백 정리
        text = re.sub(r'[\r\n\t]+', ' ', text)  # 개행문자 정리
        
        return text.strip()
    
    async def evaluate_impact_with_rag(self, news_item: Dict) -> Tuple[float, str]:
        """순수 RAG 방식 영향도 평가"""
        try:
            stock_code = news_item["stock_code"]
            stock_name = self.stock_names.get(stock_code, stock_code)
            title = news_item["title"]
            content = news_item["content"]
            
            logger.info(f"🔍 RAG 방식 영향도 평가 시작: '{title[:50]}...'")
            
            # API 호출 간격 조절 (텔레그램 API 429 에러 방지)
            api_interval = self.config.get("NEWS_API_CALL_INTERVAL", 2)
            time.sleep(api_interval)
            
            # RAG 방식 영향도 평가 (모든 뉴스를 LLM에 전달)
            api_score, direction_score, market_reaction, push_message = await self.evaluate_news_impact_api(
                news_item, stock_name or stock_code
            )
            
            # 0-10 스케일을 0-1 스케일로 변환 (기존 시스템 호환성)
            normalized_score = api_score / 10.0
            
            # 확장된 정보를 news_item에 추가 (DB 저장용)
            news_item["push_content"] = push_message
            
            logger.info(f"✅ RAG 영향도 평가 완료: {api_score}/10 (정규화: {normalized_score:.2f})")
            return normalized_score, push_message

        except Exception as e:
            logger.error(f"❌ RAG 영향도 평가 실패: {e}")
            log_error_with_traceback("RAG 영향도 평가 실패", e, {
                "stock_code": stock_code,
                "title": title[:50] if title else "No title"
            })
            return 0.0, "평가 실패"
    
    def calculate_basic_impact_score(self, news_item: Dict) -> int:
        """기본 영향도 점수 계산 (0-10 스케일)"""
        try:
            title = news_item["title"].lower()
            content = news_item["content"].lower()
            text = title + " " + content
            
            # 고영향도 키워드 가중치
            high_impact_keywords = {
                "실적": 3, "매출": 3, "영업이익": 3, "순이익": 3,
                "인수합병": 4, "M&A": 4, "투자": 2, "투자유치": 3,
                "신제품": 2, "출시": 2, "계약": 2, "수주": 3,
                "상장": 3, "IPO": 3, "증자": 2, "감자": 2,
                "배당": 2, "주식분할": 2, "합병": 4, "분할": 3,
                "규제": 2, "승인": 2, "허가": 2, "라이센스": 2,
                "특허": 2, "기술": 1, "개발": 1, "연구": 1,
                "위기": 3, "손실": 2, "적자": 2, "부실": 3,
                "사업": 1, "확장": 2, "진출": 2, "철수": 2
            }
            
            # 키워드 점수 계산
            score = 0
            for keyword, weight in high_impact_keywords.items():
                if keyword in text:
                    score += weight
            
            # 제목에 있는 키워드는 가중치 추가
            for keyword, weight in high_impact_keywords.items():
                if keyword in title:
                    score += weight * 0.5
            
            # 정규화 (0-10 범위)
            score = int(min(score, 10))
            
            return score
            
        except Exception as e:
            logger.error(f"기본 영향도 점수 계산 실패: {e}")
            return 5
    
    def get_latest_impact_keywords(self, stock_code: str, week_start: Optional[str] = None) -> Dict[str, int]:
        """❌ 단순화: 복잡한 MySQL 키워드 분석 제거 - ChromaDB keywords 컬렉션 직접 사용으로 대체"""
        return {}
    
    def calculate_basic_impact_score_with_db(self, news_item: Dict) -> int:
        """크로마 DB 핵심 키워드 기반 기본 영향도 점수 계산 (개선 버전)"""
        try:
            title = news_item["title"].lower()
            content = news_item["content"].lower()
            text = title + " " + content
            stock_code = news_item.get("stock_code", "")
            
            logger.info(f"🎯 기본 영향도 점수 계산 시작: {stock_code}")
            
            # 🔧 개선: 키워드 점수와 별개로 뉴스 내용 기반 점수 계산
            content_score = self._calculate_content_based_score(news_item)
            logger.info(f"📝 뉴스 내용 기반 점수: {content_score}/10")
            
            # 크로마 DB에서 최신 핵심 키워드 가져오기
            high_impact_keywords = {}  # ❌ MySQL 복잡한 키워드 분석 제거
            
            # 키워드 점수 계산
            keyword_score = 0
            matched_keywords = []
            
            if high_impact_keywords:
                for keyword, weight in high_impact_keywords.items():
                    if keyword in text:
                        keyword_score += weight
                        matched_keywords.append(f"{keyword}({weight})")
                
                # 제목에 있는 키워드는 가중치 추가
                for keyword, weight in high_impact_keywords.items():
                    if keyword in title:
                        keyword_score += weight * 0.5
                
                # 키워드 점수 정규화 (0-10 범위)
                keyword_score = int(min(keyword_score, 10))
                
                if matched_keywords:
                    logger.info(f"🎯 매칭된 키워드: {', '.join(matched_keywords)} → 키워드 점수: {keyword_score}/10")
                else:
                    logger.info(f"🎯 매칭된 키워드 없음 → 키워드 점수: {keyword_score}/10")
            else:
                logger.warning(f"⚠️ 키워드 데이터 없음 → 키워드 점수: 0/10")
            
            # 🔧 개선: 키워드 점수와 내용 점수를 결합 (키워드가 없어도 내용 기반으로 평가 가능)
            final_score = max(content_score, keyword_score)
            
            logger.info(f"✅ 최종 영향도 점수: {final_score}/10 (내용: {content_score}, 키워드: {keyword_score})")
            return final_score
            
        except Exception as e:
            logger.error(f"❌ DB 기반 기본 영향도 점수 계산 실패: {e}")
            log_error_with_traceback("DB 기반 기본 영향도 점수 계산 실패", e, {
                "stock_code": news_item.get("stock_code", ""),
                "title": news_item.get("title", "")[:50]
            })
            return 5  # 기본값으로 5점 반환
    
    def _calculate_content_based_score(self, news_item: Dict) -> int:
        """뉴스 내용 기반 영향도 점수 계산 (키워드와 독립적)"""
        try:
            title = news_item["title"].lower()
            content = news_item["content"].lower()
            text = title + " " + content
            
            score = 0
            
            # 1. 뉴스 길이 기반 점수 (긴 뉴스는 더 중요할 가능성)
            content_length = len(content)
            if content_length > 1000:
                score += 2
            elif content_length > 500:
                score += 1
            
            # 2. 제목 길이 기반 점수
            title_length = len(title)
            if title_length > 50:
                score += 1
            
            # 3. 특정 패턴 기반 점수
            important_patterns = {
                "실적": 3, "매출": 3, "영업이익": 3, "순이익": 3,
                "인수합병": 4, "m&a": 4, "투자": 2, "투자유치": 3,
                "신제품": 2, "출시": 2, "계약": 2, "수주": 3,
                "상장": 3, "ipo": 3, "증자": 2, "감자": 2,
                "배당": 2, "주식분할": 2, "합병": 4, "분할": 3,
                "규제": 2, "승인": 2, "허가": 2, "라이센스": 2,
                "특허": 2, "기술": 1, "개발": 1, "연구": 1,
                "위기": 3, "손실": 2, "적자": 2, "부실": 3,
                "사업": 1, "확장": 2, "진출": 2, "철수": 2,
                "증권": 1, "주식": 1, "주가": 1, "시장": 1,
                "금융": 1, "은행": 1, "보험": 1, "투자": 1
            }
            
            for pattern, weight in important_patterns.items():
                if pattern in text:
                    score += weight
            
            # 4. 제목에 있는 패턴은 가중치 추가
            for pattern, weight in important_patterns.items():
                if pattern in title:
                    score += weight * 0.5
            
            # 5. 특별한 표현 기반 점수
            special_expressions = {
                "발표": 2, "공시": 2, "발행": 2, "상장": 3,
                "인수": 3, "합병": 4, "분할": 3, "매각": 3,
                "투자": 2, "유치": 3, "계약": 2, "수주": 3,
                "신규": 2, "첫": 2, "최초": 2, "최고": 2,
                "급등": 3, "급락": 3, "상승": 2, "하락": 2,
                "호재": 3, "악재": 3, "긍정": 2, "부정": 2
            }
            
            for expr, weight in special_expressions.items():
                if expr in text:
                    score += weight
            
            # 정규화 (0-10 범위)
            score = int(min(score, 10))
            
            return score
            
        except Exception as e:
            logger.error(f"❌ 내용 기반 점수 계산 실패: {e}")
            return 3  # 기본값
    
    def search_similar_historical_cases(self, news_item: Dict) -> List[Dict]:
        """❌ 단순화: 복잡한 MySQL 유사 사례 검색 제거 - ChromaDB past_events 컬렉션 직접 사용으로 대체"""
        return []
        try:
            logger.info(f"🔍 과거 유사 사례 검색 시작: '{news_item['title'][:50]}...'")
            logger.info(f"📊 크로마DB 연결 상태 확인 중...")
            logger.info(f"🔗 크로마DB 객체: {self.vector_db is not None}")
            
            # 뉴스 텍스트 준비
            news_text = news_item["title"] + " " + news_item["content"]
            stock_code = news_item.get("stock_code", "")
            logger.info(f"📝 검색 쿼리 텍스트 길이: {len(news_text)}자")
            logger.info(f"📝 검색 쿼리 텍스트 미리보기: {news_text[:100]}...")
            
            # 1차: past_events 컬렉션에서 검색 (과거 중요 사건들)
            try:
                logger.info("📚 1차: past_events 컬렉션에서 검색 시작 (과거 중요 사건들)")
                logger.info(f"🔗 크로마DB 쿼리: collection=past_events, top_k=3")
                
                # 크로마DB 검색 전 상태 확인
                if hasattr(self.vector_db, 'collections') and 'past_events' in self.vector_db.collections:
                    try:
                        collection_count = self.vector_db.collections['past_events'].count()
                        logger.info(f"📊 past_events 컬렉션 문서 수: {collection_count}개")
                    except Exception as count_error:
                        logger.warning(f"⚠️ past_events 컬렉션 카운트 실패: {count_error}")
                        collection_count = 0
                else:
                    logger.warning("⚠️ past_events 컬렉션을 찾을 수 없음")
                    collection_count = 0
                
                # 안전한 검색 시도
                past_events_results = []
                try:
                    past_events_results = self.vector_db.search_similar_documents(
                        query=news_text,
                        collection_name="past_events",
                        top_k=3
                    )
                    logger.info(f"✅ past_events 크로마DB 쿼리 완료")
                    logger.info(f"📊 past_events 검색 결과: {len(past_events_results) if past_events_results else 0}개")
                except Exception as search_error:
                    logger.error(f"❌ past_events 검색 실패: {search_error}")
                    # 검색 실패 시 빈 결과로 처리
                    past_events_results = []
                
                # 검색 결과 상세 로깅
                if past_events_results:
                    logger.info(f"📋 검색 결과 상세 정보:")
                    for i, result in enumerate(past_events_results):
                        logger.info(f"  결과 {i+1}: distance={result.get('distance', 'N/A')}, metadata_keys={list(result.get('metadata', {}).keys())}")
                
                enhanced_cases = []
                
                if past_events_results and len(past_events_results) > 0:
                    logger.info(f"📚 past_events에서 {len(past_events_results)}개 유사 사례 발견")
                    
                    for i, case in enumerate(past_events_results):
                        try:
                            metadata = case.get("metadata", {})
                            # 🔧 수정: distance 값의 안전한 변환
                            distance = case.get("distance", 0.0)
                            try:
                                distance = float(distance) if distance is not None else 0.0
                            except (ValueError, TypeError):
                                distance = 0.0
                            
                            # 안전한 유사도 계산 (0 ≤ similarity ≤ 1)
                            similarity_score = max(0.0, min(1.0, 1.0 - distance))
                            # 유사도가 너무 낮으면 0으로 처리
                            if similarity_score < 0.1:
                                similarity_score = 0.0
                            
                            logger.info(f"🔍 사례 {i+1} 유사도 계산: distance={distance:.4f} → similarity={similarity_score:.4f}")
                            
                            # 과거 사례 정보 추출
                            case_info = {
                                "title": metadata.get("title", metadata.get("event_type", "제목 없음")),
                                "published_date": metadata.get("event_date", "날짜 없음"),
                                "stock_code": metadata.get("stock_code", "종목 없음"),
                                "impact_score": 0.8,  # past_events는 중요 사건이므로 높은 점수
                                "market_reaction": f"주가 {metadata.get('price_change', 'N/A')}",
                                "price_change": metadata.get("price_change", "가격 변동 없음"),
                                "similarity_score": similarity_score,
                                "summary": metadata.get("description", case.get("document", "")[:100] + "...")
                            }
                            
                            enhanced_cases.append(case_info)
                            
                            logger.info(f"📋 과거 사례 {i+1}: {case_info['title'][:30]}... (유사도: {similarity_score:.3f})")
                            logger.info(f"📊 크로마DB 메타데이터: {list(metadata.keys())}")
                            logger.info(f"📅 사례 날짜: {case_info['published_date']}")
                            logger.info(f"💰 가격 변동: {case_info['price_change']}")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ 과거 사례 {i+1} 처리 실패: {e}")
                            continue
                    
                    if enhanced_cases:
                        logger.info(f"✅ past_events 검색 완료: {len(enhanced_cases)}개 사례")
                        # 유사도 순으로 정렬
                        enhanced_cases.sort(key=lambda x: x.get('similarity_score', 0.0), reverse=True)
                        similarity_scores = [f"{case.get('similarity_score', 0.0):.3f}" for case in enhanced_cases]
                        logger.info(f"📊 유사도 순 정렬 완료: {similarity_scores}")
                        return enhanced_cases
                        
                else:
                    logger.warning("⚠️ past_events에서 유사 사례를 찾을 수 없음")
                    
            except Exception as e:
                logger.error(f"❌ past_events 크로마DB 검색 실패: {e}")
                logger.error(f"🔍 크로마DB 연결 상태: {self.vector_db is not None}")
                
                # HNSW 인덱스 오류인 경우 컬렉션 재생성 시도
                if "hnsw" in str(e).lower() or "index" in str(e).lower():
                    logger.warning("⚠️ HNSW 인덱스 오류 감지 - 컬렉션 재생성 시도")
                    try:
                        # past_events 컬렉션 재생성
                        if 'past_events' in self.vector_db.collections:
                            del self.vector_db.collections['past_events']
                        
                        # 컬렉션 재생성
                        if hasattr(self.vector_db, 'client') and self.vector_db.client is not None:
                            self.vector_db.collections['past_events'] = self.vector_db.client.create_collection(
                                name="past_events",
                                metadata={"hnsw:space": "cosine"}
                            )
                        else:
                            logger.error("❌ ChromaDB 클라이언트가 없어 컬렉션 재생성 불가")
                            past_events_results = []
                            return []
                        logger.info("✅ past_events 컬렉션 재생성 완료")
                        
                        # 재생성 후 다시 검색 시도
                        try:
                            past_events_results = self.vector_db.search_similar_documents(
                                query=news_text,
                                collection_name="past_events",
                                top_k=3
                            )
                            logger.info("✅ 컬렉션 재생성 후 검색 성공")
                        except Exception as retry_error:
                            logger.error(f"❌ 재생성 후 검색도 실패: {retry_error}")
                            past_events_results = []
                    except Exception as recreate_error:
                        logger.error(f"❌ 컬렉션 재생성 실패: {recreate_error}")
                        past_events_results = []
                else:
                    past_events_results = []
                
                log_error_with_traceback("past_events 검색 실패", e, {
                    "stock_code": stock_code,
                    "title": news_item.get("title", "")[:50]
                })
            
            # 최종 백업: 빈 리스트 (past_events 검색 실패 시)
            logger.debug("📋 유사 사례 없음 - 빈 리스트 반환")
            return []
            
        except Exception as e:
            logger.error(f"❌ 과거 유사 사례 검색 실패: {e}")
            log_error_with_traceback("과거 유사 사례 검색 실패", e, {
                "stock_code": news_item.get("stock_code", ""),
                "title": news_item.get("title", "")[:50]
            })
            return []
    
    def format_similar_cases_for_llm(self, similar_cases: List[Dict]) -> str:
        """유사 사례를 LLM 프롬프트용으로 포맷팅 (RAG 방식)"""
        try:
            if not similar_cases:
                return "과거 유사 사례: 없음"
            
            formatted_cases = []
            for i, case in enumerate(similar_cases, 1):
                case_text = f"""
사례 {i}:
- 제목: {case.get('title', 'N/A')}
- 날짜: {case.get('published_date', 'N/A')}
- 영향도: {case.get('impact_score', 0.0):.2f}/1.0
- 시장 반응: {case.get('market_reaction', 'N/A')}
- 가격 변동: {case.get('price_change', 'N/A')}
- 유사도: {case.get('similarity_score', 0.0):.3f}
- 요약: {case.get('summary', 'N/A')[:100]}...
"""
                formatted_cases.append(case_text.strip())
            
            result = "과거 유사 사례:\n" + "\n\n".join(formatted_cases)
            logger.debug(f"📝 LLM용 유사 사례 포맷팅 완료: {len(similar_cases)}개 사례")
            return result
            
        except Exception as e:
            logger.error(f"❌ 유사 사례 포맷팅 실패: {e}")
            return "과거 유사 사례: 포맷팅 실패"
    
    async def evaluate_news_impact_api(self, news_item: Dict, stock_name: str) -> Tuple[int, int, str, str]:
        """API 기반 뉴스 영향도 평가 (SkillStack 방식)"""
        try:
            logger.debug(f"🔍 뉴스 영향도 평가 시작: '{news_item['title'][:50]}...'")
            
            # 1. 과거 유사 사례 검색: past_events DB에서 유사한 사례 가져오기
            similar_cases = []  # ❌ MySQL 복잡한 유사 사례 검색 제거
            formatted_cases = self.format_similar_cases_for_llm(similar_cases)
            
            # 2. 핵심 키워드 가져오기: keywords DB에서 가장 최근 주차 키워드 가져오기
            stock_code = news_item.get("stock_code", "")
            impact_keywords = {}  # ❌ MySQL 복잡한 키워드 분석 제거
            
            # 3. 키워드 정보를 LLM용으로 포맷팅
            keywords_text = "핵심 영향 키워드 (최근 주차):\n"
            for keyword, weight in impact_keywords.items():
                keywords_text += f"- {keyword}: 가중치 {weight}\n"
            
            # 4. 강화된 RAG 프롬프트 생성 (순수 RAG 방식)
            enhanced_prompt = f"""
당신은 주식 시장 전문 분석가입니다. 제공된 참고 정보를 바탕으로 해당 종목에 뉴스가 어느정도의  영향도를 분석해주세요.
중요한 것은 해당 종목에 어느 정도의 영향을 미치는 가를 판단하는 것이 중요합니다!!!! 영향도 점수는 0.0-1.0 사이의 값으로 판단해주세요.

[분석 대상]
종목명: {stock_name}
종목코드: {stock_code}
뉴스 제목: {news_item['title']}
뉴스 내용: {news_item['content'][:800]}...

[참고 정보 - RAG 검색 결과]
{keywords_text}

{formatted_cases}

[분석 지침]
위의 참고 정보를 바탕으로 다음을 분석해주세요:
1. 과거 유사 사례(past_events DB)와의 비교 분석
2. 최근 주차 핵심 키워드(keywords DB)와의 연관성 평가
3. 시장 환경과의 연관성 고려

[분석 요청]
1. 영향도 점수 (0.0-1.0): 이 뉴스가 해당 종목의 주가에 미치는 영향의 강도
   - 0.0-0.3: 낮은 영향 (일반적인 업계 뉴스)
   - 0.4-0.6: 보통 영향 (기업에 직접적 영향)
   - 0.7-1.0: 높은 영향 (실적, 인수합병, 규제 등)

2. 방향성 점수 (1-5): 해당 종목의 주가에 미치는 방향성
   - 1: 매우 부정적 (실적 악화, 규제 강화 등)
   - 2: 부정적 (일시적 악재, 경쟁 심화 등)
   - 3: 중립 (정보 제공, 업계 동향 등)
   - 4: 긍정적 (실적 개선, 신규 사업 등)
   - 5: 매우 긍정적 (실적 대폭 개선, 인수합병 등)

3. 시장 영향 분석: 구체적인 시장 반응 예측 (100자 이내)

4. 투자자 알림 메시지: 텔레그램 발송용 간결한 메시지 (50자 이내)

[출력 형식]
영향도점수: 0.X
방향성점수: X
시장영향: (분석 내용)
알림메시지: (메시지 내용)

위 형식을 정확히 지켜서 응답해주세요.
"""
            
            # 5. LLM API 호출 (재시도 로직 포함)
            logger.debug("🤖 LLM API 호출 중...")
            
            response = await self._call_llm_with_retry(enhanced_prompt, max_retries=3, base_delay=3.0)
            
            if not response:
                logger.warning("⚠️ LLM API 응답이 비어있음")
                return 5, 3, "API 응답 없음", "뉴스 분석 실패"
            
            # 6. 응답 파싱
            logger.debug(f"📝 LLM 응답: {response[:200]}...")
            
            # 영향도 점수 추출 (0.0-1.0 → 0-10 변환)
            impact_score = 5
            impact_match = re.search(r'영향도점수:\s*([0-9.]+)', response)
            if impact_match:
                try:
                    impact_float = float(impact_match.group(1))
                    impact_score = int(impact_float * 10)  # 0.0-1.0 → 0-10
                    impact_score = max(0, min(10, impact_score))  # 범위 제한
                except ValueError:
                    logger.warning(f"⚠️ 영향도 점수 파싱 실패: {impact_match.group(1)}")
            
            # 방향성 점수 추출 (1-5)
            direction_score = 3
            direction_match = re.search(r'방향성점수:\s*([1-5])', response)
            if direction_match:
                try:
                    direction_score = int(direction_match.group(1))
                except ValueError:
                    logger.warning(f"⚠️ 방향성 점수 파싱 실패: {direction_match.group(1)}")
            
            # 시장 영향 분석 추출
            market_reaction = "분석 정보 없음"
            market_match = re.search(r'시장영향:\s*(.+?)(?=\n|알림메시지:|$)', response, re.DOTALL)
            if market_match:
                market_reaction = market_match.group(1).strip()[:100]
            
            # 알림 메시지 추출
            push_message = "뉴스 알림"
            push_match = re.search(r'알림메시지:\s*(.+?)(?=\n|$)', response)
            if push_match:
                push_message = push_match.group(1).strip()[:50]
            
            # 7. 결과 로깅
            logger.info(f"✅ 영향도 평가 완료: 영향도={impact_score}/10, 방향성={direction_score}/5")
            logger.debug(f"📊 시장영향: {market_reaction}")
            logger.debug(f"📱 알림메시지: {push_message}")
            
            # 8. 크로마 DB 업데이트 (고영향 뉴스만)
            if impact_score >= 0.7:  # 0.7 이상
                try:
                    # 과거 중요 이벤트 DB에 추가 (올바른 방식으로 수정)
                    high_impact_data = {
                        "stock_code": stock_code,
                        "stock_name": self.stock_names.get(stock_code, stock_code),
                        "title": news_item["title"],
                        "summary": news_item["content"][:200] + "...",
                        "impact_score": impact_score / 10.0,  # 0.0-1.0 변환
                        "publication_date": news_item.get("published_at", datetime.now()),
                    }
                    
                    # 고영향 뉴스로 저장
                    self.vector_db.add_high_impact_news(high_impact_data)
                    
                    logger.debug("📚 고영향 뉴스를 크로마 DB에 저장 완료")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 크로마 DB 저장 실패: {e}")
            
            return impact_score, direction_score, market_reaction, push_message
            
        except Exception as e:
            logger.error(f"❌ 뉴스 영향도 평가 실패: {e}")
            log_error_with_traceback("뉴스 영향도 평가 실패", e, {
                "stock_name": stock_name,
                "title": news_item.get("title", "")[:50]
            })
            return 5, 3, "평가 실패", "뉴스 분석 오류"
    
    async def generate_news_summary(self, news_item: Dict) -> Tuple[str, str]:
        """뉴스 핵심 요약 생성 (HyperCLOVA API 사용) - 완전 재구성"""
        try:
            title = news_item.get('title', '').strip()
            content = news_item.get('content', '').strip()
            stock_code = news_item.get('stock_code', '')
            stock_name = self.stock_names.get(stock_code, stock_code)
            
            logger.info(f"📝 뉴스 요약 생성 시작")
            logger.info(f"   • 종목: {stock_name} ({stock_code})")
            logger.info(f"   • 제목: {title[:50]}...")
            logger.info(f"   • 내용 길이: {len(content)}자")
            
            # 1단계: 기본 데이터 검증
            if not title:
                logger.warning("❌ 제목이 비어있음 - 요약 불가")
                return "제목 없음", "NO_TITLE"
            
            # 2단계: 내용이 너무 짧은 경우 제목 가공
            if len(content) < 50:
                logger.info(f"📝 내용이 짧음 ({len(content)}자) - 제목 기반 요약 생성")
                processed_title = self._process_title_for_summary(title)
                return processed_title, "TITLE_BASED"
            
            # 3단계: HyperCLOVA API 요약 시도 (완전 재구성)
            logger.info("🤖 HyperCLOVA API 요약 시도 시작")
            
            # 입력 데이터 정제
            clean_title = title.replace('"', '').replace("'", "").strip()
            clean_content = content[:1000].replace('"', '').replace("'", "").strip()  # 1000자로 제한
            
            logger.debug(f"📝 정제된 제목: {clean_title[:30]}...")
            logger.debug(f"📝 정제된 내용: {clean_content[:100]}...")
            
            # 강화된 프롬프트 생성
            summary_prompt = f"""
다음 뉴스를 1000자 이내로 핵심 요약해주세요.

종목: {stock_name}
제목: {clean_title}
내용: {clean_content}

요약 규칙:
1. 투자자 관점에서 핵심 내용만
2. 1000자 이내 간결하게
3. 감정적 표현 제거

응답: (1000자 이내 요약)
"""
            
            logger.debug(f"📝 프롬프트 준비 완료 (총 {len(summary_prompt)}자)")
            
            # API 호출 시도 (재시도 로직 포함)
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔄 HyperCLOVA API 호출 시도 {attempt + 1}/{max_retries}")
                    
                    api_start_time = time.time()
                    
                    # 실제 API 호출 (재시도 로직 포함)
                    raw_response = await self._call_llm_with_retry(summary_prompt, max_retries=2, base_delay=2.0)
                    
                    api_end_time = time.time()
                    api_duration = api_end_time - api_start_time
                    
                    logger.info(f"📡 API 호출 완료 (소요시간: {api_duration:.2f}초)")
                    logger.debug(f"📡 원본 응답: {raw_response}")
                    
                    # 응답 검증
                    if not raw_response:
                        logger.warning(f"⚠️ 시도 {attempt + 1}: API 응답 None")
                        if attempt == max_retries - 1:
                            break
                        continue
                    
                    if len(raw_response.strip()) < 5:
                        logger.warning(f"⚠️ 시도 {attempt + 1}: API 응답 너무 짧음 ({len(raw_response)}자)")
                        if attempt == max_retries - 1:
                            break
                        continue
                    
                    # 응답 파싱 (다단계)
                    logger.debug("🔍 응답 파싱 시작...")
                    
                    parsed_summary = ""
                    
                    # 파싱 방법 1: '응답:' 패턴
                    response_match = re.search(r'응답:\s*(.+?)(?=\n|$)', raw_response, re.DOTALL)
                    if response_match:
                        parsed_summary = response_match.group(1).strip()
                        logger.debug(f"✅ 파싱 방법 1 성공: {parsed_summary[:30]}...")
                    
                    # 파싱 방법 2: 첫 번째 의미있는 줄
                    if not parsed_summary:
                        lines = raw_response.strip().split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and len(line) > 10 and not any(keyword in line for keyword in ['응답:', '요약:', '규칙:', '종목:']):
                                parsed_summary = line
                                logger.debug(f"✅ 파싱 방법 2 성공: {parsed_summary[:30]}...")
                                break
                    
                    # 파싱 방법 3: 전체 응답 정제
                    if not parsed_summary:
                        cleaned_response = raw_response.strip()
                        # 불필요한 패턴 제거
                        cleaned_response = re.sub(r'(응답|요약|종목|제목|내용):\s*', '', cleaned_response)
                        cleaned_response = re.sub(r'\n+', ' ', cleaned_response)
                        if len(cleaned_response) > 10:
                            parsed_summary = cleaned_response
                            logger.debug(f"✅ 파싱 방법 3 성공: {parsed_summary[:30]}...")
                    
                    # 최종 검증 및 정리
                    if parsed_summary:
                        # 길이 제한 및 정리
                        final_summary = parsed_summary[:1000].strip()
                        
                        # 특수문자 정리
                        final_summary = re.sub(r'["\'\[\]{}()]', '', final_summary)
                        final_summary = re.sub(r'\s+', ' ', final_summary)
                        
                        if len(final_summary) >= 10:
                            logger.info(f"✅ HyperCLOVA 요약 성공: '{final_summary}'")
                            return final_summary, "HYPERCLOVA_SUCCESS"
                        else:
                            logger.warning(f"⚠️ 파싱된 요약이 너무 짧음: '{final_summary}'")
                    
                    logger.warning(f"⚠️ 시도 {attempt + 1}: 파싱 실패")
                    
                except Exception as api_error:
                    api_end_time = time.time()
                    api_duration = api_end_time - api_start_time if 'api_start_time' in locals() else 0
                    logger.warning(f"⚠️ 시도 {attempt + 1} API 오류 (소요시간: {api_duration:.2f}초): {api_error}")
                    
                    if attempt == max_retries - 1:
                        log_error_with_traceback("HyperCLOVA API 최종 실패", api_error, {
                            "stock_code": stock_code,
                            "title": title[:50],
                            "content_length": len(content),
                            "attempt": attempt + 1
                        })
            
            # 4단계: 모든 API 시도 실패 시 제목 기반 요약
            logger.warning("❌ 모든 HyperCLOVA API 시도 실패 - 제목 기반 요약으로 대체")
            fallback_summary = self._process_title_for_summary(title)
            return fallback_summary, "API_FAILED_FALLBACK"
                
        except Exception as e:
            logger.error(f"❌ 뉴스 요약 전체 프로세스 실패: {e}")
            log_error_with_traceback("뉴스 요약 전체 실패", e, {
                "stock_code": news_item.get('stock_code', ''),
                "title": news_item.get('title', '')[:50]
            })
            # 최종 fallback
            fallback_title = news_item.get('title', '뉴스 요약 오류')
            final_summary = fallback_title[:50] + "..." if len(fallback_title) > 50 else fallback_title
            return final_summary, "TOTAL_ERROR"

    def _process_title_for_summary(self, title: str) -> str:
        """제목을 요약용으로 가공"""
        try:
            # 간단한 제목 정리
            import re
            cleaned = title.strip()
            
            # HTML 엔티티 제거
            html_entities = {
                '&quot;': '"',
                '&amp;': '&',
                '&lt;': '<',
                '&gt;': '>',
                '&nbsp;': ' '
            }
            
            for entity, replacement in html_entities.items():
                cleaned = cleaned.replace(entity, replacement)
            
            # 언론사 태그 제거 ([서울경제], [연합뉴스] 등)
            cleaned = re.sub(r'\[.*?\]', '', cleaned)
            
            # 기자명 제거 (김○○ 기자, ○○○기자 등)
            cleaned = re.sub(r'[가-힣]{2,3}\s*기자', '', cleaned)
            
            # 연속 공백 정리
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            return cleaned.strip()
            
        except Exception as e:
            logger.error(f"제목 정리 오류: {e}")
            return title.strip()
    
    def get_stock_price_history(self, stock_code: str, news_date: str, days: int = 5) -> List[Dict]:
        """주가 데이터 조회 (pykrx 기반) - 뉴스 발생일 T부터 T+4까지"""
        try:
            logger.info(f"📈 주가 데이터 조회 시작: {stock_code}, 뉴스 발생일: {news_date}")
            logger.info(f"🔗 pykrx API 호출 준비 중...")
            
            # pykrx import
            try:
                from pykrx import stock
            except ImportError:
                logger.error("❌ pykrx 라이브러리가 설치되지 않았습니다. pip install pykrx를 실행하세요.")
                return []
            
            # 뉴스 발생일 파싱 (T일)
            try:
                news_dt = datetime.strptime(news_date, '%Y-%m-%d')
            except ValueError:
                # 다른 형식으로 시도
                news_dt = datetime.strptime(news_date[:10], '%Y-%m-%d')
            
            # 조회 기간: T일부터 T+4일까지 (총 5일)
            start_dt = news_dt
            end_dt = news_dt + timedelta(days=days)
            logger.info(f"📅 조회 기간: T({start_dt.strftime('%Y-%m-%d')}) ~ T+{days-1}({end_dt.strftime('%Y-%m-%d')})")
            
            # pykrx를 사용하여 주가 데이터 조회
            logger.info(f"🌐 pykrx API 호출 중...")
            
            # 날짜 형식을 YYYYMMDD로 변환
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
            
            # pykrx로 OHLCV 데이터 조회
            df = stock.get_market_ohlcv(start_date, end_date, stock_code)
            
            logger.info(f"✅ pykrx API 호출 완료")
            logger.info(f"📊 수신된 데이터: {len(df)}일")
            
            if df.empty:
                logger.warning(f"⚠️ 주가 데이터 없음: {stock_code}")
                return []
            
            logger.info(f"📊 주가 데이터 처리 시작: {len(df)}일 데이터")
            price_history = []
            
            for idx, row in df.iterrows():
                try:
                    # 날짜를 안전하게 문자열로 변환
                    date_str = str(idx)[:10] if str(idx) else "Unknown"
                    price_data = {
                        "date": date_str,
                        "open": round(float(row["시가"]), 2),
                        "high": round(float(row["고가"]), 2),
                        "low": round(float(row["저가"]), 2),
                        "close": round(float(row["종가"]), 2),
                        "volume": int(row["거래량"]),
                        "change": 0.0,
                        "change_percent": 0.0
                    }
                    price_history.append(price_data)
                    logger.debug(f"📈 {price_data['date']}: 종가 {price_data['close']:,.0f}원")
                except Exception as date_error:
                    logger.warning(f"⚠️ 날짜 처리 실패: {date_error}")
                    continue
            
            # 등락률 계산
            logger.info(f"📊 등락률 계산 중...")
            for i in range(1, len(price_history)):
                prev_close = price_history[i-1]["close"]
                current_close = price_history[i]["close"]
                change = current_close - prev_close
                change_percent = (change / prev_close) * 100 if prev_close != 0 else 0.0
                
                price_history[i]["change"] = round(change, 2)
                price_history[i]["change_percent"] = round(change_percent, 2)
            
            logger.info(f"✅ 주가 데이터 조회 완료: {len(price_history)}일 데이터")
            if price_history:
                logger.info(f"📊 T일 종가: {price_history[0]['close']:,.0f}원")
                logger.info(f"📊 T+{len(price_history)-1}일 종가: {price_history[-1]['close']:,.0f}원 (변동: {price_history[-1]['change_percent']:.1f}%)")
            return price_history
            
        except Exception as e:
            logger.error(f"❌ 주가 데이터 조회 실패: {e}")
            log_error_with_traceback("주가 데이터 조회 실패", e, {
                "stock_code": stock_code,
                "news_date": str(news_date),
                "days": days
            })
            return []
    
    def format_price_history_for_telegram(self, price_history: List[Dict], similar_case: Dict) -> str:
        """주가 데이터를 텔레그램 메시지용으로 포맷팅"""
        try:
            if not price_history:
                return "📈 주가 데이터를 조회할 수 없습니다."
            
            # 과거 사례 정보
            event_date = similar_case.get('published_date', '')
            event_title = similar_case.get('title', '')
            similarity_score = similar_case.get('similarity_score', 0.0)
            
            # 주가 추이 포맷팅
            formatted_lines = []
            formatted_lines.append(f"📊 <b>과거 유사 사례 주가 추이</b>")
            formatted_lines.append(f"🔍 유사 사례: {event_title[:50]}...")
            formatted_lines.append(f"📅 발생일: {event_date[:10]}")
            formatted_lines.append(f"🎯 유사도: {similarity_score:.2f}")
            formatted_lines.append("")
            formatted_lines.append("📈 <b>과거 유사 사례 5일간의 주가 추이</b>")
            
            for i, day in enumerate(price_history):
                date = day['date']
                close_price = day['close']
                change = day['change']
                change_percent = day['change_percent']
                
                # 등락에 따른 이모지
                if change_percent > 0:
                    trend_emoji = "📈"
                    change_text = f"+{change:,.0f}원 (+{change_percent:.1f}%)"
                elif change_percent < 0:
                    trend_emoji = "📉"
                    change_text = f"{change:,.0f}원 ({change_percent:.1f}%)"
                else:
                    trend_emoji = "➡️"
                    change_text = "변동 없음"
                
                # T일부터 T+4까지 표시
                if i == 0:
                    day_label = "T일"
                else:
                    day_label = f"T+{i}일"
                formatted_lines.append(f"{trend_emoji} {day_label} ({date}): {close_price:,.0f}원 {change_text}")
            
            # 전체 수익률 계산
            if len(price_history) > 1:
                first_price = price_history[0]['close']
                last_price = price_history[-1]['close']
                total_return = ((last_price - first_price) / first_price) * 100
                
                if total_return > 0:
                    return_emoji = "🚀"
                    return_text = f"+{total_return:.1f}%"
                elif total_return < 0:
                    return_emoji = "⬇️"
                    return_text = f"{total_return:.1f}%"
                else:
                    return_emoji = "➡️"
                    return_text = "0.0%"
                
                formatted_lines.append("")
                formatted_lines.append(f"💰 <b>5일간 수익률: {return_emoji} {return_text}</b>")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"❌ 주가 데이터 포맷팅 실패: {e}")
            return "📈 주가 데이터 포맷팅 중 오류가 발생했습니다."
    
    def format_trend_data_for_telegram(self, trend_data: Dict, similar_case: Dict) -> str:
        """StockTrendService 데이터를 텔레그램 메시지용으로 포맷팅"""
        try:
            if not trend_data or not trend_data.get('daily_data'):
                return "📈 주가 데이터를 조회할 수 없습니다."
            
            # 과거 사례 정보
            event_date = similar_case.get('published_date', '')
            event_title = similar_case.get('title', '')
            similarity_score = similar_case.get('similarity_score', 0.0)
            
            # 날짜 처리 (datetime 객체인 경우 문자열로 변환)
            if hasattr(event_date, 'strftime'):
                event_date_str = event_date.strftime('%Y-%m-%d')
            elif isinstance(event_date, str):
                event_date_str = event_date[:10] if len(event_date) >= 10 else str(event_date)
            else:
                event_date_str = str(event_date)[:10]
            
            # 주가 추이 포맷팅
            formatted_lines = []
            formatted_lines.append(f"📊 <b>과거 유사 사례 주가 추이 (pykrx)</b>")
            formatted_lines.append(f"🔍 유사 사례: {event_title[:50]}...")
            formatted_lines.append(f"📅 발생일: {event_date_str}")
            formatted_lines.append(f"🎯 유사도: {similarity_score:.2f}")
            formatted_lines.append("")
            formatted_lines.append("📈 <b>주가 추이 (T일부터 T+4까지)</b>")
            
            trend_data_list = trend_data['daily_data']
            
            for i, day in enumerate(trend_data_list):
                date = day.get('date', '')
                close_price = day.get('close', 0)
                change_rate = day.get('change_rate', 0)
                volume_man = day.get('volume_man', 0)
                trading_value_eok = day.get('trading_value_eok', 0)
                
                # 등락에 따른 이모지
                if change_rate > 0:
                    trend_emoji = "📈"
                    change_text = f"(+{change_rate:.1f}%)"
                elif change_rate < 0:
                    trend_emoji = "📉"
                    change_text = f"({change_rate:.1f}%)"
                else:
                    trend_emoji = "➡️"
                    change_text = "(0.0%)"
                
                # T일부터 T+4까지 표시
                if i == 0:
                    day_label = "T일"
                else:
                    day_label = f"T+{i}일"
                formatted_lines.append(f"{trend_emoji} {day_label} ({date}): {close_price:,.0f}원 {change_text}")
                
                # 거래량 정보도 포함
                if volume_man > 0:
                    formatted_lines.append(f"    📊 거래량: {volume_man:,.1f}만주 | 거래대금: {trading_value_eok:,.1f}억원")
            
            # 전체 수익률 계산
            if len(trend_data_list) > 1:
                first_price = trend_data_list[0].get('close', 0)
                last_price = trend_data_list[-1].get('close', 0)
                
                if first_price > 0:
                    total_return = ((last_price - first_price) / first_price) * 100
                    
                    if total_return > 0:
                        return_emoji = "🚀"
                        return_text = f"+{total_return:.1f}%"
                    elif total_return < 0:
                        return_emoji = "⬇️"
                        return_text = f"{total_return:.1f}%"
                    else:
                        return_emoji = "➡️"
                        return_text = "0.0%"
                    
                    formatted_lines.append("")
                    formatted_lines.append(f"💰 <b>5일간 수익률: {return_emoji} {return_text}</b>")
            
            # 추가 분석 정보
            if trend_data.get('summary'):
                summary = trend_data['summary']
                formatted_lines.append("")
                formatted_lines.append("🔍 <b>추가 분석</b>")
                formatted_lines.append(f"• 기간 수익률: {summary.get('total_change_rate', 0):+.2f}%")
                formatted_lines.append(f"• 평균 거래량: {summary.get('avg_volume_man', 0):,.1f}만주")
                formatted_lines.append(f"• 평균 거래대금: {summary.get('avg_trading_value_eok', 0):,.1f}억원")
                formatted_lines.append(f"• 변동성: {summary.get('volatility', 0):.2f}%")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"❌ StockTrendService 데이터 포맷팅 실패: {e}")
            return "📈 주가 데이터 포맷팅 중 오류가 발생했습니다."

    def create_fallback_price_message(self, similar_case: Dict, stock_code: str, stock_name: Optional[str]) -> str:
        """주가 데이터 조회 실패 시 대체 메시지 생성"""
        try:
            event_title = similar_case.get('title', '과거 사례')
            event_date = similar_case.get('published_date', '날짜 불명')
            similarity_score = similar_case.get('similarity_score', 0.0)
            
            formatted_lines = []
            formatted_lines.append(f"📊 <b>과거 유사 사례 분석 (데이터 제한)</b>")
            formatted_lines.append(f"🔍 유사 사례: {event_title[:50]}...")
            formatted_lines.append(f"📅 발생일: {event_date[:10]}")
            formatted_lines.append(f"🎯 유사도: {similarity_score:.3f}")
            formatted_lines.append("")
            formatted_lines.append("⚠️ <b>주가 데이터 조회 실패</b>")
            formatted_lines.append(f"• 종목: {stock_name} ({stock_code})")
            formatted_lines.append("• 과거 주가 데이터를 조회할 수 없습니다.")
            formatted_lines.append("• 시장 상황이나 데이터 제공 제한으로 인한 문제일 수 있습니다.")
            formatted_lines.append("")
            formatted_lines.append("💡 <b>분석 대안</b>")
            formatted_lines.append("• 유사한 과거 사례가 발견되었습니다.")
            formatted_lines.append("• 해당 종목의 최근 동향을 별도로 확인해보세요.")
            formatted_lines.append("• 전문가 의견이나 기술적 분석을 참고하시기 바랍니다.")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"❌ 대체 메시지 생성 실패: {e}")
            return "📈 주가 데이터 분석 중 오류가 발생했습니다."

    def save_news_to_db(self, news_item: Dict, impact_score: float, reasoning: str):
        """뉴스 데이터베이스 저장 (단순화)"""
        try:
            logger.debug(f"💾 뉴스 DB 저장: {news_item['title'][:30]}...")
            
            # ✅ 단순화: 기본 뉴스 정보만 MySQL에 저장
            query = """
            INSERT INTO news (
                stock_code, title, content, url, source, published_at,
                impact_score, reasoning, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                impact_score = VALUES(impact_score),
                reasoning = VALUES(reasoning),
                updated_at = NOW()
            """
            
            params = (
                news_item["stock_code"],
                news_item["title"],
                news_item["content"],
                news_item["url"],
                news_item.get("source", ""),
                news_item["published_at"],
                impact_score,
                reasoning,
                datetime.now()
            )
            
            self.mysql_client.execute_query(query, params)
            logger.info(f"✅ 뉴스 저장 완료: {news_item['title'][:50]}...")
            
        except Exception as e:
            logger.error(f"❌ 뉴스 저장 실패: {e}")
            # ❌ 복잡한 에러 처리 제거
    
    def save_to_vector_db(self, news_item: Dict, impact_score: float):
        """벡터 데이터베이스에 저장"""
        try:
            # 고영향 뉴스인 경우 영구 저장
            if impact_score >= self.impact_threshold:  # 0.7 이상
                high_impact_data = {
                    "stock_code": news_item["stock_code"],
                    "stock_name": self.stock_names.get(news_item["stock_code"], news_item["stock_code"]),
                    "title": news_item["title"],
                    "summary": news_item.get("content", "")[:200],  # 첫 200자를 요약으로 사용
                    "impact_score": impact_score,
                    "publication_date": news_item["published_at"],
                }
                
                # 고영향 뉴스 저장
                self.vector_db.add_high_impact_news(high_impact_data)
                logger.info(f"고영향 뉴스 벡터 DB 저장 완료: {news_item['title'][:50]}...")
            
            # 일일 뉴스 저장은 이미 crawl_news_for_stock에서 처리됨 (중복 저장 방지)
            logger.debug(f"일일 뉴스는 이미 저장됨: {news_item['title'][:30]}...")
            
        except Exception as e:
            logger.error(f"벡터 DB 저장 실패: {e}")
            log_error_with_traceback("벡터 DB 저장 실패", e, {
                "stock_code": news_item.get("stock_code", ""),
                "title": news_item.get("title", "")[:50]
            })
    
    async def send_alert(self, news_item: Dict, impact_score: float, reasoning: str):
        """고영향 뉴스 알림 전송 (사용자별 설정 확인 + 채널 알림)"""
        # 🔧 수정: datetime import를 함수 최상단으로 이동하여 UnboundLocalError 해결
        from datetime import datetime, timedelta
        
        try:
            stock_code = news_item["stock_code"]
            stock_name = self.stock_names.get(stock_code, stock_code)
            
            # 뉴스 요약 생성 (상세 로깅 추가)
            logger.info("📝 뉴스 요약 생성 시작...")
            logger.debug(f"📝 요약 대상 뉴스: {news_item.get('title', 'No title')[:50]}...")
            
            summary_start_time = time.time()
            try:
                news_summary, summary_method = await self.generate_news_summary(news_item)
                summary_end_time = time.time()
                summary_duration = summary_end_time - summary_start_time
                
                # 실제 요약 생성 방식에 따른 정확한 로그 출력
                if summary_method == "HYPERCLOVA_SUCCESS":
                    logger.info(f"✅ HyperCLOVA 요약 완료 (소요시간: {summary_duration:.2f}초)")
                elif summary_method == "TITLE_PROCESSING":
                    logger.info(f"✅ 제목 가공 요약 완료 (소요시간: {summary_duration:.2f}초)")
                elif summary_method == "HYPERCLOVA_FALLBACK":
                    logger.warning(f"⚠️ HyperCLOVA 응답 부족 - 제목 사용 (소요시간: {summary_duration:.2f}초)")
                elif summary_method == "HYPERCLOVA_PARSE_ERROR":
                    logger.warning(f"⚠️ HyperCLOVA 파싱 실패 - 제목 사용 (소요시간: {summary_duration:.2f}초)")
                elif summary_method == "HYPERCLOVA_API_ERROR":
                    logger.error(f"❌ HyperCLOVA API 실패 - 제목 사용 (소요시간: {summary_duration:.2f}초)")
                else:
                    logger.error(f"❌ 요약 생성 실패 - 백업 사용 (소요시간: {summary_duration:.2f}초)")
                
                logger.debug(f"📝 생성된 요약 내용: {news_summary[:100]}...")
                
                # 요약 품질 검증 로깅
                if news_summary and len(news_summary.strip()) > 5:
                    logger.debug("✅ 요약 품질 검증 통과")
                else:
                    logger.warning(f"⚠️ 요약 품질 문제: '{news_summary}' (길이: {len(news_summary) if news_summary else 0})")
                    
            except Exception as summary_error:
                summary_end_time = time.time()
                summary_duration = summary_end_time - summary_start_time
                logger.error(f"❌ 요약 생성 실패 (소요시간: {summary_duration:.2f}초): {summary_error}")
                log_error_with_traceback("뉴스 요약 생성 실패", summary_error, {
                    "stock_code": news_item.get("stock_code", ""),
                    "title": news_item.get("title", "")[:50],
                    "content_length": len(news_item.get("content", "")),
                    "duration": summary_duration
                })
                # 백업 요약 생성
                news_summary = news_item.get('title', '요약 생성 실패')[:50]
                if len(news_summary) > 50:
                    news_summary += "..."
                summary_method = "ERROR_FALLBACK"
            
            # 과거 유사 사례 검색 및 주가 추이 분석 (강화된 버전)
            logger.info("📊 과거 유사 사례 및 주가 추이 분석 시작...")
            similar_cases = self.search_similar_historical_cases(news_item)
            price_history_message = ""
            
            # 과거 유사 사례 처리 (개선된 방식)
            if similar_cases and len(similar_cases) > 0:
                # 가장 유사한 사례 선택
                most_similar_case = similar_cases[0]
                similarity_score = most_similar_case.get('similarity_score', 0.0)
                
                logger.info(f"🔍 가장 유사한 사례 발견: '{most_similar_case.get('title', 'No Title')[:50]}...'")
                logger.info(f"🔍 유사도: {similarity_score:.3f}")
                logger.info(f"📅 사례 날짜: {most_similar_case.get('published_date', 'Unknown')}")
                
                # 유사도 기준 완화 (0.1)로 더 많은 경우에 분석 수행
                if similarity_score >= 0.0:
                    logger.info(f"🚀 유사도 {similarity_score:.3f} >= 0.0 - 주가 추이 분석 시작")
                    
                    try:
                        # 과거 사례 날짜 추출 및 검증
                        event_date = most_similar_case.get('published_date', '')
                        logger.debug(f"📅 과거 사례 날짜: {event_date}")
                        
                        # 날짜 처리 강화
                        event_date_str = ""
                        if event_date:
                            try:
                                # 다양한 날짜 형식 지원
                                if isinstance(event_date, str):
                                    if len(event_date) >= 10:
                                        event_date_str = event_date[:10]
                                    else:
                                        event_date_str = event_date
                                elif hasattr(event_date, 'strftime'):
                                    event_date_str = event_date.strftime('%Y-%m-%d')
                                else:
                                    event_date_str = str(event_date)[:10]
                                
                                logger.debug(f"📅 정규화된 날짜: {event_date_str}")
                                
                                # 날짜 형식 유효성 검증
                                datetime.strptime(event_date_str, '%Y-%m-%d')
                                
                                # 주가 추이 데이터 조회
                                price_history = self.get_stock_price_history(stock_code, event_date_str, 5)
                                
                                if price_history and len(price_history) > 0:
                                    logger.info(f"📊 주가 추이 데이터 조회 성공: {len(price_history)}건")
                                    price_history_message = self.format_price_history_for_telegram(price_history, most_similar_case)
                                else:
                                    logger.warning(f"⚠️ 주가 추이 데이터 없음: {event_date_str}")
                                    price_history_message = self.create_fallback_price_message(most_similar_case, stock_code, stock_name)
                                    
                            except ValueError as date_error:
                                logger.warning(f"⚠️ 날짜 형식 오류: {event_date} - {date_error}")
                                price_history_message = self.create_fallback_price_message(most_similar_case, stock_code, stock_name)
                            except Exception as history_error:
                                logger.error(f"❌ 주가 추이 조회 실패: {history_error}")
                                price_history_message = self.create_fallback_price_message(most_similar_case, stock_code, stock_name)
                        else:
                            logger.warning(f"⚠️ 과거 사례 날짜 없음")
                            price_history_message = self.create_fallback_price_message(most_similar_case, stock_code, stock_name)
                            
                    except Exception as analysis_error:
                        logger.error(f"❌ 과거 사례 분석 실패: {analysis_error}")
                        price_history_message = self.create_fallback_price_message(most_similar_case, stock_code, stock_name)
                else:
                    logger.info(f"⚠️ 유사도 {similarity_score:.3f} < 0.0 - 주가 추이 분석 생략")
                    price_history_message = ""
            else:
                logger.info("⚠️ 유사한 과거 사례 없음 - 주가 추이 분석 생략")
                price_history_message = ""
            
            # 종목 정보 조회
            stock_info = self.get_stock_info_for_code(stock_code)
            current_price = stock_info.get('current_price', 'N/A')
            prev_close = stock_info.get('prev_close', 'N/A')
            open_price = stock_info.get('open_price', 'N/A')
            high_price = stock_info.get('high_price', 'N/A')
            market_cap = stock_info.get('market_cap', 'N/A')
            per_ratio = stock_info.get('per_ratio', 'N/A')
            
            # 영향도 레벨 결정
            if impact_score >= 0.9:
                impact_level = "🔥 매우 높음"
                impact_emoji = "🚨"
            elif impact_score >= 0.7:
                impact_level = "🔥 높음"
                impact_emoji = "🔥"
            elif impact_score >= 0.5:
                impact_level = "⚡ 중간"
                impact_emoji = "⚡"
            else:
                impact_level = "📊 보통"
                impact_emoji = "📊"
            
            # 시간 포맷팅
            pub_time = news_item['published_at']
            if isinstance(pub_time, str):
                time_str = pub_time
            else:
                time_str = pub_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 요약 생성 방식에 따른 설명 추가
            summary_source = {
                "HYPERCLOVA_SUCCESS": "HyperCLOVA AI 분석",
                "TITLE_PROCESSING": "제목 가공",
                "HYPERCLOVA_FALLBACK": "HyperCLOVA 백업",
                "HYPERCLOVA_PARSE_ERROR": "HyperCLOVA 파싱 실패",
                "HYPERCLOVA_API_ERROR": "HyperCLOVA API 실패",
                "ERROR_FALLBACK": "오류 백업"
            }.get(summary_method, "알 수 없는 방식")
            
            # 메시지 구성 (주가 추이 정보 포함)
            message_parts = []
            
            # 기본 알림 정보
            message_parts.append(f"{impact_emoji} <b>고영향 뉴스 알림</b>")
            message_parts.append("")
            message_parts.append("📊 <b>종목 현황</b>")
            message_parts.append(f"• 종목: <b>{stock_name}</b> ({stock_code})")
            message_parts.append(f"• 현재가: <b>{current_price}</b> 원")
            message_parts.append(f"• 전일종가: {prev_close} 원")
            message_parts.append(f"• 시가: {open_price} 원 | 고가: {high_price} 원")
            message_parts.append("")
            message_parts.append("📈 <b>기업 정보</b>")
            message_parts.append(f"• 시가총액: {market_cap}")
            message_parts.append(f"• PER: {per_ratio}")
            message_parts.append("")
            message_parts.append("📰 <b>뉴스 정보</b>")
            message_parts.append(f"• 제목: {news_item['title']}")
            message_parts.append(f"• 발행: {time_str}")
            message_parts.append(f"• 출처: {news_item.get('source', 'N/A')}")
            message_parts.append("")
            message_parts.append(f"🔍 <b>핵심 요약</b> ({summary_source})")
            message_parts.append(news_summary)
            message_parts.append("")
            message_parts.append("💡 <b>분석 지표</b>")
            message_parts.append(f"• 영향도: <b>{impact_score:.2f}/1.0</b> ({impact_level})")
            message_parts.append("• 필터링: 3단계 통과")
            message_parts.append(f"• 분석시간: {datetime.now().strftime('%H:%M:%S')}")
            
            # 과거 사례 주가 추이 추가
            if price_history_message:
                message_parts.append("")
                message_parts.append("📈 <b>과거 유사 사례 주가 추이</b>")
                message_parts.append(price_history_message)
            
            # 최종 메시지 조합
            final_message = "\n".join(message_parts)
            
            # 🆕 사용자별 알림 전송 (설정 확인)
            await self._send_user_notifications(news_item, final_message, impact_score)
            
            # 🆕 채널 알림 전송 (기존 방식 유지)
            await self._send_channel_notification(final_message)
            
            logger.info(f"✅ 뉴스 알림 전송 완료: {stock_name} ({stock_code})")
            
        except Exception as e:
            logger.error(f"❌ 뉴스 알림 전송 실패: {e}")
            log_error_with_traceback("뉴스 알림 전송 실패", e, {
                "stock_code": news_item.get("stock_code", ""),
                "title": news_item.get("title", "")[:50],
                "impact_score": impact_score
            })
    
    async def _send_user_notifications(self, news_item: Dict, message: str, impact_score: float):
        """사용자별 알림 전송 (설정 확인 + 종목 필터링)"""
        try:
            # UserConfigLoader import
            from shared.service_config.user_config_loader import UserConfigLoader
            
            config_loader = UserConfigLoader()
            stock_code = news_item.get("stock_code", "")
            
            # 모든 활성 사용자 조회 (현재는 테스트용으로 고정 사용자)
            # TODO: 실제로는 데이터베이스에서 활성 사용자 목록을 조회해야 함
            test_users = ["1"]  # 테스트용 사용자 ID
            
            for user_id in test_users:
                try:
                    # 🆕 사용자가 이 종목에 관심이 있는지 확인
                    is_interested = await config_loader.is_user_interested_in_stock(user_id, stock_code)
                    if not is_interested:
                        logger.debug(f"⚠️ 사용자가 종목에 관심 없음: {user_id} - {stock_code}")
                        continue
                    
                    # 사용자별 알림 설정 조회
                    notification_settings = await config_loader.get_user_notification_settings(user_id)
                    
                    # 뉴스 알림이 활성화되어 있고, 전체 알림이 활성화된 경우만 전송
                    if (notification_settings.get("enabled", True) and 
                        notification_settings.get("news_alerts", True)):
                        
                        # 사용자별 텔레그램 설정 조회
                        telegram_config = await config_loader.get_user_telegram_config(user_id)
                        if telegram_config and telegram_config.get("enabled", True):
                            # 개별 사용자에게 알림 전송
                            await self._send_user_notification(user_id, message, telegram_config)
                            logger.info(f"✅ 사용자 뉴스 알림 전송 완료: {user_id} - {stock_code}")
                        else:
                            logger.debug(f"⚠️ 사용자 텔레그램 비활성화: {user_id}")
                    else:
                        logger.debug(f"⚠️ 사용자 뉴스 알림 비활성화: {user_id}")
                        
                except Exception as user_error:
                    logger.error(f"❌ 사용자 알림 전송 실패: {user_id} - {user_error}")
                    
        except Exception as e:
            logger.error(f"❌ 사용자별 알림 전송 실패: {e}")
    
    async def _send_user_notification(self, user_id: str, message: str, telegram_config: Dict):
        """개별 사용자에게 알림 전송"""
        try:
            # 사용자별 채팅 ID 사용
            chat_id = telegram_config.get("chat_id")
            if chat_id:
                # 텔레그램 봇으로 개별 사용자에게 전송
                from shared.apis.telegram_api import TelegramBotClient
                telegram_bot = TelegramBotClient()
                telegram_bot.send_message(message, str(chat_id))
                logger.info(f"✅ 개별 사용자 알림 전송 완료: {user_id} -> {chat_id}")
            else:
                logger.warning(f"⚠️ 사용자 채팅 ID 없음: {user_id}")
                
        except Exception as e:
            logger.error(f"❌ 개별 사용자 알림 전송 실패: {user_id} - {e}")
    
    async def _send_channel_notification(self, message: str):
        """채널 알림 전송 (기존 방식)"""
        try:
            from shared.apis.telegram_api import TelegramBotClient
            telegram_bot = TelegramBotClient()
            telegram_bot.send_message(message)
            logger.info("✅ 채널 알림 전송 완료")
        except Exception as e:
            logger.error(f"❌ 채널 알림 전송 실패: {e}")

    async def crawl_news_for_stock(self, stock_code: str):
        """종목별 뉴스 크롤링 (4단계 준비)"""
        try:
            logger.info(f"📈 종목 {stock_code} 뉴스 크롤링 시작")
            
            # 종목 정보 수집
            logger.debug(f"📊 종목 정보 수집 요청: {stock_code}")
            stock_info = self.get_stock_info_for_code(stock_code)
            
            # 종목 정보 수집 결과 로깅
            stock_name = stock_info.get("종목명", "Unknown")
            if stock_name != "Unknown":
                logger.debug(f"✅ 종목 정보 수집 성공: {stock_name} ({stock_code})")
                logger.debug(f"🔮 4단계 준비: {stock_name} 종목 정보 준비 완료")
            else:
                logger.warning(f"⚠️ 종목 정보 수집 실패: {stock_code} - 기본값으로 진행")
                logger.debug(f"🔮 4단계 준비: 종목 정보 없이 진행 - 나중에 보완 필요")
            
            # API 방식으로 뉴스 수집 (페이지 3개, 페이지당 20개)
            logger.debug(f"📰 뉴스 수집 시작: {stock_code} (API 방식)")
            news_list = self.crawl_naver_finance_news(stock_code, pages=2, size=3)
            logger.debug(f"📰 뉴스 수집 완료: {len(news_list)}개 수집")
            
            # 각 뉴스에 종목 정보 추가
            logger.debug(f"📊 뉴스에 종목 정보 추가 중...")
            for news_item in news_list:
                news_item.update({
                    "stock_info": stock_info,
                    "stock_name": stock_name
                })
                logger.debug(f"📊 뉴스에 종목 정보 추가: '{news_item['title'][:30]}...' -> {stock_name}")
            
            logger.debug(f"🔮 4단계 준비: {len(news_list)}개 뉴스에 종목 정보 통합 완료")
            
            # 🔥 중요: 모든 뉴스를 daily_news ChromaDB에 저장 (필터링 없이)
            logger.info(f"📚 모든 뉴스를 daily_news ChromaDB에 저장 시작: {len(news_list)}개 뉴스")
            successful_saves = 0
            failed_saves = 0
            
            for i, news_item in enumerate(news_list, 1):
                try:
                    logger.debug(f"📚 [{i}/{len(news_list)}] daily_news 저장 시도: {news_item['title'][:50]}...")
                    
                    daily_news_data = {
                        "stock_code": news_item["stock_code"],
                        "stock_name": stock_name,
                        "title": news_item["title"],
                        "content": news_item.get("content", ""),
                        "url": news_item["url"],
                        "publication_date": news_item["published_at"]
                    }
                    
                    # 데이터 유효성 검사
                    if not daily_news_data["title"].strip():
                        logger.warning(f"⚠️ [{i}] 제목이 비어있는 뉴스 건너뜀")
                        failed_saves += 1
                        continue
                    
                    if not daily_news_data["stock_code"].strip():
                        logger.warning(f"⚠️ [{i}] 종목코드가 비어있는 뉴스 건너뜀")
                        failed_saves += 1
                        continue
                    
                    # 모든 뉴스를 daily_news에 저장 (필터링 없이)
                    result_id = self.vector_db.add_daily_news(daily_news_data)
                    
                    if result_id:
                        successful_saves += 1
                        logger.debug(f"✅ [{i}] daily_news 저장 성공: {result_id}")
                    else:
                        failed_saves += 1
                        logger.error(f"❌ [{i}] daily_news 저장 결과 ID 없음")
                    
                except Exception as e:
                    failed_saves += 1
                    logger.error(f"❌ [{i}] daily_news 저장 실패: {e}")
                    logger.error(f"❌ 실패한 뉴스 데이터: {news_item.get('title', 'NO_TITLE')[:50]}")
                    import traceback
                    logger.error(f"❌ 상세 에러: {traceback.format_exc()}")
                    continue
            
            # 저장 결과 요약
            logger.info(f"📚 daily_news ChromaDB 저장 완료:")
            logger.info(f"  ✅ 성공: {successful_saves}개")
            logger.info(f"  ❌ 실패: {failed_saves}개")
            logger.info(f"  📊 총계: {len(news_list)}개 (성공률: {successful_saves/len(news_list)*100:.1f}%)")
            
            # ChromaDB 저장 검증 (실제로 저장되었는지 확인)
            try:
                verification_stats = self.vector_db.get_collection_stats()
                daily_news_count = verification_stats.get("daily_news", {}).get("count", 0)
                logger.info(f"🔍 ChromaDB 검증: daily_news 컬렉션에 실제 {daily_news_count}개 문서 존재")
            except Exception as e:
                logger.error(f"❌ ChromaDB 검증 실패: {e}")
            
            # 뉴스 처리 태스크 생성 (필터링 및 분석용)
            logger.debug(f"🔄 뉴스 처리 태스크 생성 중...")
            tasks = []
            for news_item in news_list:
                task = asyncio.create_task(self.process_news_item(news_item))
                tasks.append(task)

            if tasks:
                logger.debug(f"�� {len(tasks)}개 뉴스 처리 태스크 실행 중...")
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.debug(f"✅ 모든 뉴스 처리 태스크 완료")

            logger.info(f"✅ 종목 {stock_code} 뉴스 크롤링 완료: {len(news_list)}개 ({stock_name})")

        except Exception as e:
            logger.error(f"❌ 종목 {stock_code} 뉴스 크롤링 실패: {e}")
            log_error_with_traceback("종목별 뉴스 크롤링 실패", e, {"stock_code": stock_code})

    def clear_session_cache(self):
        """세션 캐시 정리"""
        try:
            with self.cache_lock:
                cache_size = len(self.news_cache)
                self.news_cache.clear()
                logger.info(f"세션 캐시 정리 완료: {cache_size}개 항목")
        except Exception as e:
            logger.error(f"세션 캐시 정리 실패: {e}")

    async def crawl_all_news(self):
        """모든 종목 뉴스 크롤링"""
        try:
            logger.info("전체 뉴스 크롤링 시작")
            
            # 세션 시작 시 캐시 초기화
            self.clear_session_cache()

            for stock_code in self.stock_codes:
                await self.crawl_news_for_stock(stock_code)

            logger.info("전체 뉴스 크롤링 완료")

            # --- [추가] 고영향 뉴스가 하나도 없을 때 임의 뉴스 텔레그램 전송 ---
            stats = self.calculate_daily_stats()
            if stats["high_impact_news"] == 0 and stats["total_news"] > 0:
                logger.info("⚠️ 고영향 뉴스가 없어 임의 뉴스로 텔레그램 테스트 전송 시작")
                
                # CSV에서 임의 뉴스 1개 선택
                if self.daily_csv_file.exists():
                    with open(self.daily_csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        if rows:
                            row = rows[0]  # 첫 번째 뉴스
                            logger.info(f"📰 임의 뉴스 선택: {row.get('title', 'Unknown')[:50]}...")
                            
                            # dict → news_item 변환
                            news_item = dict(row)
                            
                            # 필드 타입 보정
                            news_item["impact_score"] = float(news_item.get("impact_score", 0.0))
                            news_item["published_at"] = news_item.get("published_at", datetime.now())
                            
                            # stock_info 보충
                            if "stock_info" not in news_item or not news_item["stock_info"]:
                                stock_info = self.get_stock_info_for_code(news_item["stock_code"])
                                news_item["stock_info"] = stock_info
                                logger.info(f"📊 종목 정보 보충: {stock_info.get('종목명', 'Unknown')}")
                            
                            # 텔레그램 전송
                            await self.send_alert(news_item, news_item["impact_score"], news_item.get("reasoning", "임의 뉴스 테스트"))
                            logger.info("✅ 임의 뉴스 텔레그램 전송 완료")

                            # --- 과거 유사 사례도 임의 1개 전송 ---
                            logger.info("🔍 과거 유사 사례 검색 시작...")
                            similar_cases = self.search_similar_historical_cases(news_item)
                            if similar_cases:
                                case = similar_cases[0]
                                logger.info(f"📚 과거 사례 선택: {case.get('title', 'Unknown')[:50]}...")
                                
                                # 과거 사례 텔레그램 메시지 포맷
                                msg_parts = []
                                msg_parts.append("🕰️ <b>과거 유사 사례 테스트</b>")
                                msg_parts.append("")
                                msg_parts.append(f"📰 <b>현재 뉴스</b>")
                                msg_parts.append(f"• 제목: {news_item.get('title', 'Unknown')}")
                                msg_parts.append(f"• 종목: {news_item.get('stock_name', news_item.get('stock_code', 'Unknown'))}")
                                msg_parts.append("")
                                msg_parts.append(f"📚 <b>과거 유사 사례</b>")
                                msg_parts.append(f"• 제목: {case.get('title', 'Unknown')}")
                                msg_parts.append(f"• 날짜: {case.get('published_date', 'Unknown')}")
                                msg_parts.append(f"• 유사도: {case.get('similarity_score', 0.0):.3f}")
                                if case.get('summary'):
                                    msg_parts.append(f"• 요약: {case.get('summary', '')}")
                                msg_parts.append("")
                                msg_parts.append("🔍 <b>RAG 검색 결과</b>")
                                msg_parts.append(f"• 검색된 사례 수: {len(similar_cases)}개")
                                msg_parts.append(f"• 크로마DB 통신: 성공")
                                msg_parts.append("")
                                msg_parts.append("⚠️ <i>이 분석은 참고용이며, 투자 결정은 신중하게 하시기 바랍니다.</i>")
                                
                                msg = "\n".join(msg_parts)
                                await self.telegram_bot.send_message_async(msg, parse_mode="HTML")
                                
                                # 최근 알람 메시지 저장
                                await save_latest_signal(msg)
                                logger.info("✅ 임의 과거 사례 텔레그램 전송 완료")
                            else:
                                logger.warning("⚠️ 과거 유사 사례를 찾을 수 없음")
                        else:
                            logger.warning("⚠️ CSV 파일에 뉴스 데이터가 없음")
                else:
                    logger.warning("⚠️ 일일 CSV 파일이 존재하지 않음")

        except Exception as e:
            logger.error(f"전체 뉴스 크롤링 실패: {e}")
        finally:
            self.close_driver()

    async def process_news_item(self, news_item: Dict):
        """뉴스 아이템 처리 (완전 통합 버전)"""
        start_time = time.time()
        telegram_sent = False
        filter_stage = "처리 시작"
        
        try:
            # 1. 3단계 필터링
            is_filtered, filter_reason, filter_result = await self.check_three_stage_filtering(news_item)
            if is_filtered:
                filter_stage = f"필터링됨: {filter_reason}"
                processing_time = time.time() - start_time
                
                # 필터링된 뉴스도 CSV에 기록 (통계용)
                self.save_to_csv(news_item, 0.0, filter_reason, filter_stage, processing_time, False)
                
                logger.info(f"필터링된 뉴스 제외: {news_item['title']} (사유: {filter_reason})")
                return

            filter_stage = "3단계 필터링 통과"

            # 2. 영향력 평가
            impact_score, reasoning = await self.evaluate_impact_with_rag(news_item)
            filter_stage = f"영향력 평가 완료 ({impact_score:.2f})"

            # 3. 데이터베이스 저장
            self.save_news_to_db(news_item, impact_score, reasoning)

            # 4. 벡터 DB 저장
            self.save_to_vector_db(news_item, impact_score)

            # 5. 고영향 뉴스 알림
            if impact_score >= self.impact_threshold:
                # 고영향 뉴스 상세 로깅
                self.log_high_impact_news_details(news_item, impact_score, reasoning)
                
                # 텔레그램 알림 전송
                await self.send_alert(news_item, impact_score, reasoning)
                telegram_sent = True
                
                # 고영향 뉴스 전용 CSV 저장
                processing_time_temp = time.time() - start_time
                self.save_high_impact_news_to_csv(news_item, impact_score, reasoning, processing_time_temp)
                
                filter_stage = f"고영향 뉴스 알림 전송 ({impact_score:.2f})"
                logger.info(f"🚨 고영향 뉴스 알림 발송: {news_item['title']} (점수: {impact_score:.2f})")

            # 6. 처리 시간 계산
            processing_time = time.time() - start_time

            # 7. CSV 저장 (최종 결과)
            self.save_to_csv(news_item, impact_score, reasoning, filter_stage, processing_time, telegram_sent)

            logger.info(f"✅ 뉴스 처리 완료: {news_item['title'][:50]}... (영향도: {impact_score:.2f}, 처리시간: {processing_time:.2f}s)")

        except Exception as e:
            processing_time = time.time() - start_time
            error_message = f"처리 오류: {str(e)}"
            
            # 오류도 CSV에 기록
            self.save_to_csv(news_item, 0.0, error_message, "처리 오류", processing_time, False)
            
            logger.error(f"❌ 뉴스 처리 실패: {e}")
            log_error_with_traceback("뉴스 처리 실패", e, {
                "title": news_item.get("title", "Unknown"),
                "stock_code": news_item.get("stock_code", "Unknown"),
                "url": news_item.get("url", "Unknown")
            })

    def init_daily_csv(self):
        """일일 CSV 파일 초기화"""
        try:
            # 파일이 없으면 헤더 생성
            if not self.daily_csv_file.exists():
                with open(self.daily_csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.csv_headers)
                logger.info(f"✅ 일일 CSV 파일 생성: {self.daily_csv_file}")
        except Exception as e:
            logger.error(f"❌ CSV 파일 초기화 실패: {e}")
    
    def save_to_csv(self, news_item: Dict, impact_score: float, reasoning: str, 
                   filter_stage: str, processing_time: float, telegram_sent: bool = False):
        """필터링 결과를 CSV 파일에 저장"""
        try:
            stock_code = news_item["stock_code"]
            stock_name = self.stock_names.get(stock_code, stock_code)
            stock_info = news_item.get("stock_info", {})
            
            # CSV 행 데이터 구성
            row_data = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # timestamp
                stock_code,
                stock_name,
                news_item["title"],
                news_item["content"][:500] + "..." if len(news_item["content"]) > 500 else news_item["content"],
                news_item["url"],
                news_item.get("source", ""),
                news_item["published_at"].strftime('%Y-%m-%d %H:%M:%S') if isinstance(news_item["published_at"], datetime) else news_item["published_at"],
                f"{impact_score:.3f}",
                reasoning[:200] + "..." if len(reasoning) > 200 else reasoning,
                f"{news_item.get('relevance_score', 0.0):.3f}",
                f"{news_item.get('similarity_score', 0.0):.3f}",
                filter_stage,
                stock_info.get("현재가", "N/A"),
                stock_info.get("등락률", "N/A"),
                "Yes" if telegram_sent else "No",
                f"{processing_time:.2f}s"
            ]
            
            # CSV 파일에 저장
            with open(self.daily_csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
            
            logger.debug(f"📊 CSV 저장 완료: {stock_name} - {news_item['title'][:30]}...")
            
        except Exception as e:
            logger.error(f"❌ CSV 저장 실패: {e}")
            log_error_with_traceback("CSV 저장 실패", e, {
                "stock_code": news_item.get("stock_code", ""),
                "title": news_item.get("title", "")[:50]
            })
    
    def save_high_impact_news_to_csv(self, news_item: Dict, impact_score: float, reasoning: str, processing_time: float):
        """고영향 뉴스 전용 CSV 저장"""
        try:
            # 고영향 뉴스 전용 CSV 파일 경로
            high_impact_csv_file = self.csv_output_dir / f"high_impact_news_{datetime.now().strftime('%Y%m%d')}.csv"
            
            # 파일이 없으면 헤더 생성
            if not high_impact_csv_file.exists():
                with open(high_impact_csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "alert_time", "stock_code", "stock_name", "title", "content_preview", 
                        "url", "source", "published_at", "impact_score", "reasoning", 
                        "current_price", "change_rate", "telegram_success", "processing_time"
                    ])
            
            stock_code = news_item["stock_code"]
            stock_name = self.stock_names.get(stock_code, stock_code)
            stock_info = news_item.get("stock_info", {})
            
            # 고영향 뉴스 CSV 행 데이터
            high_impact_row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # alert_time
                stock_code,
                stock_name,
                news_item["title"],
                news_item["content"][:200] + "..." if len(news_item["content"]) > 200 else news_item["content"],
                news_item["url"],
                news_item.get("source", ""),
                news_item["published_at"].strftime('%Y-%m-%d %H:%M:%S') if isinstance(news_item["published_at"], datetime) else news_item["published_at"],
                f"{impact_score:.3f}",
                reasoning[:300],  # 더 자세한 분석 내용
                stock_info.get("현재가", "N/A"),
                stock_info.get("등락률", "N/A"),
                "Yes",  # 고영향 뉴스는 항상 텔레그램 발송 시도
                f"{processing_time:.2f}s"
            ]
            
            # 고영향 뉴스 CSV에 저장
            with open(high_impact_csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(high_impact_row)
            
            logger.info(f"🚨 고영향 뉴스 CSV 저장: {stock_name} - {news_item['title'][:30]}...")
            
        except Exception as e:
            logger.error(f"❌ 고영향 뉴스 CSV 저장 실패: {e}")
    
    def log_high_impact_news_details(self, news_item: Dict, impact_score: float, reasoning: str):
        """고영향 뉴스 상세 로깅"""
        try:
            stock_code = news_item["stock_code"]
            stock_name = self.stock_names.get(stock_code, stock_code)
            stock_info = news_item.get("stock_info", {})
            
            # 구분선으로 눈에 띄게 로깅
            logger.info("=" * 80)
            logger.info("🚨🔥 고영향 뉴스 상세 분석 🔥🚨")
            logger.info("=" * 80)
            logger.info(f"📊 종목 정보:")
            logger.info(f"   • 종목명: {stock_name} ({stock_code})")
            logger.info(f"   • 현재가: {stock_info.get('현재가', 'N/A')}")
            logger.info(f"   • 등락률: {stock_info.get('등락률', 'N/A')}")
            logger.info(f"   • 거래량: {stock_info.get('거래량', 'N/A')}")
            logger.info(f"📰 뉴스 정보:")
            logger.info(f"   • 제목: {news_item['title']}")
            logger.info(f"   • 발행시간: {news_item['published_at']}")
            logger.info(f"   • 출처: {news_item.get('source', 'N/A')}")
            logger.info(f"   • URL: {news_item['url']}")
            logger.info(f"🔍 영향도 분석:")
            logger.info(f"   • 영향도 점수: {impact_score:.3f}/1.0")
            logger.info(f"   • 분석 결과: {reasoning}")
            logger.info(f"📱 알림 정보:")
            logger.info(f"   • 텔레그램 발송: 예정")
            logger.info(f"   • 크로마 DB 저장: 예정")
            logger.info(f"   • 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ 고영향 뉴스 상세 로깅 실패: {e}")
    
    def create_summary_csv(self) -> str:
        """일일 요약 CSV 생성"""
        try:
            summary_file = self.csv_output_dir / f"daily_summary_{datetime.now().strftime('%Y%m%d')}.csv"
            
            # 통계 계산
            stats = self.calculate_daily_stats()
            
            # 요약 CSV 생성
            with open(summary_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 헤더
                writer.writerow(["구분", "값"])
                
                # 통계 데이터
                writer.writerow(["전체 뉴스 수", stats["total_news"]])
                writer.writerow(["고영향 뉴스 수", stats["high_impact_news"]])
                writer.writerow(["텔레그램 알림 수", stats["telegram_alerts"]])
                writer.writerow(["평균 영향도", f"{stats['avg_impact']:.3f}"])
                writer.writerow(["처리 시간 (초)", f"{stats['total_processing_time']:.2f}"])
                writer.writerow(["생성 시간", datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                
                # 종목별 통계
                writer.writerow([])
                writer.writerow(["종목별 뉴스 수"])
                writer.writerow(["종목코드", "종목명", "뉴스수", "평균영향도"])
                
                for stock_code, stock_stats in stats["by_stock"].items():
                    stock_name = self.stock_names.get(stock_code, stock_code)
                    writer.writerow([
                        stock_code, 
                        stock_name, 
                        stock_stats["count"], 
                        f"{stock_stats['avg_impact']:.3f}"
                    ])
            
            logger.info(f"✅ 일일 요약 CSV 생성 완료: {summary_file}")
            return str(summary_file)
            
        except Exception as e:
            logger.error(f"❌ 요약 CSV 생성 실패: {e}")
            return ""
    
    def calculate_daily_stats(self) -> Dict:
        """일일 통계 계산"""
        try:
            if not self.daily_csv_file.exists():
                return {
                    "total_news": 0,
                    "high_impact_news": 0,
                    "telegram_alerts": 0,
                    "avg_impact": 0.0,
                    "total_processing_time": 0.0,
                    "by_stock": {}
                }
            
            stats = {
                "total_news": 0,
                "high_impact_news": 0,
                "telegram_alerts": 0,
                "total_impact": 0.0,
                "total_processing_time": 0.0,
                "by_stock": {}
            }
            
            with open(self.daily_csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    stats["total_news"] += 1
                    
                    # 영향도 통계
                    impact_score = float(row["impact_score"])
                    stats["total_impact"] += impact_score
                    
                    if impact_score >= 0.7:
                        stats["high_impact_news"] += 1
                    
                    # 텔레그램 알림 통계
                    if row["telegram_sent"] == "Yes":
                        stats["telegram_alerts"] += 1
                    
                    # 처리 시간 통계
                    processing_time = float(row["processing_time"].replace('s', ''))
                    stats["total_processing_time"] += processing_time
                    
                    # 종목별 통계
                    stock_code = row["stock_code"]
                    if stock_code not in stats["by_stock"]:
                        stats["by_stock"][stock_code] = {
                            "count": 0,
                            "total_impact": 0.0
                        }
                    
                    stats["by_stock"][stock_code]["count"] += 1
                    stats["by_stock"][stock_code]["total_impact"] += impact_score
            
            # 평균 계산
            stats["avg_impact"] = stats["total_impact"] / stats["total_news"] if stats["total_news"] > 0 else 0.0
            
            # 종목별 평균 계산
            for stock_code, stock_stats in stats["by_stock"].items():
                stock_stats["avg_impact"] = stock_stats["total_impact"] / stock_stats["count"]
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 일일 통계 계산 실패: {e}")
            return {
                "total_news": 0,
                "high_impact_news": 0,
                "telegram_alerts": 0,
                "avg_impact": 0.0,
                "total_processing_time": 0.0,
                "by_stock": {}
            }


def get_news_service():
    """뉴스 서비스 인스턴스 반환 (지연 초기화)"""
    global news_service_instance
    if news_service_instance is None:
        try:
            news_service_instance = NewsService()
            return news_service_instance
        except Exception as e:
            logger.error(f"뉴스 서비스 초기화 실패: {e}")
            raise
    return news_service_instance

async def save_latest_signal(message: str):
    """최근 알람 메시지 저장"""
    global latest_signal_message
    latest_signal_message = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "service": "news"
    }

# === FastAPI 엔드포인트 ===

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
            "service": "news"
        }

def is_peak_hours(current_time: datetime) -> bool:
    """뉴스 서비스 피크 시간대 확인 (7:30-9:30, 14:30-16:30)"""
    time_only = current_time.time()
    
    # 오전 피크: 7:30-9:30
    morning_start = datetime.strptime("07:30", "%H:%M").time()
    morning_end = datetime.strptime("09:30", "%H:%M").time()
    
    # 오후 피크: 14:30-16:30  
    afternoon_start = datetime.strptime("14:30", "%H:%M").time()
    afternoon_end = datetime.strptime("16:30", "%H:%M").time()
    
    return (morning_start <= time_only <= morning_end) or (afternoon_start <= time_only <= afternoon_end)

def should_execute_now() -> Tuple[bool, str]:
    """현재 실행할 시간인지 판단"""
    global last_execution_time
    
    now = datetime.now()
    
    # 첫 실행인 경우
    if last_execution_time is None:
        return True, "첫 실행"
    
    # 마지막 실행으로부터 경과 시간 계산
    time_diff = (now - last_execution_time).total_seconds()
    
    # 시간대별 실행 간격 확인
    if is_peak_hours(now):
        # 피크 시간대: 10분 간격
        required_interval = 600  # 10분 = 600초
        interval_name = "피크 시간대 10분 간격"
    else:
        # 일반 시간대: 1시간 간격
        required_interval = 3600  # 1시간 = 3600초
        interval_name = "일반 시간대 1시간 간격"
    
    if time_diff >= required_interval:
        return True, f"{interval_name} - 마지막 실행: {last_execution_time.strftime('%H:%M')}"
    else:
        remaining = int(required_interval - time_diff)
        return False, f"{interval_name} - {remaining}초 후 실행 가능"

async def execute_news_crawling() -> Dict:
    """뉴스 크롤링 실행"""
    global last_execution_time
    try:
        logger.info("🚀 뉴스 크롤링 실행 시작")
        
        # 뉴스 서비스 인스턴스 확인 및 초기화
        global news_service_instance
        if news_service_instance is None:
            logger.warning("⚠️ 뉴스 서비스 인스턴스가 없음 - 지연 초기화 시도")
            try:
                news_service_instance = get_news_service()
                logger.info("✅ 뉴스 서비스 지연 초기화 완료")
            except Exception as e:
                logger.error(f"❌ 뉴스 서비스 지연 초기화 실패: {e}")
                return {"success": False, "error": f"서비스 초기화 실패: {str(e)}"}
        
        # 모든 종목에 대해 뉴스 크롤링 실행
        total_news = 0
        processed_stocks = []
        
        for stock_code in news_service_instance.stock_codes:
            try:
                # 종목별 뉴스 크롤링
                logger.info(f"📰 {stock_code} 뉴스 크롤링 시작")
                news_list = news_service_instance.crawl_naver_finance_news(stock_code, pages=1, size=3)
        
                if news_list:
                    # 각 뉴스에 대해 필터링 및 분석
                    for news_item in news_list:
                        try:
                            # 3단계 필터링
                            is_filtered, filter_reason, filter_result = await news_service_instance.check_three_stage_filtering(news_item)
        
                            if not is_filtered:
                                # RAG 방식 영향도 평가
                                impact_score, reasoning = await news_service_instance.evaluate_impact_with_rag(news_item)
        
                                # 고영향도 뉴스인 경우 알림 전송
                                if impact_score >= news_service_instance.impact_threshold:
                                    await news_service_instance.send_alert(news_item, impact_score, reasoning)
                                    logger.info(f"📢 고영향도 뉴스 알림 전송: {news_item['title'][:30]}...")
                                
                                total_news += 1
                                
                        except Exception as e:
                            logger.error(f"❌ 뉴스 처리 실패: {e}")
                            continue
                
                processed_stocks.append(stock_code)
                logger.info(f"✅ {stock_code} 뉴스 크롤링 완료: {len(news_list)}개")
                
            except Exception as e:
                logger.error(f"❌ {stock_code} 뉴스 크롤링 실패: {e}")
                continue
        
        # 실행 시간 업데이트
        last_execution_time = datetime.now()
        
        result = {
            "success": True,
            "processed_stocks": len(processed_stocks),
            "total_news": total_news,
            "execution_time": last_execution_time.isoformat(),
        }
        
        logger.info(f"✅ 뉴스 크롤링 완료: {len(processed_stocks)}개 종목, {total_news}개 뉴스")
        return result
        
    except Exception as e:
        logger.error(f"❌ 뉴스 크롤링 실행 실패: {e}")
        return {"success": False, "error": str(e)}

# FastAPI 엔드포인트 추가
@app.post("/set-user/{user_id}")
async def set_user_id_endpoint(user_id: str):
    """사용자 ID 설정 엔드포인트"""
    try:
        news_service = get_news_service()
        await news_service.set_user_id(user_id)
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
        news_service = get_news_service()
        await news_service.set_user_id(user_id)
        
        # 사용자 설정 조회
        user_config = await news_service.user_config_manager.get_user_config(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "config": {
                "stocks": user_config.get("stocks", []),
                "news_similarity_threshold": user_config.get("news_similarity_threshold"),
                "news_impact_threshold": user_config.get("news_impact_threshold")
            }
        }
    except Exception as e:
        logger.error(f"❌ 사용자 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="사용자 설정 조회에 실패했습니다")

@app.post("/execute")
async def execute_news_analysis(request: Request):
    """뉴스 분석 실행 - 사용자별 동적 처리"""
    try:
        # Header에서 user_id 추출 (문자열로 처리)
        user_id = request.headers.get("X-User-ID", "1")
        
        # 서비스 인스턴스의 user_id 동적 업데이트
        service = get_news_service()
        if service.current_user_id != user_id:
            await service.set_user_id(user_id)
            logger.info(f"🔄 사용자 컨텍스트 변경: {user_id}")
        
        # 뉴스 크롤링 실행
        result = await execute_news_crawling()
        return result
        
    except Exception as e:
        logger.error(f"❌ 뉴스 분석 실행 실패: {e}")
        return {"success": False, "error": str(e)}

@app.post("/check-schedule")
async def check_schedule():
    """오케스트레이터 체크 신호 수신 - 독립적으로 실행 시간 판단"""
    try:
        should_run, reason = should_execute_now()
        
        if should_run:
            # 실행 조건 만족 시 뉴스 크롤링 실행
            result = await execute_news_crawling()
            
            if result["success"]:
                return {
                    "executed": True,
                    "message": f"뉴스 크롤링 실행 완료 - {reason}",
                    "details": result
                }
            else:
                return {
                    "executed": False,
                    "message": f"뉴스 크롤링 실행 실패 - {result.get('error', 'Unknown')}",
                    "reason": reason
                }
        else:
            return {
                "executed": False,
                "message": reason,
                "next_execution": "조건 만족 시"
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
            logger.info("✅ 사용자 개인화 로더 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 사용자 개인화 로더 초기화 실패: {e}")
            self.user_config_loader = None

    async def get_personalized_config(self, user_id: str) -> Dict[str, Any]:
        """사용자별 개인화 설정 조회"""
        try:
            if not self.user_config_loader:
                logger.warning("⚠️ 사용자 설정 로더가 초기화되지 않음 - 기본값 사용")
                return self._get_default_config()
            
            # 캐시에서 먼저 확인
            if user_id in self.personalized_configs:
                return self.personalized_configs[user_id]
            
            # API를 통해 사용자 설정 로드
            config = await self.user_config_loader.load_user_config(user_id)
            if config:
                # 뉴스 서비스에 특화된 설정 추출
                personalized_config = {
                    "user_id": user_id,
                    "stocks": [stock["stock_code"] for stock in config.get("stocks", [])],
                    "model_type": config.get("model_type", "hyperclova"),
                    "news_similarity_threshold": config.get("news_similarity_threshold", 0.7),
                    "news_impact_threshold": config.get("news_impact_threshold", 0.8),
                    "active_service": config.get("active_services", {}).get("news_service", 0) == 1
                }
                
                # 캐시에 저장
                self.personalized_configs[user_id] = personalized_config
                logger.info(f"✅ 사용자 개인화 설정 로드 완료: {user_id}")
                return personalized_config
            else:
                logger.warning(f"⚠️ 사용자 설정을 찾을 수 없음: {user_id} - 기본값 사용")
                return self._get_default_config()
                
        except Exception as e:
            logger.error(f"❌ 사용자 개인화 설정 로드 실패: {user_id} - {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "user_id": "default",
            "stocks": ["005930", "000660"],  # 기본 종목: 삼성전자, SK하이닉스
            "model_type": "hyperclova",
            "news_similarity_threshold": 0.7,
            "news_impact_threshold": 0.8,
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
            logger.error(f"❌ 사용자별 분석 필요성 확인 실패: {user_id}, {stock_code} - {e}")
            return True  # 오류 시 기본적으로 분석 진행

    async def get_user_analysis_model(self, user_id: str) -> str:
        """사용자가 선택한 AI 모델 반환"""
        try:
            config = await self.get_personalized_config(user_id)
            return config.get("model_type", "hyperclova")
        except Exception as e:
            logger.error(f"❌ 사용자 AI 모델 조회 실패: {user_id} - {e}")
            return "hyperclova"

    def clear_user_cache(self, user_id: Optional[str] = None):
        """사용자 설정 캐시 클리어"""
        if user_id:
            self.personalized_configs.pop(user_id, None)
            if self.user_config_loader:
                self.user_config_loader.clear_cache(user_id)
            logger.debug(f"🧹 사용자 설정 캐시 클리어: {user_id}")
        else:
            self.personalized_configs.clear()
            if self.user_config_loader:
                self.user_config_loader.clear_cache()
            logger.debug("🧹 모든 사용자 설정 캐시 클리어")

def main():
    """메인 함수 - API 서버만 시작, 실제 서비스 로직은 스케줄링에 따라 실행"""
    try:
        logger.info("🚀 뉴스 서비스 API 서버 시작 (포트: 8001)")
        logger.info("📋 스케줄링 정책:")
        logger.info("   • 피크시간(7:30-9:30, 14:30-16:30): 10분 간격")
        logger.info("   • 일반시간: 1시간 간격")
        
        # FastAPI 서버 실행
        uvicorn.run(app, host="0.0.0.0", port=8001)
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"뉴스 서비스 시작 실패 [{error_type}]: {e}")
        log_error_with_traceback("뉴스 서비스 시작 실패", e)
        raise


if __name__ == "__main__":
    main()