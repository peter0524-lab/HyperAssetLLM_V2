# 🐳 HyperAsset LLM Docker Compose 배포 가이드

## 📋 **개요**

기존의 `simple_server_starter.py` 방식에서 **Docker Compose 기반 마이크로서비스 아키텍처**로 전환되었습니다.

### **변경사항**
- ❌ **Before**: `simple_server_starter.py`로 각 서비스 개별 시작
- ✅ **After**: Docker Compose로 모든 서비스 통합 관리

## 🚀 **배포 방법**

### **Option 1: 빠른 시작 (로컬 개발)**

```bash
# 1. 빠른 시작 스크립트 실행
./quick-start.sh

# 또는 직접 Docker Compose 실행
docker-compose up -d

# 2. 서비스 상태 확인
docker-compose ps

# 3. 로그 확인
docker-compose logs -f

# 4. 서비스 중지
docker-compose down
```

### **Option 2: 프로덕션 배포**

```bash
# 1. 환경 변수 설정
cp env-config.example .env.production
# .env.production 파일에서 실제 값들로 수정

# 2. 프론트엔드 환경 변수 설정
cd stock_analysis_service/frontend
echo "VITE_API_BASE_URL=http://your-vm-ip" > .env.production
cd ../..

# 3. 전체 배포 실행
./deploy-docker-compose.sh
```

## 🏗️ **아키텍처 구조**

### **Docker Compose 서비스들**

| 서비스 | 포트 | 설명 |
|--------|------|------|
| `api-gateway` | 8005 | 메인 API 게이트웨이 |
| `user-service` | 8006 | 사용자 관리 서비스 |
| `news-service` | 8001 | 뉴스 분석 서비스 |
| `disclosure-service` | 8002 | 공시 분석 서비스 |
| `chart-service` | 8003 | 차트 분석 서비스 |
| `flow-analysis-service` | 8010 | 자금 흐름 분석 |
| `business-report-service` | 8007 | 사업보고서 분석 |
| `report-service` | 8008 | 리포트 생성 서비스 |
| `orchestrator` | 8000 | 서비스 오케스트레이터 |

### **네트워크 구조**

```
Internet
    ↓
Firebase Hosting (Frontend)
    ↓ (API calls)
Docker Compose Network
    ├── API Gateway (8005) ← 메인 진입점
    ├── User Service (8006)
    ├── News Service (8001)
    ├── Other Services...
    └── AWS RDS (Database)
```

## 🎯 **프론트엔드 동작 변경**

### **Before (simple_server_starter 방식)**
```javascript
// Hero.tsx - 기존 방식
fetch('/api/start-servers', { method: 'POST' })
```

### **After (Docker Compose 방식)**
```javascript
// Hero.tsx - 새로운 방식
const checkDockerServices = async () => {
  // API Gateway 헬스체크
  await fetch('http://localhost:8005/health')
  
  // User Service 헬스체크  
  await fetch('http://localhost:8006/health')
}
```

## 🔧 **개발 워크플로우**

### **1. 로컬 개발**
```bash
# 백엔드 시작
docker-compose up -d

# 프론트엔드 시작 (별도 터미널)
cd stock_analysis_service/frontend
npm run dev
```

### **2. 코드 변경 후 재시작**
```bash
# 특정 서비스만 재빌드
docker-compose build user-service
docker-compose up -d user-service

# 전체 재빌드
docker-compose build --no-cache
docker-compose up -d
```

### **3. 디버깅**
```bash
# 특정 서비스 로그 확인
docker-compose logs -f user-service

# 컨테이너 내부 접근
docker-compose exec user-service bash

# 서비스 상태 확인
docker-compose ps
curl http://localhost:8005/health
```

## 🚨 **문제 해결**

### **서비스가 시작되지 않는 경우**
```bash
# 1. 컨테이너 상태 확인
docker-compose ps

# 2. 로그 확인
docker-compose logs service-name

# 3. 컨테이너 재시작
docker-compose restart service-name

# 4. 완전히 재시작
docker-compose down
docker-compose up -d
```

### **포트 충돌 문제**
```bash
# 포트 사용 중인 프로세스 확인 (Windows)
netstat -ano | findstr :8005

# 프로세스 종료 (Windows)
taskkill /PID <PID번호> /F
```

### **데이터베이스 연결 실패**
1. AWS RDS 보안 그룹 확인
2. VPC 설정 확인
3. 환경 변수 DATABASE_* 값들 확인

## 📦 **배포 체크리스트**

### **사전 준비**
- [ ] Docker 및 Docker Compose 설치
- [ ] Firebase CLI 설치 (`npm install -g firebase-tools`)
- [ ] AWS RDS 접근 권한 확인
- [ ] VM 또는 서버 준비

### **로컬 테스트**
- [ ] `docker-compose up -d` 실행
- [ ] 모든 서비스 헬스체크 통과
- [ ] 프론트엔드에서 백엔드 API 호출 성공

### **프로덕션 배포**
- [ ] 환경 변수 설정 완료
- [ ] 프론트엔드 빌드 및 Firebase 배포
- [ ] 백엔드 Docker Compose 배포
- [ ] 전체 시스템 통합 테스트

## 🎉 **배포 완료 후 확인사항**

1. **프론트엔드 접속**: https://hyperasset-llm.web.app
2. **대시보드 시작하기 버튼 클릭**: Docker 서비스 헬스체크 실행
3. **API 엔드포인트 확인**: 
   - API Gateway: `http://your-vm:8005/health`
   - User Service: `http://your-vm:8006/health`
4. **로그 모니터링**: `docker-compose logs -f`

---

**🔄 기존 방식 대비 장점:**
- ✅ 서비스별 독립적 관리 및 스케일링
- ✅ 자동 재시작 및 헬스체크
- ✅ 통합 로그 관리
- ✅ 환경별 설정 분리
- ✅ 배포 자동화