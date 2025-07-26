@echo off
echo ============================================
echo 🚀 주식 분석 서비스 설치 스크립트 (Windows)
echo ============================================
echo.

REM 현재 디렉토리 확인
echo 📁 현재 경로: %cd%
echo.

REM Python 버전 확인
echo 🐍 Python 버전 확인...
python --version
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았습니다!
    echo    Python 3.8 이상을 설치해주세요: https://python.org
    pause
    exit /b 1
)
echo.

REM 가상환경 생성
echo 🔧 가상환경 생성 중...
if exist "venv" (
    echo ⚠️  기존 가상환경이 존재합니다. 삭제하고 다시 생성합니다.
    rmdir /s /q venv
)
python -m venv venv
if errorlevel 1 (
    echo ❌ 가상환경 생성 실패!
    pause
    exit /b 1
)
echo ✅ 가상환경 생성 완료
echo.

REM 가상환경 활성화
echo 🔄 가상환경 활성화...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 가상환경 활성화 실패!
    pause
    exit /b 1
)
echo ✅ 가상환경 활성화 완료
echo.

REM pip 업그레이드
echo 📦 pip 업그레이드...
python -m pip install --upgrade pip
echo ✅ pip 업그레이드 완료
echo.

REM 기본 패키지 설치
echo 📚 기본 패키지 설치 중...
pip install wheel setuptools
echo ✅ 기본 패키지 설치 완료
echo.

REM 핵심 패키지 우선 설치
echo 🎯 핵심 패키지 우선 설치...
pip install fastapi uvicorn pydantic
pip install requests beautifulsoup4
pip install numpy pandas
echo ✅ 핵심 패키지 설치 완료
echo.

REM 머신러닝 패키지 설치
echo 🤖 머신러닝 패키지 설치...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers sentence-transformers
pip install scikit-learn
echo ✅ 머신러닝 패키지 설치 완료
echo.

REM 데이터베이스 패키지 설치
echo 🗄️ 데이터베이스 패키지 설치...
pip install mysql-connector-python pymysql sqlalchemy
pip install chromadb
echo ✅ 데이터베이스 패키지 설치 완료
echo.

REM 특수 패키지 설치 (오류 가능성 있음)
echo 🔧 특수 패키지 설치 중...
echo   - TA-Lib (기술적 분석)
pip install TA-Lib
if errorlevel 1 (
    echo ⚠️  TA-Lib 설치 실패 - 수동 설치가 필요할 수 있습니다
    echo    https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib 에서 다운로드
)

echo   - KoNLPy (한국어 자연어 처리)
pip install konlpy
if errorlevel 1 (
    echo ⚠️  KoNLPy 설치 실패 - Java 설치가 필요할 수 있습니다
)

echo   - SimHash (중복 제거)
pip install simhash
echo ✅ 특수 패키지 설치 시도 완료
echo.

REM 전체 requirements.txt 설치
echo 📋 전체 패키지 목록 설치...
pip install -r requirements.txt
echo ✅ 전체 패키지 설치 완료
echo.

REM 필요한 디렉토리 생성
echo 📁 필요한 디렉토리 생성...
if not exist "data" mkdir data
if not exist "data\chroma" mkdir data\chroma
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp
echo ✅ 디렉토리 생성 완료
echo.

REM 데이터베이스 초기화
echo 🛠️ 데이터베이스 초기화...
python utils/init_database.py
if errorlevel 1 (
    echo ⚠️  데이터베이스 초기화 실패 - 나중에 수동으로 실행하세요
    echo    python utils/init_database.py
)
echo.

REM 설치 확인
echo 🔍 설치 확인...
python -c "import fastapi; print('✅ FastAPI:', fastapi.__version__)"
python -c "import torch; print('✅ PyTorch:', torch.__version__)"
python -c "import transformers; print('✅ Transformers:', transformers.__version__)"
python -c "import chromadb; print('✅ ChromaDB:', chromadb.__version__)"
python -c "import mysql.connector; print('✅ MySQL Connector: OK')"
echo.

echo ============================================
echo 🎉 설치 완료!
echo ============================================
echo.
echo 🚀 실행 방법:
echo   1. 가상환경 활성화: venv\Scripts\activate
echo   2. 서비스 실행: python run.py
echo.
echo 📝 참고사항:
echo   - 가상환경을 종료하려면: deactivate
echo   - 다음 실행시에는 가상환경만 활성화하면 됩니다
echo.
pause 