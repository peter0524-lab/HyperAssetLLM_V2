#!/bin/bash
echo "🚀 주식 분석 서비스 설치 중..."
python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && mkdir -p data/chroma && python utils/init_database.py && echo "✅ 설치 완료!" && echo "다음 실행: source venv/bin/activate 후 python run.py" 