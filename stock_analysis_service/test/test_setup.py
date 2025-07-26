#!/usr/bin/env python3
"""
시스템 설정 테스트 스크립트
현재 발생할 수 있는 에러들을 사전에 진단하고 해결책을 제시
"""

import sys
import os
import importlib


def test_python_version():
    """Python 버전 확인"""
    print("🐍 Python 버전 확인...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python 버전이 낮습니다: {version.major}.{version.minor}")
        print("   Python 3.8 이상이 필요합니다")
        return False


def test_packages():
    """필수 패키지 import 테스트"""
    print("\n📦 필수 패키지 테스트...")

    packages = {
        "fastapi": "FastAPI 웹 프레임워크",
        "uvicorn": "ASGI 서버",
        "requests": "HTTP 클라이언트",
        "mysql.connector": "MySQL 커넥터",
        "pandas": "데이터 처리",
        "numpy": "수치 계산",
        "torch": "PyTorch",
        "transformers": "Transformer 모델",
        "sentence_transformers": "문장 임베딩",
        "chromadb": "벡터 데이터베이스",
        "beautifulsoup4": "웹 크롤링",
        "schedule": "스케줄링",
    }

    failed_packages = []

    for package, description in packages.items():
        try:
            importlib.import_module(package.replace("-", "_"))
            print(f"✅ {package}: {description}")
        except ImportError:
            print(f"❌ {package}: {description} - 설치 필요")
            failed_packages.append(package)

    return len(failed_packages) == 0, failed_packages


def test_environment_variables():
    """환경 변수 확인"""
    print("\n🔧 환경 변수 확인...")

    # config 모듈 import 테스트
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from config.env_local import get_env_var

        print("✅ config.env_local 모듈 로드 성공")
    except Exception as e:
        print(f"❌ config.env_local 모듈 로드 실패: {e}")
        return False

    # 필수 환경 변수 확인
    required_vars = {
        "TARGET_STOCK_CODE": "006800",
        "DATABASE_HOST": "your_mysql_host",
        "DATABASE_USER": "your_mysql_user",
        "DATABASE_PASSWORD": "your_mysql_password",
        "HYPERCLOVA_API_KEY": "nv-a835f0aa82b7477f87792ae2e48941afZsnZ",
        "DART_API_KEY": "your_dart_key",
        "TELEGRAM_BOT_TOKEN": "your_telegram_token",
        "TELEGRAM_CHAT_ID": "your_chat_id",
    }

    missing_vars = []
    for var, example in required_vars.items():
        value = get_env_var(var, "")
        if not value or value == example:
            print(f"⚠️ {var}: 설정 필요 (예시: {example})")
            missing_vars.append(var)
        else:
            print(f"✅ {var}: 설정됨")

    return len(missing_vars) == 0, missing_vars


def test_file_structure():
    """파일 구조 확인"""
    print("\n📁 파일 구조 확인...")

    required_files = [
        "config/env_local.py",
        "config/stocks.json",
        "shared/database/mysql_client.py",
        "shared/database/vector_db.py",
        "shared/llm/hyperclova_client.py",
        "services/news_service/main.py",
        "requirements.txt",
        "run.py",
    ]

    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 파일 없음")
            missing_files.append(file_path)

    return len(missing_files) == 0, missing_files


def test_database_connection():
    """데이터베이스 연결 테스트"""
    print("\n🗄️ 데이터베이스 연결 테스트...")

    try:
        from shared.database.mysql_client import MySQLClient

        client = MySQLClient()
        health = client.health_check()

        if health["status"] == "healthy":
            print("✅ MySQL 데이터베이스 연결 성공")
            return True
        else:
            print(f"❌ MySQL 연결 실패: {health.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print(f"❌ MySQL 연결 테스트 실패: {e}")
        print("   데이터베이스 설정을 확인해주세요")
        return False


def print_solutions(failed_packages, missing_vars, missing_files):
    """해결책 출력"""
    print("\n" + "=" * 50)
    print("🔧 해결책")
    print("=" * 50)

    if failed_packages:
        print("\n📦 누락된 패키지 설치:")
        print("pip install " + " ".join(failed_packages))

    if missing_vars:
        print("\n🔧 환경 변수 설정:")
        print("다음 환경 변수들을 설정해주세요:")
        for var in missing_vars:
            print(f"  {var}=your_value_here")

    if missing_files:
        print("\n📁 누락된 파일:")
        for file in missing_files:
            print(f"  {file}")

    print("\n🚀 해결 후 실행 방법:")
    print("1. 가상환경 활성화: venv\\Scripts\\activate")
    print("2. 환경 변수 설정")
    print("3. 데이터베이스 초기화: python utils/init_database.py")
    print("4. 서비스 실행: python run.py")


def main():
    """메인 함수"""
    print("🔍 주식 분석 서비스 설정 진단")
    print("=" * 50)

    # 각 테스트 실행
    python_ok = test_python_version()
    packages_ok, failed_packages = test_packages()
    env_ok, missing_vars = test_environment_variables()
    files_ok, missing_files = test_file_structure()

    # 데이터베이스 테스트 (환경 변수가 설정된 경우에만)
    db_ok = False
    if env_ok:
        db_ok = test_database_connection()

    # 전체 결과
    print("\n" + "=" * 50)
    print("📊 진단 결과")
    print("=" * 50)

    all_ok = python_ok and packages_ok and env_ok and files_ok and db_ok

    if all_ok:
        print("🎉 모든 테스트 통과! 서비스 실행 준비 완료!")
        print("\n실행 명령어:")
        print("venv\\Scripts\\activate")
        print("python run.py")
    else:
        print("⚠️ 일부 문제가 발견되었습니다.")
        print_solutions(failed_packages, missing_vars, missing_files)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
