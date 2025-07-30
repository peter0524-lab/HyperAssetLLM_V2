# 🚀 HyperAsset LLM Firebase 배포 가이드

## 🆕 분리 배포 공식 워크플로우

이 프로젝트는 **프론트엔드(Firebase Hosting)**와 **백엔드(Google Cloud Run)**를 완전히 분리하여 배포/운영합니다.

### 분리 배포 스크립트
- 프론트엔드만: `quick-deploy.sh`
- 백엔드만: `deploy-backend.sh`
- 전체: `deploy.sh`
- 연결 확인: `check-connection.sh`

### 권장 배포 시나리오
- **UI/프론트엔드만 변경**: `quick-deploy.sh`
- **API/백엔드만 변경**: `deploy-backend.sh`
- **전체 변경/최초 배포**: `deploy.sh`
- **배포 후 연결 확인**: `check-connection.sh`

---

# 이하 기존 가이드 유지

## 📋 프로젝트 개요

**HyperAsset LLM 주식 분석 시스템**을 Firebase Hosting + Google Cloud Run으로 배포하는 완전한 가이드입니다.

### 🏗️ 아키텍처 구성
```
Frontend (Firebase Hosting) - React + Vite + TypeScript
    ↓
Backend (Google Cloud Run) - Python FastAPI 마이크로서비스
    ↓
Database (AWS RDS MySQL) - 기존 데이터베이스
    ↓
Vector DB (ChromaDB) - 임시 스토리지
```

## 🎯 배포 전략

### ✅ 현재 구현 상태
- **Frontend**: React + Vite + TypeScript (포트 3000) ✅
- **Backend**: Python FastAPI 마이크로서비스 (포트 8005) ✅
- **Database**: AWS RDS MySQL (기존 구성) ✅
- **Services**: 8개 마이크로서비스 + 오케스트레이터 ✅

### 🚀 배포 옵션

#### **Option 1: 완전 클라우드 네이티브 (권장)**
- Frontend: Firebase Hosting
- Backend: Google Cloud Run
- Database: AWS RDS (기존)
- Vector DB: ChromaDB + 임시 스토리지

#### **Option 2: 하이브리드 배포**
- Frontend: Firebase Hosting
- Backend: VPS/EC2
- Database: AWS RDS (기존)
- Vector DB: ChromaDB + S3

## 🛠️ 사전 준비사항

### 1. Firebase CLI 설치
```bash
npm install -g firebase-tools
firebase login
```

### 2. Google Cloud CLI 설치
```bash
# Windows
curl https://sdk.cloud.google.com | bash
gcloud init

# Mac
brew install google-cloud-sdk
gcloud init
```

### 3. Docker 설치
```bash
# Windows/Mac: Docker Desktop 설치
# Linux
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

## 📦 배포 단계별 가이드

### 1단계: Firebase 프로젝트 설정

#### 1.1 Firebase 프로젝트 생성
```bash
# Firebase 콘솔에서 새 프로젝트 생성
# 또는 CLI로 생성
firebase projects:create hyperasset-llm
firebase use hyperasset-llm
```

#### 1.2 Firebase Hosting 초기화
```bash
cd stock_analysis_service/frontend
firebase init hosting

# 선택사항:
# - Public directory: dist
# - Single-page app: Yes
# - Overwrite index.html: No
```

#### 1.3 firebase.json 설정
```json
{
  "hosting": {
    "public": "dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      },
      {
        "source": "**/*.@(jpg|jpeg|gif|png|svg|webp)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      }
    ]
  }
}
```

### 2단계: Frontend 배포

#### 2.1 프론트엔드 빌드
```bash
cd stock_analysis_service/frontend

# 의존성 설치
npm install

# 프로덕션 빌드
npm run build

# 빌드 결과 확인
ls -la dist/
```

#### 2.2 Firebase Hosting 배포
```bash
# Firebase 배포
firebase deploy --only hosting

# 배포 URL 확인
firebase hosting:channel:list
```

### 3단계: Backend 배포 (Cloud Run)

#### 3.1 Dockerfile 확인
```dockerfile
# stock_analysis_service/deployment/Dockerfile
FROM python:3.11-slim

# 시스템 패키지 업데이트
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 환경 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENV=production

# Python 의존성 설치
COPY requirements_final.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_final.txt

# 애플리케이션 코드 복사
COPY . .

# ChromaDB 데이터 디렉토리 생성
RUN mkdir -p /tmp/chroma

# 포트 노출
EXPOSE 8005

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "1"]
```

#### 3.2 Cloud Run 배포
```bash
# 프로젝트 설정
gcloud config set project hyperasset-llm

# Docker 이미지 빌드
docker build -t gcr.io/hyperasset-llm/stock-analysis-api -f deployment/Dockerfile .

# Google Container Registry에 푸시
docker tag gcr.io/hyperasset-llm/stock-analysis-api gcr.io/hyperasset-llm/stock-analysis-api:latest
docker push gcr.io/hyperasset-llm/stock-analysis-api:latest

# Cloud Run 배포
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
```

### 4단계: 환경 변수 설정

#### 4.1 Cloud Run 환경 변수 설정
```bash
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
```

### 5단계: ChromaDB 설정

#### 5.1 ChromaDB 설정 파일 확인
```python
# stock_analysis_service/config/chromadb_config.py
import chromadb
from chromadb.config import Settings
import os

def get_chromadb_client():
    """프로덕션 환경용 ChromaDB 클라이언트"""
    if os.getenv('ENV') == 'production':
        # 프로덕션: 임시 디렉토리 사용
        return chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="/tmp/chroma"
        ))
    else:
        # 개발: 로컬 디렉토리 사용
        return chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./data/chroma"
        ))
