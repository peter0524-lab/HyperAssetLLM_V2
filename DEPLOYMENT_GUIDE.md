# 🚀 HyperAsset LLM 프로젝트 완전 배포 가이드

## 📋 **개요**
HyperAsset LLM 프로젝트를 GCP VM + Docker Compose + NGINX HTTPS로 완전 배포하는 방법입니다.

## 🏗️ **배포 아키텍처**
- **프론트엔드**: Firebase Hosting (HTTPS)
- **백엔드**: GCP Compute Engine VM + Docker Compose + NGINX (HTTPS)
- **도메인**: hyperasset.site
- **통신**: Firebase(HTTPS) → NGINX(HTTPS) → Docker Services(HTTP)

---

## 📝 **1단계: 사전 준비**

### 1.1 도메인 구매 및 DNS 설정
```bash
# 도메인: hyperasset.site 구매
# DNS A 레코드 설정
# Type: A, Name: @, Value: [GCP VM 외부 IP]
```

### 1.2 GCP VM 생성
```bash
# GCP Console에서 VM 인스턴스 생성
# Name: hyperasset-backend
# Zone: asia-northeast1-a
# Machine type: e2-medium (2 vCPU, 4 GB)
# Boot disk: Ubuntu 20.04 LTS
# Firewall: HTTP, HTTPS 허용
```

### 1.3 Git 저장소 준비
```bash
# GitHub에 프로젝트 업로드
# Repository: https://github.com/oen123456/HypperassetLLM_e2e.git
```

---

## 🐳 **2단계: Docker 설정 파일 생성**

### 2.1 베이스 Dockerfile 생성
```dockerfile
# Dockerfile.base
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치 (OpenCV 의존성 포함)
RUN apt-get update && apt-get install -y --fix-missing \
    gcc \
    g++ \
    curl \
    wget \
    git \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python 환경 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENV=production

# Python 의존성 설치
COPY stock_analysis_service/requirements_final_complete.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_final_complete.txt

# 공통 코드 복사
COPY stock_analysis_service/shared/ ./shared/
COPY stock_analysis_service/config/ ./config/
COPY stock_analysis_service/database/ ./database/
COPY stock_analysis_service/service_manager.py ./service_manager.py

# ChromaDB 데이터 디렉토리 생성
RUN mkdir -p /app/data/chroma
```

### 2.2 개별 서비스 Dockerfile 생성
```dockerfile
# stock_analysis_service/services/api_gateway/Dockerfile
FROM hyperasset-base:latest

COPY stock_analysis_service/services/api_gateway/ ./services/api_gateway/

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["python", "services/api_gateway/main.py"]
```

```dockerfile
# stock_analysis_service/services/user_service/Dockerfile
FROM hyperasset-base:latest

COPY stock_analysis_service/services/user_service/ ./services/user_service/

EXPOSE 8006

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

CMD ["python", "services/user_service/user_service.py"]
```

### 2.3 docker-compose.yml 생성
```yaml
services:
  # 베이스 이미지 빌드
  base:
    build:
      context: .
      dockerfile: Dockerfile.base
    image: hyperasset-base:latest

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - api-gateway
      - user-service
      - news-service
      - disclosure-service
      - chart-service
      - flow-service
    restart: unless-stopped

  api-gateway:
    build:
      context: .
      dockerfile: stock_analysis_service/services/api_gateway/Dockerfile
    depends_on:
      - base
    ports:
      - "8005:8005"
    environment:
      - ENV=production
      - DATABASE_HOST=database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com
      - DATABASE_PORT=3306
      - DATABASE_USER=admin
      - DATABASE_PASSWORD=Peter0524!
      - DATABASE_NAME=HyperAsset
    restart: unless-stopped

  user-service:
    build:
      context: .
      dockerfile: stock_analysis_service/services/user_service/Dockerfile
    depends_on:
      - base
    ports:
      - "8006:8006"
    environment:
      - ENV=production
      - DATABASE_HOST=database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com
      - DATABASE_PORT=3306
      - DATABASE_USER=admin
      - DATABASE_PASSWORD=Peter0524!
      - DATABASE_NAME=HyperAsset
    restart: unless-stopped

  news-service:
    build:
      context: .
      dockerfile: stock_analysis_service/services/news_service/Dockerfile
    depends_on:
      - base
    ports:
      - "8001:8001"
    volumes:
      - ./stock_analysis_service/data/chroma:/app/data/chroma
    environment:
      - ENV=production
      - DATABASE_HOST=database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com
      - DATABASE_PORT=3306
      - DATABASE_USER=admin
      - DATABASE_PASSWORD=Peter0524!
      - DATABASE_NAME=HyperAsset
      - HYPERCLOVA_API_KEY=nv-b8935535a68442e3bce731a356b119a4Xbzy
      - HYPERCLOVA_API_URL=https://clovastudio.stream.ntruss.com/testapp/v3/chat-completions/HCX-005
    restart: unless-stopped

  disclosure-service:
    build:
      context: .
      dockerfile: stock_analysis_service/services/disclosure_service/Dockerfile
    depends_on:
      - base
    ports:
      - "8002:8002"
    environment:
      - ENV=production
      - DATABASE_HOST=database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com
      - DATABASE_PORT=3306
      - DATABASE_USER=admin
      - DATABASE_PASSWORD=Peter0524!
      - DATABASE_NAME=HyperAsset
    restart: unless-stopped

  chart-service:
    build:
      context: .
      dockerfile: stock_analysis_service/services/chart_service/Dockerfile
    depends_on:
      - base
    ports:
      - "8003:8003"
    environment:
      - ENV=production
      - DATABASE_HOST=database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com
      - DATABASE_PORT=3306
      - DATABASE_USER=admin
      - DATABASE_PASSWORD=Peter0524!
      - DATABASE_NAME=HyperAsset
    restart: unless-stopped

  flow-service:
    build:
      context: .
      dockerfile: stock_analysis_service/services/flow_analysis_service/Dockerfile
    depends_on:
      - base
    ports:
      - "8010:8010"
    environment:
      - ENV=production
      - DATABASE_HOST=database-1.c7gaw6asmxbo.ap-northeast-2.rds.amazonaws.com
      - DATABASE_PORT=3306
      - DATABASE_USER=admin
      - DATABASE_PASSWORD=Peter0524!
      - DATABASE_NAME=HyperAsset
    restart: unless-stopped

networks:
  default:
    driver: bridge

volumes:
  chroma_data:
    driver: local
```

