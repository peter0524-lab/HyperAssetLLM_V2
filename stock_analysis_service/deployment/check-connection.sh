#!/bin/bash

# HyperAsset LLM 연결 확인 스크립트
set -e

FRONTEND_URL="https://hyperasset-llm.web.app"
BACKEND_URL="https://stock-analysis-api-xxxxx-xx.a.run.app"

# 프론트엔드 확인
echo "🌐 프론트엔드 상태 확인: $FRONTEND_URL"
curl -I $FRONTEND_URL || { echo "❌ 프론트엔드 접속 실패"; exit 1; }
echo "✅ 프론트엔드 접속 성공"

echo
# 백엔드 헬스체크
echo "🔗 백엔드 헬스체크: $BACKEND_URL/health"
curl -f $BACKEND_URL/health || { echo "❌ 백엔드 헬스체크 실패"; exit 1; }
echo "✅ 백엔드 헬스체크 성공"

echo
# 프론트엔드에서 백엔드 API 연결 테스트 (예시: /api/test)
echo "🔗 프론트엔드 → 백엔드 API 연결 테스트 (수동 확인 필요)"
echo "프론트엔드에서 실제 API 호출이 정상 동작하는지 브라우저에서 확인하세요."
echo "(예: 로그인, 데이터 조회 등)"

echo "=================================="
echo "✅ 연결 확인 완료!"
echo "=================================="