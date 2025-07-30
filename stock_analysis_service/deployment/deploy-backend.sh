#!/bin/bash

# HyperAsset LLM 백엔드 전용 배포 스크립트 (Cloud Run)
set -e

echo "🚀 HyperAsset LLM 백엔드 배포 시작..."
echo "=================================="

# Docker 빌드
cd ..
echo "[1/3] Docker 이미지 빌드 중..."
docker build -t gcr.io/hyperasset-llm/stock-analysis-api -f deployment/Dockerfile .
docker tag gcr.io/hyperasset-llm/stock-analysis-api gcr.io/hyperasset-llm/stock-analysis-api:latest

echo "[2/3] 이미지 푸시 중..."
docker push gcr.io/hyperasset-llm/stock-analysis-api:latest

# Cloud Run 배포
cd deployment
echo "[3/3] Cloud Run 배포 중..."
gcloud run deploy stock-analysis-api \
  --image gcr.io/hyperasset-llm/stock-analysis-api:latest \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --max-instances 10 \
  --set-env-vars ENV=production

echo "=================================="
echo "✅ 백엔드 배포 완료!"
echo "URL: https://stock-analysis-api-xxxxx-xx.a.run.app"
echo "=================================="