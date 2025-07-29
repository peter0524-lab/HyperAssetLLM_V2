"""
주식 분석 서비스 로컬 개발 환경 설정
"""

import os
from typing import Dict, Any

# 기본 환경 변수 설정
DEFAULT_ENV_VARS: Dict[str, Any] = {
    # 기본 설정
    "ENV": "development",
    "DEBUG": True,
    "LOG_LEVEL": "INFO",
    # 타겟 종목
    "TARGET_STOCK_CODE": "006800",
    "TARGET_STOCK_NAME": "미래에셋증권",
    # 서비스 포트 설정
    "ORCHESTRATOR_HOST": "0.0.0.0",
    "ORCHESTRATOR_PORT": 8000,
    "NEWS_SERVICE_PORT": 8001,
    "DISCLOSURE_SERVICE_PORT": 8002,
    "CHART_SERVICE_PORT": 8003,
    "NOTIFICATION_SERVICE_PORT": 8004,
    "REPORT_SERVICE_PORT": 8005,
    "ANALYSIS_SERVICE_PORT": 8006,
    "MONITORING_SERVICE_PORT": 8007,
    # MySQL 데이터베이스 설정 (AWS RDS)
    "DATABASE_HOST": "database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com",
    "DATABASE_PORT": 3306,
    "DATABASE_USER": "admin",
    "DATABASE_PASSWORD": "Peter0524!",
    "DATABASE_NAME": "HyperAsset",
    "DATABASE_TIMEZONE": "+09:00",
    "DATABASE_CONNECTION_LIMIT": 100,
    "DATABASE_SSL_DISABLED": False,
    "DATABASE_SSL_VERIFY_CERT": False,
    # ChromaDB 설정 (PersistentClient 방식 - 별도 서버 포트 불필요)
    "CHROMADB_HOST": "localhost",
    "CHROMADB_PERSIST_DIRECTORY": "./data/chroma",
    # 벡터 데이터베이스 컬렉션 이름
    "VECTOR_DB_HIGH_IMPACT_NEWS": "high_impact_news",
    "VECTOR_DB_PAST_EVENTS": "past_events",
    "VECTOR_DB_DAILY_NEWS": "daily_news",
    "VECTOR_DB_KEYWORDS": "keywords",
    # HyperCLOVA X API 설정
    #이태환 "HYPERCLOVA_API_KEY": "nv-f5e893309c02432ab1a2bad85faa57e0UUAO",
    "HYPERCLOVA_API_KEY": "nv-b8935535a68442e3bce731a356b119a4Xbzy", #이거 김민겸꺼
    "HYPERCLOVA_API_URL": "https://clovastudio.stream.ntruss.com/testapp/v3/chat-completions/HCX-005",
    "HYPERCLOVA_MAX_TOKENS": 2048,
    "HYPERCLOVA_TEMPERATURE": 0.3,
    "HYPERCLOVA_TOP_P": 0.8,
    # Gemini API 설정
    "GEMINI_API_KEY": "",  # Google AI Studio에서 발급
    "GEMINI_MODEL": "gemini-2.0-flash-exp",
    "GEMINI_MAX_TOKENS": 2048,
    "GEMINI_TEMPERATURE": 0.3,
    # OpenAI API 설정
    "OPENAI_API_KEY": "",  # OpenAI에서 발급
    "OPENAI_MODEL": "gpt-4o-mini",
    "OPENAI_MAX_TOKENS": 2048,
    "OPENAI_TEMPERATURE": 0.3,
    # Claude API 설정
    "CLAUDE_API_KEY": "",  # Anthropic에서 발급
    "CLAUDE_MODEL": "claude-3-5-sonnet-20241022",
    "CLAUDE_MAX_TOKENS": 2048,
    "CLAUDE_TEMPERATURE": 0.3,
    # Grok API 설정
    "GROK_API_KEY": "",  # xAI에서 발급
    "GROK_MODEL": "grok-beta",
    "GROK_MAX_TOKENS": 2048,
    "GROK_TEMPERATURE": 0.3,
    # DART API 설정
    #"DART_API_KEY": "c734e72eb6cdc78a5677e7650e050652f2e78f0b",
    "DART_API_KEY": "db8f419d48d03346fc42b2f071e155aca0cd6248",
    "DART_API_URL": "https://opendart.fss.or.kr/api",
    # KIS API 설정
    #이태환 : "KIS_APP_KEY": "PSFQSGJo78mtRSTBkFBJGB5pdgos8eSYYeyE",
    "KIS_APP_KEY": "PS6bXXjjR7M9PQFtcBGJFtou5RjDkDVGQxU2",
    #이태환 : "KIS_APP_SECRET": "qYWWTBehthpn+lK3yiPkpmAYXjjwC6qbxGx5/CfUSUmRwZGXI6wIeEnDK0h0RT87ilVUGR5zQGLgjoAqkTtU4y/L3AB/f6ur3Nhb2ngGWkEUbRWuN2gDqJY7FYevk3/BHDXYK8paTOHQfXfOzwOys0oFKtP013Ju931bJ7X6nzyNeTlrv1s=",
    "KIS_APP_SECRET": "bGip//guXNjVFYNUliUemp0YJiG36KX6mSsTquuDx2ySmJHndzH4pt4SUsWSQuB6h9YP5CwfCc6dokaKJ0yM8Z+4zRRW1A7GlOwsJ1jv5d8UUvEhusLCenu0BPkX/0kv9PAxpzOU/K6dmTSfow7eDHTvWT8k3MuzPBF7A+3jny2t3zbewqs=",
    "KIS_API_URL": "https://openapi.koreainvestment.com:9443",  # 실전투자 URL
    "KIS_WS_URL": "ws://ops.koreainvestment.com:21000",  # 실전투자 웹소켓 URL
    "KIS_PAPER_TRADING": False,  # 실전투자 사용
    # 텔레그램 봇 설정
    #TELEGRAM_BOT_TOKEN": "8019204369:AAH343PfdI_JKnr12OB3wafHYb-nNfNaWnM",
    #"TELEGRAM_BOT_TOKEN": "7804706615:AAF_1WH5LZFa5mWktH3CZiHHKf98WRp4Buo",
    "TELEGRAM_BOT_TOKEN": "7888091225:AAHMqbCQV4_so7VqDeLqbWaiGTvVyQ698-M",
    #"TELEGRAM_CHAT_ID":"-4950321224",  그룹 채팅 ID 
    "TELEGRAM_CHAT_ID": "-1002819230740",  # 그룹 채팅 ID
    #"TELEGRAM_CHAT_ID": "6173086855",
    
    "TELEGRAM_PARSE_MODE": "HTML",
    # 임베딩 모델 설정
    "EMBEDDING_MODEL_NAME": "jhgan/ko-sroberta-multitask",  # 더 정확한 한국어 임베딩 모델
    "EMBEDDING_MODEL_DEVICE": "cpu",
    "EMBEDDING_BATCH_SIZE": 32,
    # 뉴스 크롤링 설정
    "NEWS_CRAWL_INTERVAL_MARKET": 5,
    "NEWS_CRAWL_INTERVAL_AFTER": 60,
    "NEWS_CRAWL_PAGES": 2,
    "NEWS_CRAWL_SIZE": 3,
    "NEWS_SIMILARITY_THRESHOLD": 1.1,  # 벡터 유사도 임계값을 0.95로 상향 조정
    "NEWS_IMPACT_THRESHOLD": 0.5,  # 순수 RAG 방식: 중간 이상 영향도 뉴스만 처리 (0.0-1.0 스케일)
    "NEWS_RELEVANCE_THRESHOLD": 0.6,  # 종목 관련성 임계값
    "NEWS_API_CALL_INTERVAL": 1,  # API 호출 간격 (초)
    "NEWS_HIGH_IMPACT_ONLY": True,  # 고영향도 뉴스만 API 호출
    # 차트 분석 설정
    "CHART_ANALYSIS_INTERVAL": 30,
    "CHART_WEBSOCKET_TIMEOUT": 30,
    "CHART_INDICATOR_PERIOD": 20,
    "CHART_VOLUME_THRESHOLD": 10000000,
    "CHART_PRICE_CHANGE_THRESHOLD": 0.1,
    # 공시 설정
    "DISCLOSURE_CHECK_INTERVAL": 3600,
    "DISCLOSURE_KEYWORDS": "증자,감자,배당,인수,합병,분할,상장,폐지,투자",
    # 알림 설정
    "NOTIFICATION_ENABLED": True,
    "NOTIFICATION_RATE_LIMIT": 10,
    "NOTIFICATION_RETRY_COUNT": 3,
    "NOTIFICATION_RETRY_DELAY": 5,
    # 보고서 설정
    "REPORT_GENERATION_DAY": 6,  # 일요일
    "REPORT_GENERATION_HOUR": 20,
    "REPORT_GENERATION_MINUTE": 0,
    "REPORT_RESEARCH_PAGES": 5,
    # 한국 시장 시간 설정
    "MARKET_OPEN_HOUR": 9,
    "MARKET_OPEN_MINUTE": 0,
    "MARKET_CLOSE_HOUR": 15,
    "MARKET_CLOSE_MINUTE": 30,
    "MARKET_TIMEZONE": "Asia/Seoul",
    # 데이터 보존 설정
    "DATA_RETENTION_DAYS": 30,
    "DAILY_NEWS_CLEANUP_HOUR": 0,
    "DAILY_NEWS_CLEANUP_MINUTE": 0,
    # 시스템 설정
    "SYSTEM_HEALTH_CHECK_INTERVAL": 60,
    "SYSTEM_MEMORY_LIMIT": "8GB",
    "SYSTEM_CPU_LIMIT": 80,
    # 로그 설정
    "LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "LOG_DATE_FORMAT": "%Y-%m-%d %H:%M:%S",
    "LOG_FILE_PATH": "./data/logs",
    "LOG_MAX_SIZE": "10MB",
    "LOG_BACKUP_COUNT": 5,
    # 큐 시스템 설정
    "QUEUE_REDIS_HOST": "localhost",
    "QUEUE_REDIS_PORT": 6379,
    "QUEUE_REDIS_DB": 0,
    "QUEUE_HIGH_PRIORITY": "high_priority",
    "QUEUE_NORMAL_PRIORITY": "normal_priority",
    "QUEUE_LOW_PRIORITY": "low_priority",
    # 보안 설정
    "SECRET_KEY": "your-secret-key-here",
    "API_KEY_HEADER": "X-API-Key",
    "CORS_ORIGINS": "http://localhost:3000,http://localhost:8000",
    # 외부 API 호출 제한
    "API_RATE_LIMIT": 100,
    "API_RATE_LIMIT_WINDOW": 3600,
    "API_TIMEOUT": 30,
    "API_RETRY_COUNT": 3,
    "API_RETRY_DELAY": 1,
    # 개발 도구 설정
    "RELOAD_ON_CHANGE": True,
    "SHOW_DOCS": True,
    "ENABLE_PROFILING": False,
}