### 2.4 nginx.conf 생성
```nginx
events {
    worker_connections 1024;
}

http {
    upstream api_gateway {
        server api-gateway:8005;
    }

    upstream user_service {
        server user-service:8006;
    }

    upstream news_service {
        server news-service:8001;
    }

    upstream chart_service {
        server chart-service:8003;
    }
    
    upstream disclosure_service {
        server disclosure-service:8002;
    }
    
    upstream flow_service {
        server flow-service:8010;
    }
    
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }
    
    server {
        listen 443 ssl;
        server_name _;

        ssl_certificate /etc/letsencrypt/live/hyperasset.site/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/hyperasset.site/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;

        # Hide CORS headers from backend services
        proxy_hide_header Access-Control-Allow-Origin;
        proxy_hide_header Access-Control-Allow-Methods;
        proxy_hide_header Access-Control-Allow-Headers;

        # Set our own CORS headers
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization, X-Requested-With" always;

        # Handle OPTIONS requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }

        location /health {
            proxy_pass http://api_gateway;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /users/health {
            proxy_pass http://user_service/health;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /users {
            proxy_pass http://user_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /news {
            proxy_pass http://news_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /chart {
            proxy_pass http://chart_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /disclosure {
            proxy_pass http://disclosure_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /flow {
            proxy_pass http://flow_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api {
            proxy_pass http://api_gateway;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

---

## 🖥️ **3단계: GCP VM 설정**

### 3.1 VM 접속 및 기본 설정
```bash
# VM SSH 접속
gcloud compute ssh hyperasset-backend

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Git 설치
sudo apt install git -y
```

### 3.2 프로젝트 클론
```bash
# 프로젝트 디렉토리로 이동
cd ~
git clone https://github.com/oen123456/HypperassetLLM_e2e.git
cd HypperassetLLM_e2e
```

### 3.3 SSL 인증서 발급
```bash
# Certbot 설치
sudo apt install certbot -y

# 포트 80, 443 사용 중인 프로세스 종료
sudo fuser -k 80/tcp
sudo fuser -k 443/tcp

# SSL 인증서 발급
sudo certbot certonly --standalone -d hyperasset.site

# 인증서 경로 확인
sudo ls -la /etc/letsencrypt/live/hyperasset.site/
```

---

## 🚀 **4단계: Docker 배포**

### 4.1 Docker 이미지 빌드
```bash
# 베이스 이미지 빌드
docker-compose build base

# 모든 서비스 빌드
docker-compose build
```

### 4.2 서비스 실행
```bash
# 모든 서비스 시작
docker-compose up -d

# 상태 확인
docker-compose ps
```

### 4.3 문제 해결
```bash
# 포트 충돌 시 기존 프로세스 종료
sudo fuser -k 8001/tcp
sudo fuser -k 8002/tcp
sudo fuser -k 8003/tcp
sudo fuser -k 8005/tcp
sudo fuser -k 8006/tcp
sudo fuser -k 8010/tcp

# Docker 컨테이너 정리
docker-compose down
docker system prune -f

