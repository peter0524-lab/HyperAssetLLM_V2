#!/usr/bin/env python3
"""
API Gateway 실행 스크립트
- 개발/운영 환경별 실행 옵션
- 로깅 설정
- 환경변수 검증
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import uvicorn
from config import get_gateway_config, Environment

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def validate_environment():
    """환경 검증"""
    config = get_gateway_config()
    
    # 필수 환경 확인
    if Environment.is_production():
        required_env_vars = [
            "MYSQL_HOST",
            "MYSQL_USER", 
            "MYSQL_PASSWORD",
            "TELEGRAM_BOT_TOKEN"
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"운영환경 필수 환경변수 누락: {missing_vars}")
            sys.exit(1)
    
    # Redis 연결 테스트 (선택사항)
    try:
        import aioredis
        logger.info("Redis 클라이언트 사용 가능")
    except ImportError:
        logger.warning("Redis 클라이언트 없음 - 로컬 캐시 사용")
    
    # 의존성 패키지 확인
    required_packages = [
        "fastapi", "uvicorn", "aiohttp", 
        "prometheus_client", "structlog", "pybreaker"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"필수 패키지 누락: {missing_packages}")
        logger.info("pip install -r requirements.txt 를 실행하세요")
        sys.exit(1)
    
    logger.info("✅ 환경 검증 완료")

def setup_logging(log_level: str):
    """로깅 설정"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'잘못된 로그 레벨: {log_level}')
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # uvicorn 로거 설정
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(numeric_level)
    
    logger.info(f"로깅 레벨 설정: {log_level.upper()}")

def parse_arguments():
    """명령행 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="API Gateway - 주식 분석 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python run.py                          # 기본 설정으로 실행
  python run.py --port 8080              # 포트 변경
  python run.py --reload --log-level debug  # 개발 모드
  python run.py --workers 4              # 멀티 워커 (운영환경)
        """
    )
    
    # 서버 설정
    parser.add_argument(
        "--host", 
        default=None,
        help="바인딩할 호스트 (기본값: 설정파일 또는 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=None,
        help="바인딩할 포트 (기본값: 설정파일 또는 8005)"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=1,
        help="워커 프로세스 수 (운영환경 권장: CPU 코어 수)"
    )
    
    # 개발 옵션
    parser.add_argument(
        "--reload", 
        action="store_true",
        help="파일 변경시 자동 재시작 (개발용)"
    )
    parser.add_argument(
        "--log-level", 
        default=None,
        choices=["debug", "info", "warning", "error", "critical"],
        help="로그 레벨 (기본값: 설정파일 또는 info)"
    )
    
    # 환경 설정
    parser.add_argument(
        "--env", 
        choices=["development", "production"],
        help="실행 환경 강제 설정"
    )
    
    # 검증 옵션
    parser.add_argument(
        "--check", 
        action="store_true",
        help="환경 검증만 수행하고 종료"
    )
    
    return parser.parse_args()

def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    # 환경 변수 설정
    if args.env:
        os.environ["ENVIRONMENT"] = args.env
    
    # 설정 로드
    config = get_gateway_config()
    
    # 명령행 인자로 설정 오버라이드
    host = args.host or config.host
    port = args.port or config.port
    log_level = args.log_level or config.log_level
    
    # 로깅 설정
    setup_logging(log_level)
    
    # 환경 검증
    validate_environment()
    
    if args.check:
        logger.info("환경 검증 완료 - 종료")
        return
    
    # 시작 정보 출력
    logger.info("=" * 60)
    logger.info("🚀 API Gateway 시작")
    logger.info("=" * 60)
    logger.info(f"환경: {Environment.get_environment()}")
    logger.info(f"호스트: {host}")
    logger.info(f"포트: {port}")
    logger.info(f"워커 수: {args.workers}")
    logger.info(f"로그 레벨: {log_level}")
    logger.info(f"자동 재시작: {'예' if args.reload else '아니오'}")
    logger.info("=" * 60)
    
    # 시작 시간 저장
    start_time = time.time()
    
    try:
        # uvicorn 설정
        uvicorn_config = {
            "app": "main:app",
            "host": host,
            "port": port,
            "log_level": log_level.lower(),
            "access_log": True,
            "use_colors": True,
            "reload": args.reload
        }
        
        # 멀티워커는 reload와 함께 사용할 수 없음
        if not args.reload and args.workers > 1:
            uvicorn_config["workers"] = args.workers
        
        # 운영환경 최적화
        if Environment.is_production():
            uvicorn_config.update({
                "loop": "uvloop",  # 성능 최적화
                "http": "httptools",  # HTTP 파서 최적화
                "reload": False,
                "access_log": False,  # 운영환경에서는 액세스 로그 비활성화
            })
        
        # 서버 실행
        uvicorn.run(**uvicorn_config)
        
    except KeyboardInterrupt:
        logger.info("\n🛑 사용자 중단 요청")
    except Exception as e:
        logger.error(f"❌ API Gateway 실행 실패: {e}")
        sys.exit(1)
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"총 실행 시간: {elapsed_time:.2f}초")
        logger.info("🏁 API Gateway 종료")

if __name__ == "__main__":
    main() 