def load_env_vars() -> None:
    """환경 변수를 시스템에 로드"""
    for key, value in DEFAULT_ENV_VARS.items():
        if key not in os.environ:
            os.environ[key] = str(value)


def get_env_var(key: str, default: Any = None) -> str:
    """환경 변수 값 가져오기"""
    value = os.getenv(key)
    return value if value is not None else str(default)


def get_int_env_var(key: str, default: int = 0) -> int:
    """정수형 환경 변수 값 가져오기"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_bool_env_var(key: str, default: bool = False) -> bool:
    """불린형 환경 변수 값 가져오기"""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


def get_float_env_var(key: str, default: float = 0.0) -> float:
    """실수형 환경 변수 값 가져오기"""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_list_env_var(key: str, default: str = "", separator: str = ",") -> list:
    """리스트형 환경 변수 값 가져오기"""
    value = os.getenv(key, default) # 환경변수에서 읽어옴
    if not value:
        return []
    return [item.strip() for item in value.split(separator) if item.strip()] # 쉼표로 분리하고 공백제거


# 초기화 시 환경 변수 로드
load_env_vars()


def get_config() -> Dict[str, Any]:
    """전체 설정 딕셔너리 반환"""
    return {
        # 기본 설정
        "env": get_env_var("ENV", "development"),
        "debug": get_bool_env_var("DEBUG", True),
        "log_level": get_env_var("LOG_LEVEL", "INFO"),
        # 타겟 종목
        "target_stock_code": get_env_var("TARGET_STOCK_CODE", "006800"),
        "target_stock_name": get_env_var("TARGET_STOCK_NAME", "미래에셋증권"),
        # 서비스 포트 설정
        "orchestrator": {
            "host": get_env_var("ORCHESTRATOR_HOST", "0.0.0.0"),
            "port": get_int_env_var("ORCHESTRATOR_PORT", 8000),
        },
        "news_service_port": get_int_env_var("NEWS_SERVICE_PORT", 8001),
        "disclosure_service_port": get_int_env_var("DISCLOSURE_SERVICE_PORT", 8002),
        "chart_service_port": get_int_env_var("CHART_SERVICE_PORT", 8003),
        "notification_service_port": get_int_env_var("NOTIFICATION_SERVICE_PORT", 8004),
        "report_service_port": get_int_env_var("REPORT_SERVICE_PORT", 8005),
        "analysis_service_port": get_int_env_var("ANALYSIS_SERVICE_PORT", 8006),
        "monitoring_service_port": get_int_env_var("MONITORING_SERVICE_PORT", 8007),
        # MySQL 데이터베이스 설정
        "mysql": {
            "host": get_env_var("DATABASE_HOST", "127.0.0.1"),
            "port": get_int_env_var("DATABASE_PORT", 3306),
            "user": get_env_var("DATABASE_USER", "root"),
            "password": get_env_var("DATABASE_PASSWORD", "peter0524!"),
            "database": get_env_var("DATABASE_NAME", "backendTest"),
            "timezone": get_env_var("DATABASE_TIMEZONE", "+09:00"),
            "connection_limit": get_int_env_var("DATABASE_CONNECTION_LIMIT", 100),
        },
        # ChromaDB 설정
        "chromadb": {
            "host": get_env_var("CHROMADB_HOST", "localhost"),
            "persist_directory": get_env_var(
                "CHROMADB_PERSIST_DIRECTORY", "./data/chroma"
            ),
        },
        # 벡터 데이터베이스 컬렉션 이름
        "vector_db": {
            "high_impact_news": get_env_var(
                "VECTOR_DB_HIGH_IMPACT_NEWS", "high_impact_news"
            ),
            "past_events": get_env_var("VECTOR_DB_PAST_EVENTS", "past_events"),
            "daily_news": get_env_var("VECTOR_DB_DAILY_NEWS", "daily_news"),
            "keywords": get_env_var("VECTOR_DB_KEYWORDS", "keywords"),
        },
        # HyperCLOVA X API 설정
        "hyperclova": {
            "api_key": get_env_var(
                "HYPERCLOVA_API_KEY", "nv-b8935535a68442e3bce731a356b119a4Xbzy"
            ),
            "api_url": get_env_var(
                "HYPERCLOVA_API_URL",
                "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003",
            ),
            "max_tokens": get_int_env_var("HYPERCLOVA_MAX_TOKENS", 2048),
            "temperature": get_float_env_var("HYPERCLOVA_TEMPERATURE", 0.3),
            "top_p": get_float_env_var("HYPERCLOVA_TOP_P", 0.8),
        },
        # DART API 설정
        "dart": {
            "api_key": get_env_var(
                "DART_API_KEY", "c734e72eb6cdc78a5677e7650e050652f2e78f0b"
            ),
            "api_url": get_env_var("DART_API_URL", "https://opendart.fss.or.kr/api"),
        },
        # KIS API 설정
        "kis_api": {
            "app_key": get_env_var(
                "KIS_APP_KEY", "PS6bXXjjR7M9PQFtcBGJFtou5RjDkDVGQxU2"
            ),
            "app_secret": get_env_var(
                "KIS_APP_SECRET","bGip//guXNjVFYNUliUemp0YJiG36KX6mSsTquuDx2ySmJHndzH4pt4SUsWSQuB6h9YP5CwfCc6dokaKJ0yM8Z+4zRRW1A7GlOwsJ1jv5d8UUvEhusLCenu0BPkX/0kv9PAxpzOU/K6dmTSfow7eDHTvWT8k3MuzPBF7A+3jny2t3zbewqs=",
            ),
            "api_url": get_env_var(
                "KIS_API_URL", "https://openapi.koreainvestment.com:9443"
            ),
            "ws_url": get_env_var("KIS_WS_URL", "ws://ops.koreainvestment.com:21000"),
            "paper_trading": get_bool_env_var("KIS_PAPER_TRADING", False),
        },
        # 텔레그램 봇 설정
        "telegram": {
            "bot_token": get_env_var(
                "TELEGRAM_BOT_TOKEN", "7804706615:AAF_1WH5LZFa5mWktH3CZiHHKf98WRp4Buo"
            ),
            "chat_id": get_env_var("TELEGRAM_CHAT_ID", "-1002819230740"),
            "parse_mode": get_env_var("TELEGRAM_PARSE_MODE", "HTML"),
        },
        # 임베딩 모델 설정
        "embedding": {
            "model_name": get_env_var("EMBEDDING_MODEL_NAME", "jhgan/ko-sbert-nli"),
            "device": get_env_var("EMBEDDING_MODEL_DEVICE", "cpu"),
            "batch_size": get_int_env_var("EMBEDDING_BATCH_SIZE", 32),
        },
        # 뉴스 크롤링 설정
        "news": {
            "crawl_interval_market": get_int_env_var("NEWS_CRAWL_INTERVAL_MARKET", 5),
            "crawl_interval_after": get_int_env_var("NEWS_CRAWL_INTERVAL_AFTER", 60),
            "crawl_pages": get_int_env_var("NEWS_CRAWL_PAGES", 10),
            "crawl_size": get_int_env_var("NEWS_CRAWL_SIZE", 20),
            "similarity_threshold": get_float_env_var("NEWS_SIMILARITY_THRESHOLD", 0.95),
            "impact_threshold": get_float_env_var("NEWS_IMPACT_THRESHOLD", 0.4),
        },
        # 차트 분석 설정
        "chart": {
            "analysis_interval": get_int_env_var("CHART_ANALYSIS_INTERVAL", 30),
            "websocket_timeout": get_int_env_var("CHART_WEBSOCKET_TIMEOUT", 30),
            "indicator_period": get_int_env_var("CHART_INDICATOR_PERIOD", 20),
            "volume_threshold": get_int_env_var("CHART_VOLUME_THRESHOLD", 10000000),
            "price_change_threshold": get_float_env_var(
                "CHART_PRICE_CHANGE_THRESHOLD", 0.1
            ),
        },
        # 공시 설정
        "disclosure": {
            "check_interval": get_int_env_var("DISCLOSURE_CHECK_INTERVAL", 3600),
            "keywords": get_list_env_var(
                "DISCLOSURE_KEYWORDS", "증자,감자,배당,인수,합병,분할,상장,폐지,투자"
            ),
        },
        # 알림 설정
        "notification": {
            "enabled": get_bool_env_var("NOTIFICATION_ENABLED", True),
            "rate_limit": get_int_env_var("NOTIFICATION_RATE_LIMIT", 10),
            "retry_count": get_int_env_var("NOTIFICATION_RETRY_COUNT", 3),
            "retry_delay": get_int_env_var("NOTIFICATION_RETRY_DELAY", 5),
        },
        # 보고서 설정
        "report": {
            "generation_day": get_int_env_var("REPORT_GENERATION_DAY", 6),
            "generation_hour": get_int_env_var("REPORT_GENERATION_HOUR", 20),
            "generation_minute": get_int_env_var("REPORT_GENERATION_MINUTE", 0),
            "research_pages": get_int_env_var("REPORT_RESEARCH_PAGES", 5),
        },
        # 한국 시장 시간 설정
        "market": {
            "open_hour": get_int_env_var("MARKET_OPEN_HOUR", 9),
            "open_minute": get_int_env_var("MARKET_OPEN_MINUTE", 0),
            "close_hour": get_int_env_var("MARKET_CLOSE_HOUR", 15),
            "close_minute": get_int_env_var("MARKET_CLOSE_MINUTE", 30),
            "timezone": get_env_var("MARKET_TIMEZONE", "Asia/Seoul"),
        },
        # 데이터 보존 설정
        "data": {
            "retention_days": get_int_env_var("DATA_RETENTION_DAYS", 30),
            "daily_news_cleanup_hour": get_int_env_var("DAILY_NEWS_CLEANUP_HOUR", 0),
            "daily_news_cleanup_minute": get_int_env_var(
                "DAILY_NEWS_CLEANUP_MINUTE", 0
            ),
        },
        # 시스템 설정
        "system": {
            "health_check_interval": get_int_env_var(
                "SYSTEM_HEALTH_CHECK_INTERVAL", 60
            ),
            "memory_limit": get_env_var("SYSTEM_MEMORY_LIMIT", "8GB"),
            "cpu_limit": get_int_env_var("SYSTEM_CPU_LIMIT", 80),
        },
        # 로그 설정
        "logging": {
            "format": get_env_var(
                "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            "date_format": get_env_var("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
            "file_path": get_env_var("LOG_FILE_PATH", "./data/logs"),
            "max_size": get_env_var("LOG_MAX_SIZE", "10MB"),
            "backup_count": get_int_env_var("LOG_BACKUP_COUNT", 5),
        },
    }


# 지원되는 환경 변수 상수 정의
LOCAL_ENV = get_config()
