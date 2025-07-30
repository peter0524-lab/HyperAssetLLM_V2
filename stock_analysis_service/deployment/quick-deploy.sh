#!/bin/bash

# HyperAsset LLM 빠른 배포 스크립트 (프론트엔드만)
# Firebase Hosting 전용

set -e

echo "⚡ HyperAsset LLM 빠른 배포 시작..."
echo "=================================="

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 사전 체크
check_firebase() {
    log_info "Firebase CLI 체크 중..."
    
    if ! command -v firebase &> /dev/null; then
        echo "Firebase CLI가 설치되지 않았습니다."
        echo "npm install -g firebase-tools 를 실행하세요."
        exit 1
    fi
    
    log_success "Firebase CLI 확인 완료"
}

# 프론트엔드 빌드
build_frontend() {
    log_info "프론트엔드 빌드 시작..."
    
    cd ../frontend
    
    # 의존성 설치 (캐시 사용)
    log_info "npm 의존성 설치 중..."
    npm ci --only=production || npm install
    
    # 프로덕션 빌드
    log_info "프로덕션 빌드 중..."
    npm run build
    
    # 빌드 결과 확인
    if [ ! -d "dist" ]; then
        echo "빌드 실패: dist 폴더가 생성되지 않았습니다."
        exit 1
    fi
    
    log_success "프론트엔드 빌드 완료"
    cd ../deployment
}

# Firebase 배포
deploy_firebase() {
    log_info "Firebase Hosting 배포 시작..."
    
    cd ../frontend
    
    # Firebase 배포
    log_info "Firebase Hosting 배포 중..."
    firebase deploy --only hosting
    
    # 배포 URL 확인
    log_info "배포 URL 확인 중..."
    firebase hosting:channel:list
    
    log_success "Firebase Hosting 배포 완료"
    cd ../deployment
}

# 메인 실행
main() {
    echo "=================================="
    echo "HyperAsset LLM 빠른 배포"
    echo "=================================="
    
    check_firebase
    build_frontend
    deploy_firebase
    
    echo "=================================="
    log_success "✅ 프론트엔드 배포 완료!"
    echo "=================================="
    echo "Frontend: https://hyperasset-llm.web.app"
    echo "=================================="
}

main "$@" 