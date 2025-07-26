#!/usr/bin/env python3
"""
간단한 실행 버전 - 뉴스 서비스만 실행
환경변수와 복잡한 의존성 없이 기본 기능 테스트
"""

import os
import sys
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def set_default_environment():
    """기본 환경변수 설정"""
    default_vars = {
        "TARGET_STOCK_CODE": "006800",
        "DATABASE_HOST": "gcp-db-mysql.c54b7gzqp4hq.ap-northeast-2.rds.amazonaws.com",
        "DATABASE_USER": "backendtest",
        "DATABASE_PASSWORD": "qlzh0807!",
        "DATABASE_NAME": "backendTest",
        "DATABASE_PORT": "3306",
        "HYPERCLOVA_API_KEY": "nv-a835f0aa82b7477f87792ae2e48941afZsnZ",
        "DART_API_KEY": "c734e72eb6cdc78a5677e7650e050652f2e78f0b",
        "TELEGRAM_BOT_TOKEN": "7804706615:AAF_1WH5LZFa5mWktH3CZiHHKf98WRp4Buo",
        "TELEGRAM_CHAT_ID": "1002263561615",
        "CHROMADB_PERSIST_DIRECTORY": "./data/chroma",
        "LOG_LEVEL": "INFO",
    }

    for key, value in default_vars.items():
        if key not in os.environ:
            os.environ[key] = value

    logger.info("기본 환경변수 설정 완료")


def check_packages():
    """필수 패키지 확인"""
    try:
        import requests
        import pymysql
        import fastapi
        import uvicorn

        logger.info("✅ 필수 패키지 확인 완료")
        return True
    except ImportError as e:
        logger.error(f"❌ 패키지 누락: {e}")
        return False


def create_directories():
    """필요한 디렉토리 생성"""
    dirs = ["data", "data/chroma", "logs"]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
    logger.info("✅ 디렉토리 생성 완료")


