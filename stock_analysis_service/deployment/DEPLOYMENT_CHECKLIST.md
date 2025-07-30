# 🚀 HyperAsset LLM 배포 체크리스트

## ✅ 사전 준비사항

### 1. 개발 환경 설정
- [ ] Node.js 18+ 설치
- [ ] Python 3.11+ 설치
- [ ] Docker Desktop 설치
- [ ] Git 설치

### 2. 클라우드 계정 설정
- [ ] Firebase 계정 생성 및 로그인
- [ ] Google Cloud 계정 생성 및 로그인
- [ ] AWS RDS 접근 권한 확인

### 3. CLI 도구 설치
- [ ] Firebase CLI 설치: `npm install -g firebase-tools`
- [ ] Google Cloud CLI 설치
- [ ] Docker CLI 확인

### 4. 프로젝트 설정
- [ ] Firebase 프로젝트 생성: `hyperasset-llm`
- [ ] Google Cloud 프로젝트 설정: `hyperasset-llm`
- [ ] 환경 변수 확인

## 🔧 배포 전 체크

### 1. 코드 품질
- [ ] 모든 테스트 통과
- [ ] 린터 오류 해결
- [ ] 빌드 오류 없음
- [ ] 환경 변수 정리

### 2. 보안 체크
- [ ] API 키가 코드에 하드코딩되지 않음
- [ ] 데이터베이스 비밀번호 보안
- [ ] CORS 설정 확인
- [ ] HTTPS 강제 적용

### 3. 성능 체크
- [ ] 이미지 최적화
- [ ] 번들 크기 확인
- [ ] 메모리 사용량 확인
- [ ] 로딩 시간 테스트

## 📦 배포 단계별 체크리스트

### 1. 전체 배포 (deploy.sh)
- [ ] 프론트엔드 빌드 및 배포
- [ ] 백엔드 Docker 빌드 및 배포
- [ ] 환경 변수 설정
- [ ] 통합 테스트

### 2. 프론트엔드만 배포 (quick-deploy.sh)
- [ ] 프론트엔드 빌드 테스트: `npm run build`
- [ ] Firebase Hosting 배포: `firebase deploy --only hosting`
- [ ] 배포 URL 확인: `https://hyperasset-llm.web.app`

### 3. 백엔드만 배포 (deploy-backend.sh)
- [ ] Docker 이미지 빌드: `docker build -f deployment/Dockerfile .`
- [ ] Container Registry 푸시: `docker push gcr.io/hyperasset-llm/stock-analysis-api:latest`
- [ ] Cloud Run 배포: `gcloud run deploy stock-analysis-api`
- [ ] 환경 변수 확인
- [ ] 헬스체크: `curl https://stock-analysis-api-xxxxx-xx.a.run.app/health`

### 4. 연결 확인 (check-connection.sh)
- [ ] 프론트엔드 접속 확인
- [ ] 백엔드 헬스체크
- [ ] 프론트엔드에서 백엔드 API 호출 정상 동작 확인

## 🔍 배포 후 확인

- [ ] 메인 페이지 로딩: `https://hyperasset-llm.web.app`
- [ ] API 호출: `https://stock-analysis-api-xxxxx-xx.a.run.app/docs`
- [ ] 데이터베이스 연결 확인
- [ ] 사용자 인증/데이터 표시

## 🚨 문제 해결/문의
- [ ] CORS 에러 해결
- [ ] 데이터베이스 연결 실패 해결
- [ ] 메모리 부족 문제 해결
- [ ] Cold Start 최적화
- [ ] 로그 확인: `firebase hosting:channel:list`, `gcloud logs read --service=stock-analysis-api`

---

**🎉 분리 배포 체크리스트로 효율적이고 안전하게 운영하세요!** 