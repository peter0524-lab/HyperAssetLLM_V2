#!/bin/bash

# HyperAsset LLM 빠른 시작 스크립트 (로컬 개발용)

set -e

echo "⚡ HyperAsset LLM 빠른 시작..."
echo "================================"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 1. Docker Compose로 백엔드 시작
log_info "1단계: Docker Compose 백엔드 시작..."
docker-compose up -d

# 2. 서비스 시작 대기
log_info "2단계: 서비스 시작 대기 (20초)..."
sleep 20

# 3. 컨테이너 상태 확인
log_info "3단계: 컨테이너 상태 확인..."
docker-compose ps

# 4. 헬스체크
log_info "4단계: 헬스체크..."
echo "API Gateway (8005): $(curl -s http://localhost:8005/health 2>/dev/null || echo '❌ 실패')"
echo "User Service (8006): $(curl -s http://localhost:8006/health 2>/dev/null || echo '❌ 실패')"

# 5. 프론트엔드 시작 (선택사항)
read -p "프론트엔드도 시작하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "5단계: 프론트엔드 시작..."
    cd stock_analysis_service/frontend
    npm install
    npm run dev &
    cd ../..
    log_success "프론트엔드가 http://localhost:3000 에서 시작됩니다"
fi

echo "================================"
log_success "🎉 HyperAsset LLM 시작 완료!"
echo "📋 접속 정보:"
echo "  - 프론트엔드: http://localhost:3000"
echo "  - API Gateway: http://localhost:8005"
echo "  - User Service: http://localhost:8006"
echo ""
echo "🔍 Docker 로그 확인: docker-compose logs -f"
echo "⏹️  서비스 중지: docker-compose down"
echo "================================"