def test_database_connection():
    """데이터베이스 연결 테스트"""
    try:
        import pymysql.cursors

        conn = pymysql.connect(
            host=os.environ["DATABASE_HOST"],
            user=os.environ["DATABASE_USER"],
            password=os.environ["DATABASE_PASSWORD"],
            database=os.environ["DATABASE_NAME"],
            port=int(os.environ["DATABASE_PORT"]),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            logger.info("✅ 데이터베이스 연결 성공")
            return True
        else:
            logger.error("❌ 데이터베이스 연결 실패")
            return False

    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 에러: {e}")
        return False


def create_basic_tables():
    """기본 테이블 생성"""
    try:
        import pymysql.cursors

        conn = pymysql.connect(
            host=os.environ["DATABASE_HOST"],
            user=os.environ["DATABASE_USER"],
            password=os.environ["DATABASE_PASSWORD"],
            database=os.environ["DATABASE_NAME"],
            port=int(os.environ["DATABASE_PORT"]),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        cursor = conn.cursor()

        # 뉴스 테이블 생성
        create_news_table = """
        CREATE TABLE IF NOT EXISTS news (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            title VARCHAR(1000) NOT NULL,
            content TEXT NOT NULL,
            url VARCHAR(1000) NOT NULL,
            source VARCHAR(100) NOT NULL,
            published_at DATETIME NOT NULL,
            impact_score DECIMAL(3,2) DEFAULT 0.00,
            reasoning TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_stock_code (stock_code),
            INDEX idx_created_at (created_at),
            UNIQUE KEY unique_url (url)
        );
        """

        cursor.execute(create_news_table)
        conn.commit()
        cursor.close()
        conn.close()

        logger.info("✅ 기본 테이블 생성 완료")
        return True

    except Exception as e:
        logger.error(f"❌ 테이블 생성 실패: {e}")
        return False


def run_simple_news_service():
    """간단한 뉴스 서비스 실행"""
    try:
        from fastapi import FastAPI
        import uvicorn
        import requests
        from bs4 import BeautifulSoup
        import pymysql.cursors
        from datetime import datetime

        app = FastAPI(title="Simple News Service", version="1.0.0")

        @app.get("/")
        async def root():
            return {
                "message": "Simple News Service",
                "status": "running",
                "timestamp": datetime.now().isoformat(),
            }

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        @app.get("/test-crawl")
        async def test_crawl():
            """간단한 크롤링 테스트"""
            try:
                # 네이버 금융 뉴스 간단 크롤링
                stock_code = "006800"
                url = (
                    f"https://finance.naver.com/item/news_news.naver?code={stock_code}"
                )

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }

                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, "html.parser")

                # 첫 번째 뉴스 제목 추출
                news_items = soup.find_all("a", class_="tit")
                if news_items:
                    first_news = news_items[0].get_text().strip()
                    return {
                        "status": "success",
                        "sample_news": first_news,
                        "crawled_at": datetime.now().isoformat(),
                    }
                else:
                    return {"status": "no_news_found"}

            except Exception as e:
                return {"status": "error", "error": str(e)}

        @app.get("/test-db")
        async def test_db():
            """데이터베이스 테스트"""
            try:
                conn = pymysql.connect(
                    host=os.environ["DATABASE_HOST"],
                    user=os.environ["DATABASE_USER"],
                    password=os.environ["DATABASE_PASSWORD"],
                    database=os.environ["DATABASE_NAME"],
                    port=int(os.environ["DATABASE_PORT"]),
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )

                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM news")
                result = cursor.fetchone()
                count = result['count'] if result else 0
                cursor.close()
                conn.close()

                return {
                    "status": "success",
                    "news_count": count,
                    "tested_at": datetime.now().isoformat(),
                }

            except Exception as e:
                return {"status": "error", "error": str(e)}

        logger.info("🚀 Simple News Service 시작 중...")
        logger.info("📱 웹 브라우저에서 http://localhost:8001 접속하세요")
        logger.info("🧪 테스트 URL:")
        logger.info("   - http://localhost:8001/test-crawl (크롤링 테스트)")
        logger.info("   - http://localhost:8001/test-db (데이터베이스 테스트)")

        uvicorn.run(app, host="0.0.0.0", port=8001)

    except Exception as e:
        logger.error(f"❌ 서비스 실행 실패: {e}")
        return False


def main():
    """메인 함수"""
    print("🚀 주식 분석 서비스 - 간단 실행 버전")
    print("=" * 50)

    # 1. 환경변수 설정
    logger.info("1. 환경변수 설정 중...")
    set_default_environment()

    # 2. 패키지 확인
    logger.info("2. 패키지 확인 중...")
    if not check_packages():
        logger.error("필수 패키지가 설치되지 않았습니다.")
        logger.error(
            "pip install fastapi uvicorn requests beautifulsoup4 mysql-connector-python"
        )
        return 1

    # 3. 디렉토리 생성
    logger.info("3. 디렉토리 생성 중...")
    create_directories()

    # 4. 데이터베이스 연결 테스트
    logger.info("4. 데이터베이스 연결 테스트 중...")
    if not test_database_connection():
        logger.error("데이터베이스 연결에 실패했습니다.")
        logger.error("환경변수를 확인해주세요.")
        return 1

    # 5. 기본 테이블 생성
    logger.info("5. 기본 테이블 생성 중...")
    if not create_basic_tables():
        logger.error("테이블 생성에 실패했습니다.")
        return 1

    # 6. 서비스 실행
    logger.info("6. 서비스 실행 중...")
    print("\n🎉 모든 준비 완료! 서비스를 시작합니다...")
    print("💡 브라우저에서 http://localhost:8001 에 접속하세요")
    print("🛑 종료하려면 Ctrl+C를 누르세요\n")

    run_simple_news_service()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\n👋 서비스가 종료되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 예상치 못한 오류: {e}")
        sys.exit(1)