# 다시 시작
docker-compose up -d
```

---

## 🌐 **5단계: 프론트엔드 설정**

### 5.1 환경 변수 설정
```bash
# stock_analysis_service/frontend/.env.production 생성
echo "VITE_API_BASE_URL=https://hyperasset.site" > stock_analysis_service/frontend/.env.production
```

### 5.2 API 설정 수정
```typescript
// stock_analysis_service/frontend/src/lib/api.ts
const VM_BACKEND_URL = import.meta.env.VITE_API_BASE_URL || 'https://hyperasset.site';
const API_GATEWAY_URL = `${VM_BACKEND_URL}`;
const USER_SERVICE_URL = `${VM_BACKEND_URL}`;
```

### 5.3 Hero 컴포넌트 수정
```typescript
// stock_analysis_service/frontend/src/components/Hero.tsx
const checkDockerServices = async () => {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://hyperasset.site';
  const API_GATEWAY_URL = `${API_BASE_URL}/health`;
  const USER_SERVICE_URL = `${API_BASE_URL}/users/health`;
  
  // API Gateway 헬스체크
  const gatewayResponse = await fetch(API_GATEWAY_URL, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  // User Service 헬스체크
  const userResponse = await fetch(USER_SERVICE_URL, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
};
```

### 5.4 Firebase 배포
```bash
cd stock_analysis_service/frontend
npm run build
firebase deploy
```

---

## ✅ **6단계: 테스트 및 검증**

### 6.1 백엔드 테스트
```bash
# VM에서 직접 테스트
curl -k https://hyperasset.site/health
curl -k https://hyperasset.site/users/health

# 예상 결과:
# {"status":"healthy","timestamp":"...","gateway":"running","version":"2.0.0"}
# {"status":"healthy","service":"user_service"}
```

### 6.2 프론트엔드 테스트
- 웹사이트 접속: `https://hyperasset.web.app`
- "대시보드 시작하기" 버튼 클릭
- 헬스체크 성공 확인

---

## 🔧 **7단계: 문제 해결**

### 7.1 CORS 에러 해결
```nginx
# nginx.conf에 추가
proxy_hide_header Access-Control-Allow-Origin;
proxy_hide_header Access-Control-Allow-Methods;
proxy_hide_header Access-Control-Allow-Headers;

add_header Access-Control-Allow-Origin "*" always;
add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization, X-Requested-With" always;
```

### 7.2 SSL 인증서 문제
```bash
# Certbot 재설치
sudo apt purge python3-openssl
sudo apt install python3-openssl
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

### 7.3 포트 충돌 해결
```bash
# 사용 중인 포트 확인
sudo netstat -tlnp | grep ":800[0-9]"

# 프로세스 종료
sudo kill -9 [PID]
```

---

## 📊 **8단계: 모니터링**

### 8.1 서비스 상태 확인
```bash
# Docker 컨테이너 상태
docker-compose ps

# 로그 확인
docker-compose logs nginx
docker-compose logs api-gateway
docker-compose logs user-service
```

### 8.2 성능 모니터링
```bash
# 시스템 리소스 확인
htop
df -h
free -h
```

---

## 🎯 **최종 결과**

✅ **완전 배포된 시스템:**
- 🌐 프론트엔드: `https://hyperasset.web.app`
- ⚙️ 백엔드: `https://hyperasset.site`
- 🔐 SSL: Let's Encrypt 인증서
- 🐳 서비스: 6개 마이크로서비스 (API Gateway, User, News, Chart, Disclosure, Flow)
- 🟢 상태: 모든 서비스 정상 실행

---

## 📝 **주의사항**

1. **환경 변수**: 실제 프로덕션에서는 데이터베이스 비밀번호 등을 환경 변수로 관리
2. **보안**: 방화벽 설정 및 보안 그룹 확인
3. **백업**: 정기적인 데이터 백업 설정
4. **모니터링**: 로그 모니터링 및 알림 설정
5. **업데이트**: 정기적인 보안 업데이트

---

## 🆘 **문제 해결 가이드**

### 자주 발생하는 문제들:

1. **CORS 에러**: nginx.conf에서 `proxy_hide_header` 설정 확인
2. **SSL 인증서 문제**: Certbot 재설치 및 포트 80/443 확인
3. **포트 충돌**: `sudo fuser -k [PORT]/tcp` 명령으로 해결
4. **Docker 빌드 실패**: `docker system prune -f` 후 재시도
5. **서비스 시작 실패**: 로그 확인 후 의존성 문제 해결

---

## 📞 **지원**

문제가 발생하면 다음을 확인하세요:
1. 모든 단계를 순서대로 실행했는지 확인
2. 로그 파일에서 에러 메시지 확인
3. 네트워크 연결 및 방화벽 설정 확인
4. Docker 및 nginx 설정 파일 문법 확인

이 가이드를 따라하면 HyperAsset LLM 프로젝트를 완전히 배포할 수 있습니다! 🚀 