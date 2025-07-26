#!/bin/bash

echo "============================================"
echo "🚀 주식 분석 서비스 설치 스크립트 (Mac/Linux)"
echo "============================================"
echo ""

# 현재 디렉토리 확인
echo "📁 현재 경로: $(pwd)"
echo ""

# Python 버전 확인
echo "🐍 Python 버전 확인..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되지 않았습니다!"
    echo "   Python 3.8 이상을 설치해주세요:"
    echo "   Mac: brew install python"
    echo "   Ubuntu: sudo apt-get install python3 python3-pip python3-venv"
    echo "   CentOS: sudo yum install python3 python3-pip"
    exit 1
fi

python3 --version
echo ""

# 가상환경 생성
echo "🔧 가상환경 생성 중..."
if [ -d "venv" ]; then
    echo "⚠️  기존 가상환경이 존재합니다. 삭제하고 다시 생성합니다."
    rm -rf venv
fi

python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ 가상환경 생성 실패!"
    exit 1
fi
echo "✅ 가상환경 생성 완료"
echo ""

# 가상환경 활성화
echo "🔄 가상환경 활성화..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ 가상환경 활성화 실패!"
    exit 1
fi
echo "✅ 가상환경 활성화 완료"
echo ""

# pip 업그레이드
echo "📦 pip 업그레이드..."
python -m pip install --upgrade pip
echo "✅ pip 업그레이드 완료"
echo ""

# 기본 패키지 설치
echo "📚 기본 패키지 설치 중..."
pip install wheel setuptools
echo "✅ 기본 패키지 설치 완료"
echo ""

# 핵심 패키지 우선 설치
echo "🎯 핵심 패키지 우선 설치..."
pip install fastapi uvicorn pydantic
pip install requests beautifulsoup4
pip install numpy pandas
echo "✅ 핵심 패키지 설치 완료"
echo ""

# 머신러닝 패키지 설치
echo "🤖 머신러닝 패키지 설치..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers sentence-transformers
pip install scikit-learn
echo "✅ 머신러닝 패키지 설치 완료"
echo ""

# 데이터베이스 패키지 설치
echo "🗄️ 데이터베이스 패키지 설치..."
pip install mysql-connector-python pymysql sqlalchemy
pip install chromadb
echo "✅ 데이터베이스 패키지 설치 완료"
echo ""

# 특수 패키지 설치 (오류 가능성 있음)
echo "🔧 특수 패키지 설치 중..."

# TA-Lib 설치 (Mac/Linux)
echo "  - TA-Lib (기술적 분석)"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Mac
    if command -v brew &> /dev/null; then
        brew install ta-lib
        pip install TA-Lib
    else
        echo "⚠️  Homebrew가 설치되지 않았습니다. TA-Lib 수동 설치 필요"
        echo "    brew install ta-lib"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "  TA-Lib 의존성 설치 중..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y build-essential wget
    elif command -v yum &> /dev/null; then
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y wget
    fi
    
    # TA-Lib 소스 컴파일
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr/local
    make
    sudo make install
    cd ..
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
    pip install TA-Lib
else
    echo "⚠️  지원하지 않는 운영체제입니다. TA-Lib 수동 설치 필요"
fi

# KoNLPy 설치
echo "  - KoNLPy (한국어 자연어 처리)"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Mac - Java 설치 확인
    if command -v java &> /dev/null; then
        pip install konlpy
    else
        echo "⚠️  Java가 설치되지 않았습니다. KoNLPy 설치를 위해 Java 설치 필요"
        echo "    brew install openjdk"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - Java 설치
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y openjdk-8-jdk
    elif command -v yum &> /dev/null; then
        sudo yum install -y java-1.8.0-openjdk-devel
    fi
    pip install konlpy
fi

# SimHash 설치
echo "  - SimHash (중복 제거)"
pip install simhash

echo "✅ 특수 패키지 설치 시도 완료"
echo ""

# 전체 requirements.txt 설치
echo "📋 전체 패키지 목록 설치..."
pip install -r requirements.txt
echo "✅ 전체 패키지 설치 완료"
echo ""

# 필요한 디렉토리 생성
echo "📁 필요한 디렉토리 생성..."
mkdir -p data/chroma
mkdir -p logs
mkdir -p temp
echo "✅ 디렉토리 생성 완료"
echo ""

# 데이터베이스 초기화
echo "🛠️ 데이터베이스 초기화..."
python utils/init_database.py
if [ $? -ne 0 ]; then
    echo "⚠️  데이터베이스 초기화 실패 - 나중에 수동으로 실행하세요"
    echo "    python utils/init_database.py"
fi
echo ""

# 설치 확인
echo "🔍 설치 확인..."
python -c "import fastapi; print('✅ FastAPI:', fastapi.__version__)" 2>/dev/null || echo "⚠️  FastAPI 확인 실패"
python -c "import torch; print('✅ PyTorch:', torch.__version__)" 2>/dev/null || echo "⚠️  PyTorch 확인 실패"
python -c "import transformers; print('✅ Transformers:', transformers.__version__)" 2>/dev/null || echo "⚠️  Transformers 확인 실패"
python -c "import chromadb; print('✅ ChromaDB:', chromadb.__version__)" 2>/dev/null || echo "⚠️  ChromaDB 확인 실패"
python -c "import mysql.connector; print('✅ MySQL Connector: OK')" 2>/dev/null || echo "⚠️  MySQL Connector 확인 실패"
echo ""

echo "============================================"
echo "🎉 설치 완료!"
echo "============================================"
echo ""
echo "🚀 실행 방법:"
echo "  1. 가상환경 활성화: source venv/bin/activate"
echo "  2. 서비스 실행: python run.py"
echo ""
echo "📝 참고사항:"
echo "  - 가상환경을 종료하려면: deactivate"
echo "  - 다음 실행시에는 가상환경만 활성화하면 됩니다"
echo ""
echo "Press Enter to continue..."
read 