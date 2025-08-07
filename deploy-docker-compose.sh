#!/bin/bash

# HyperAsset LLM Docker Compose 배포 스크립트
# 프론트엔드는 Firebase, 백엔드는 Docker Compose로 배포

set -e

echo "🚀 HyperAsset LLM Docker Compose 배포 시작..."
echo "================================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 함수 정의
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 사전 체크
check_prerequisites() {
    log_info "사전 요구사항 체크 중..."
    
    # Docker 체크
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되지 않았습니다."
        exit 1
    fi
    
    # Docker Compose 체크
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose가 설치되지 않았습니다."
        exit 1
    fi
    
    # Firebase CLI 체크
    if ! command -v firebase &> /dev/null; then
        log_error "Firebase CLI가 설치되지 않았습니다."
        echo "npm install -g firebase-tools 를 실행하세요."
        exit 1
    fi
    
    log_success "사전 요구사항 체크 완료"
}

# 1단계: 기존 컨테이너 정리
cleanup_containers() {
    log_info "1단계: 기존 컨테이너 정리 중..."
    
    # 기존 컨테이너 중지 및 제거
    docker-compose down --remove-orphans || true
    
    # 사용하지 않는 이미지 정리 (선택사항)
    read -p "사용하지 않는 Docker 이미지를 정리하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker image prune -f
        log_info "Docker 이미지 정리 완료"
    fi
    
    log_success "컨테이너 정리 완료"
}

# 2단계: 백엔드 Docker Compose 빌드 및 시작
deploy_backend() {
    log_info "2단계: 백엔드 Docker Compose 배포 시작..."
    
    # Docker Compose 빌드
    log_info "Docker 이미지 빌드 중..."
    docker-compose build --no-cache
    
    # Docker Compose 시작
    log_info "Docker 컨테이너 시작 중..."
    docker-compose up -d
    
    # 컨테이너 시작 대기
    log_info "서비스 시작 대기 중... (30초)"
    sleep 30
    
    # 컨테이너 상태 확인
    log_info "컨테이너 상태 확인 중..."
    docker-compose ps
    
    log_success "백엔드 Docker Compose 배포 완료"
}

# 3단계: 백엔드 헬스체크
check_backend_health() {
    log_info "3단계: 백엔드 서비스 헬스체크..."
    
    API_BASE_URL=${API_BASE_URL:-"http://localhost"}
    
    # API Gateway 헬스체크
    log_info "API Gateway 헬스체크 중..."
    for i in {1..5}; do
        if curl -f "${API_BASE_URL}:8005/health" > /dev/null 2>&1; then
            log_success "API Gateway (8005) - 정상"
            break
        else
            log_warning "API Gateway 헬스체크 실패 (시도 $i/5)"
            sleep 10
        fi
    done
    
    # User Service 헬스체크
    log_info "User Service 헬스체크 중..."
    for i in {1..5}; do
        if curl -f "${API_BASE_URL}:8006/health" > /dev/null 2>&1; then
            log_success "User Service (8006) - 정상"
            break
        else
            log_warning "User Service 헬스체크 실패 (시도 $i/5)"
            sleep 10
        fi
    done
    
    log_success "백엔드 헬스체크 완료"
}

# 4단계: 프론트엔드 빌드 및 배포
deploy_frontend() {
    log_info "4단계: 프론트엔드 Firebase 배포 시작..."
    
    cd stock_analysis_service/frontend
    
    # npm 의존성 설치
    log_info "npm 의존성 설치 중..."
    npm install
    
    # 프로덕션 빌드
    log_info "프론트엔드 프로덕션 빌드 중..."
    npm run build
    
    # Firebase 배포
    log_info "Firebase Hosting 배포 중..."
    firebase deploy --only hosting --non-interactive
    
    # 배포 URL 확인
    log_info "배포 결과 확인..."
    firebase hosting:channel:list
    
    cd ../..
    
    log_success "프론트엔드 Firebase 배포 완료"
}

# 5단계: 전체 시스템 테스트
test_full_system() {
    log_info "5단계: 전체 시스템 통합 테스트..."
    
    # 프론트엔드 접속 확인
    log_info "프론트엔드 접속 확인..."
    FRONTEND_URL="https://hyperasset-llm.web.app"
    if curl -f "$FRONTEND_URL" > /dev/null 2>&1; then
        log_success "프론트엔드 접속 확인 - $FRONTEND_URL"
    else
        log_warning "프론트엔드 접속 실패"
    fi
    
    # 백엔드 API 확인
    log_info "백엔드 API 확인..."
    API_BASE_URL=${API_BASE_URL:-"http://localhost"}
    if curl -f "${API_BASE_URL}:8005/health" > /dev/null 2>&1; then
        log_success "백엔드 API 확인 - ${API_BASE_URL}:8005"
    else
        log_warning "백엔드 API 접속 실패"
    fi
    
    log_success "전체 시스템 테스트 완료"
}

# 메인 실행 흐름
main() {
    echo "🎯 Docker Compose 기반 하이브리드 배포 시작"
    echo "  - 백엔드: Docker Compose (VM)"
    echo "  - 프론트엔드: Firebase Hosting"
    echo "================================================"
    
    check_prerequisites
    cleanup_containers
    deploy_backend
    check_backend_health
    deploy_frontend
    test_full_system
    
    echo "================================================"
    log_success "🎉 HyperAsset LLM 배포 완료!"
    echo "📋 접속 정보:"
    echo "  - 프론트엔드: https://hyperasset-llm.web.app"
    echo "  - API Gateway: ${API_BASE_URL:-http://localhost}:8005"
    echo "  - User Service: ${API_BASE_URL:-http://localhost}:8006"
    echo "================================================"
    
    # Docker Compose 로그 확인 옵션
    read -p "Docker Compose 실시간 로그를 확인하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Docker Compose 로그 출력 중... (Ctrl+C로 종료)"
        docker-compose logs -f
    fi
}

# 스크립트 실행
main "$@"