```

### 6단계: CORS 설정

#### 6.1 Frontend CORS 설정
```typescript
// stock_analysis_service/frontend/src/lib/api.ts
const API_BASE_URL = import.meta.env.PROD 
  ? 'https://stock-analysis-api-xxxxx-xx.a.run.app'
  : 'http://localhost:8005';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

#### 6.2 Backend CORS 설정 확인
```python
# services/api_gateway/main.py에서 CORS 설정 확인
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hyperasset-llm.web.app",
        "https://hyperasset-llm.firebaseapp.com",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🔧 배포 스크립트

### 자동 배포 스크립트 사용

#### Linux/Mac 사용자
```bash
# 전체 배포 (권장)
cd stock_analysis_service/deployment
chmod +x deploy.sh
./deploy.sh

# 빠른 배포 (프론트엔드만)
chmod +x quick-deploy.sh
./quick-deploy.sh
```

#### Windows 사용자
```powershell
# PowerShell에서 실행
cd stock_analysis_service\deployment

# 전체 배포 (권장)
.\deploy.sh

# 빠른 배포 (프론트엔드만)
.\quick-deploy.sh
```

### 수동 배포 명령어

#### 1. 프론트엔드만 배포 (빠른 배포)
```bash
# Linux/Mac
cd stock_analysis_service/frontend
npm install
npm run build
firebase deploy --only hosting

# Windows PowerShell
cd stock_analysis_service\frontend
npm install
npm run build
firebase deploy --only hosting
```

#### 2. 백엔드만 배포
```bash
# Linux/Mac
cd stock_analysis_service
docker build -t gcr.io/hyperasset-llm/stock-analysis-api -f deployment/Dockerfile .
docker push gcr.io/hyperasset-llm/stock-analysis-api:latest
gcloud run deploy stock-analysis-api --image gcr.io/hyperasset-llm/stock-analysis-api:latest --region asia-northeast3

# Windows PowerShell
cd stock_analysis_service
docker build -t gcr.io/hyperasset-llm/stock-analysis-api -f deployment/Dockerfile .
docker push gcr.io/hyperasset-llm/stock-analysis-api:latest
gcloud run deploy stock-analysis-api --image gcr.io/hyperasset-llm/stock-analysis-api:latest --region asia-northeast3
```

## 🔍 배포 후 확인사항

### 1. Frontend 확인
```bash
# Firebase Hosting URL 확인
firebase hosting:channel:list

# 브라우저에서 확인
open https://hyperasset-llm.web.app
```

### 2. Backend 확인
```bash
# Cloud Run 서비스 상태 확인
gcloud run services describe stock-analysis-api --region asia-northeast3

# API 엔드포인트 테스트
curl https://stock-analysis-api-xxxxx-xx.a.run.app/health
```

### 3. 데이터베이스 연결 확인
```bash
# Cloud Run 로그 확인
gcloud logs read --service=stock-analysis-api --limit=50
```

## 💰 비용 최적화

### Firebase Hosting
- **무료 플랜**: 1GB/월, 10GB/월 전송
- **Blaze 플랜**: 사용량 기반 과금

### Cloud Run
- **무료 플랜**: 2백만 요청/월, 360,000 vCPU-초/월, 180,000 GiB-초/월
- **과금**: 사용량 초과 시 요금 부과

### AWS RDS (기존)
- **t3.micro**: $8.47/월
- **t3.small**: $16.94/월

## 🚨 주의사항

### 1. 보안
- 환경 변수는 절대 코드에 하드코딩하지 마세요
- API 키는 Google Secret Manager 사용 권장
- 데이터베이스 접근은 VPC 연결 권장

### 2. 성능
- Cold Start 최소화를 위해 최소 인스턴스 설정
- 메모리 사용량 모니터링 필수
- ChromaDB는 임시 디렉토리 사용으로 인한 데이터 손실 주의

### 3. 확장성
- Auto Scaling 설정으로 트래픽 대응
- CDN 사용으로 정적 파일 전송 최적화
- 로드 밸런서 설정으로 고가용성 확보

## 🔧 문제 해결

### 일반적인 문제들

#### 1. CORS 에러
```bash
# Backend CORS 설정 확인
gcloud run services update stock-analysis-api \
  --region asia-northeast3 \
  --set-env-vars CORS_ORIGINS="https://hyperasset-llm.web.app"
```

#### 2. 데이터베이스 연결 실패
```bash
# Cloud Run에서 RDS 연결 확인
gcloud run services update stock-analysis-api \
  --region asia-northeast3 \
  --add-cloudsql-instances hyperasset-llm:asia-northeast3:database-1
```

#### 3. 메모리 부족
```bash
# 메모리 증가
gcloud run services update stock-analysis-api \
  --region asia-northeast3 \
  --memory 4Gi
```

#### 4. Windows에서 스크립트 실행 오류
```powershell
# PowerShell 실행 정책 변경
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 또는 Git Bash 사용
bash deploy.sh
```

## 📞 지원

배포 중 문제가 발생하면:
1. Cloud Run 로그 확인: `gcloud logs read --service=stock-analysis-api`
2. Firebase 로그 확인: `firebase hosting:channel:list`
3. 데이터베이스 연결 테스트: `mysql -h database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com -u admin -p`

---

**🎉 배포 완료 후 URL:**
- Frontend: `https://hyperasset-llm.web.app`
- Backend: `https://stock-analysis-api-xxxxx-xx.a.run.app`
- API Docs: `https://stock-analysis-api-xxxxx-xx.a.run.app/docs` 