# 🚀 HyperAsset LLM 배포 도구

이 디렉토리는 **HyperAsset LLM 주식 분석 시스템**의 배포를 위한 모든 도구들을 포함합니다.

## 📁 파일 구조

```
deployment/
├── README.md                    # 이 파일 (사용법 가이드)
├── FIREBASE_DEPLOYMENT_README.md # 완전한 배포 가이드
├── DEPLOYMENT_CHECKLIST.md      # 배포 체크리스트
├── deploy.sh                    # 전체 자동 배포 스크립트
├── quick-deploy.sh              # 빠른 프론트엔드 배포 스크립트
├── Dockerfile                   # Cloud Run 배포용
├── .dockerignore                # Docker 빌드 최적화
└── chromadb_config.py          # 프로덕션 ChromaDB 설정
```

## 🎯 배포 옵션

### 1. 전체 배포 (권장)
```bash
# Linux/Mac
chmod +x deploy.sh
./deploy.sh

# Windows PowerShell
.\deploy.sh
```

### 2. 빠른 배포 (프론트엔드만)
```bash
# Linux/Mac
chmod +x quick-deploy.sh
./quick-deploy.sh

# Windows PowerShell
.\quick-deploy.sh
```

## 📋 사전 준비사항

### 필수 도구 설치
```bash
# Firebase CLI
npm install -g firebase-tools

# Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

# Docker
# https://docs.docker.com/get-docker/
```

### 계정 설정
```bash
# Firebase 로그인
firebase login

# Google Cloud 로그인
gcloud auth login

# 프로젝트 설정
gcloud config set project hyperasset-llm
```

## 🔧 배포 단계

### 1단계: 프론트엔드 배포
- React 앱 빌드
- Firebase Hosting 배포
- 배포 URL 확인

### 2단계: 백엔드 배포
- Docker 이미지 빌드
- Google Container Registry 푸시
- Cloud Run 배포
- 환경 변수 설정

### 3단계: 통합 테스트
- 프론트엔드-백엔드 연결 확인
- API 엔드포인트 테스트
- 데이터베이스 연결 확인

## 🌐 배포 후 URL

- **Frontend**: `https://hyperasset-llm.web.app`
- **Backend**: `https://stock-analysis-api-xxxxx-xx.a.run.app`
- **API Docs**: `https://stock-analysis-api-xxxxx-xx.a.run.app/docs`

## 🚨 문제 해결

### 일반적인 문제들

#### 1. 권한 오류 (Linux/Mac)
```bash
chmod +x deploy.sh quick-deploy.sh
```

#### 2. PowerShell 실행 정책 (Windows)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 3. Firebase 프로젝트 설정
```bash
cd ../frontend
firebase init hosting
```

#### 4. Docker 빌드 오류
```bash
# Docker 데몬 실행 확인
docker --version
docker ps
```

## 📊 모니터링

### 로그 확인
```bash
# Cloud Run 로그
gcloud logs read --service=stock-analysis-api

# Firebase 로그
firebase hosting:channel:list
```

### 서비스 상태 확인
```bash
# Cloud Run 서비스 상태
gcloud run services describe stock-analysis-api --region asia-northeast3

# API 헬스체크
curl https://stock-analysis-api-xxxxx-xx.a.run.app/health
```

## 💰 비용 정보

- **Firebase Hosting**: 무료 (1GB/월)
- **Cloud Run**: 사용량 기반 (~$5-20/월)
- **AWS RDS**: 기존 비용 유지 (~$8-17/월)

## 📞 지원

문제가 발생하면:
1. `FIREBASE_DEPLOYMENT_README.md` 참조
2. `DEPLOYMENT_CHECKLIST.md` 확인
3. 로그 파일 확인
4. 개발팀에 문의

---

**🎉 배포 성공 시 확인사항:**
- [ ] 프론트엔드 접속 가능
- [ ] 백엔드 API 응답
- [ ] 데이터베이스 연결
- [ ] 모든 기능 정상 작동 