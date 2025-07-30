#!/bin/bash

# HyperAsset LLM 배포 스크립트
# Firebase Hosting + Google Cloud Run + AWS RDS

set -e  # 에러 발생 시 스크립트 중단

echo "🚀 HyperAsset LLM 배포 시작..."
echo "=================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    
    # Firebase CLI 체크
    if ! command -v firebase &> /dev/null; then
        log_error "Firebase CLI가 설치되지 않았습니다."
        echo "npm install -g firebase-tools 를 실행하세요."
        exit 1
    fi
    
    # Docker 체크
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되지 않았습니다."
        exit 1
    fi
    
    # gcloud 체크
    if ! command -v gcloud &> /dev/null; then
        log_error "Google Cloud CLI가 설치되지 않았습니다."
        exit 1
    fi
    
    log_success "사전 요구사항 체크 완료"
}

# 1단계: 프론트엔드 빌드
build_frontend() {
    log_info "1단계: 프론트엔드 빌드 시작..."
    
    cd ../frontend
    
    # 의존성 설치
    log_info "npm 의존성 설치 중..."
    npm install
    
    # 프로덕션 빌드
    log_info "프로덕션 빌드 중..."
    npm run build
    
    # 빌드 결과 확인
    if [ ! -d "dist" ]; then
        log_error "빌드 실패: dist 폴더가 생성되지 않았습니다."
        exit 1
    fi
    
    log_success "프론트엔드 빌드 완료"
    cd ../deployment
}

# 2단계: Firebase Hosting 배포
deploy_firebase() {
    log_info "2단계: Firebase Hosting 배포 시작..."
    
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

# 3단계: Docker 이미지 빌드
build_docker() {
    log_info "3단계: Docker 이미지 빌드 시작..."
    
    cd ..
    
    # Docker 이미지 빌드
    log_info "Docker 이미지 빌드 중..."
    docker build -t gcr.io/hyperasset-llm/stock-analysis-api -f deployment/Dockerfile .
    
    # 이미지 태그
    docker tag gcr.io/hyperasset-llm/stock-analysis-api gcr.io/hyperasset-llm/stock-analysis-api:latest
    
    log_success "Docker 이미지 빌드 완료"
    cd deployment
}

# 4단계: Container Registry 푸시
push_docker() {
    log_info "4단계: Container Registry 푸시 시작..."
    
    # Google Container Registry에 푸시
    log_info "이미지 푸시 중..."
    docker push gcr.io/hyperasset-llm/stock-analysis-api:latest
    
    log_success "Container Registry 푸시 완료"
}

# 5단계: Cloud Run 배포
deploy_cloud_run() {
    log_info "5단계: Cloud Run 배포 시작..."
    
    # Cloud Run 배포
    log_info "Cloud Run 서비스 배포 중..."
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
    
    log_success "Cloud Run 배포 완료"
}

# 6단계: 환경 변수 설정
setup_environment() {
    log_info "6단계: 환경 변수 설정 시작..."
    
    # Cloud Run 환경 변수 설정
    log_info "환경 변수 설정 중..."
    gcloud run services update stock-analysis-api \
        --region asia-northeast3 \
        --set-env-vars \
            DATABASE_HOST=database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com,\
            DATABASE_USER=admin,\
            DATABASE_PASSWORD=Peter0524!,\
            DATABASE_NAME=HyperAsset,\
            HYPERCLOVA_API_KEY=nv-b8935535a68442e3bce731a356b119a4Xbzy,\
            DART_API_KEY=db8f419d48d03346fc42b2f071e155aca0cd6248,\
            KIS_APP_KEY=PS6bXXjjR7M9PQFtcBGJFtou5RjDkDVGQxU2,\
            TELEGRAM_BOT_TOKEN=7888091225:AAHMqbCQV4_so7VqDeLqbWaiGTvVyQ698-M,\
            TELEGRAM_CHAT_ID=-1002819230740
    
    log_success "환경 변수 설정 완료"
}

# 7단계: 배포 확인
verify_deployment() {
    log_info "7단계: 배포 확인 시작..."
    
    # Cloud Run 서비스 상태 확인
    log_info "Cloud Run 서비스 상태 확인 중..."
    gcloud run services describe stock-analysis-api --region asia-northeast3
    
    # API 엔드포인트 테스트
    log_info "API 엔드포인트 테스트 중..."
    SERVICE_URL=$(gcloud run services describe stock-analysis-api --region asia-northeast3 --format="value(status.url)")
    
    if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
        log_success "API 엔드포인트 테스트 성공"
    else
        log_warning "API 엔드포인트 테스트 실패 - 서비스 시작 중일 수 있습니다."
    fi
    
    log_success "배포 확인 완료"
}

# 메인 실행
main() {
    echo "=================================="
    echo "HyperAsset LLM 배포 스크립트"
    echo "=================================="
    
    # 사전 체크
    check_prerequisites
    
    # 배포 단계 실행
    build_frontend
    deploy_firebase
    build_docker
    push_docker
    deploy_cloud_run
    setup_environment
    verify_deployment
    
    echo "=================================="
    log_success "🎉 배포 완료!"
    echo "=================================="
    echo "Frontend: https://hyperasset-llm.web.app"
    echo "Backend: https://stock-analysis-api-xxxxx-xx.a.run.app"
    echo "API Docs: https://stock-analysis-api-xxxxx-xx.a.run.app/docs"
    echo "=================================="
}

# 스크립트 실행
main "$@" 