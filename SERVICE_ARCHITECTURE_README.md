# HyperAsset 주식 분석 시스템 - 서비스 아키텍처 및 API 명세서

## 📋 목차

- [시스템 개요](#시스템-개요)
- [서비스 아키텍처](#서비스-아키텍처)
- [마이크로서비스 구성](#마이크로서비스-구성)
- [API 명세서](#api-명세서)
- [데이터베이스 구조](#데이터베이스-구조)
- [배포 및 운영](#배포-및-운영)

## 🔍 시스템 개요

**HyperAsset**은 AI 기반 주식 분석 시스템으로, 마이크로서비스 아키텍처를 기반으로 구축되었습니다.

### 주요 기능

- 📊 **실시간 차트 분석**: KIS API를 통한 실시간 주식 데이터 수집 및 8가지 기술적 지표 분석
- 📰 **뉴스 분석**: AI 기반 뉴스 분석 및 주식 영향도 평가
- 📋 **공시 분석**: 전자공시시스템(DART) API를 통한 공시 정보 분석
- 📈 **리포트 생성**: 종합적인 투자 분석 리포트 자동 생성
- 💰 **자금 흐름 분석**: 기관/외국인 투자자 자금 흐름 분석
- 👤 **사용자 개인화**: 사용자별 맞춤 종목 및 AI 모델 설정
- 🔔 **실시간 알림**: 텔레그램을 통한 실시간 투자 신호 알림

### 기술 스택

- **Backend**: Python, FastAPI, AsyncIO
- **Frontend**: React, TypeScript, Vite
- **Database**: MySQL, ChromaDB (Vector DB)
- **AI/ML**: Naver HyperCLOVA, OpenAI API, Gemini API
- **Message Queue**: Redis (캐싱)
- **Monitoring**: Prometheus, Structlog
- **API Integration**: KIS API, DART API, Telegram Bot API

## 🏗️ 서비스 아키텍처

### 전체 아키텍처 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend                               │
│                    (React + TypeScript)                        │
│                        Port: 3000                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                      API Gateway                               │
│                  (FastAPI + CORS)                              │
│   • 로드 밸런싱 • Circuit Breaker • 캐싱 • 모니터링             │
│                        Port: 8005                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┬─────────────┬─────────────┐
         │                         │             │             │
┌────────▼─────────┐   ┌───────────▼──┐   ┌─────▼────┐   ┌────▼─────┐
│   User Service   │   │ Orchestrator │   │News      │   │Chart     │
│   Port: 8006     │   │ Port: 8000   │   │Service   │   │Service   │
└──────────────────┘   └──────────────┘   │Port: 8001│   │Port: 8003│
                                          └──────────┘   └──────────┘

┌─────────────────┬────────────────┬─────────────────┬──────────────┐
│  Disclosure     │  Report        │  Flow Analysis  │ Business     │
│  Service        │  Service       │  Service        │ Report       │
│  Port: 8002     │  Port: 8004    │  Port: 8010     │ Service      │
└─────────────────┴────────────────┴─────────────────┴──────────────┘
```

### 데이터 흐름

```
External APIs ─┐
               ├─► Services ─► Database ─► AI Analysis ─► Notifications
User Input ────┘              (MySQL)     (LLM APIs)    (Telegram)
```

## 🔧 마이크로서비스 구성

### 1. API Gateway (`services/api_gateway/`)

- **포트**: 8005
- **역할**: 모든 마이크로서비스의 단일 진입점
- **주요 기능**:
  - 로드 밸런싱 (라운드 로빈)
  - Circuit Breaker 패턴
  - Redis 기반 캐싱
  - Prometheus 메트릭 수집
  - CORS 처리
  - 헬스체크 및 모니터링

### 2. User Service (`services/user_service/`)

- **포트**: 8006
- **역할**: 사용자 설정 및 프로필 관리
- **주요 기능**:
  - 사용자 프로필 CRUD
  - 종목 설정 관리
  - AI 모델 선택 설정
  - 서비스별 활성화 설정

### 3. Chart Service (`services/chart_service/`)

- **포트**: 8003
- **역할**: 실시간 차트 분석 및 기술적 지표 모니터링
- **주요 기능**:
  - KIS API 실시간 데이터 수집
  - 8가지 조건식 모니터링:
    - 골든크로스/데드크로스
    - 볼린저밴드 터치
    - 20일선 터치
    - RSI 과매수/과매도
    - 거래량 급증
    - MACD 골든크로스
    - 지지/저항선 돌파
  - WebSocket 기반 실시간 모니터링
  - 스마트 스케줄링 (장중/장후/주말 모드)

### 4. News Service (`services/news_service/`)

- **포트**: 8001
- **역할**: 뉴스 수집 및 AI 분석
- **주요 기능**:
  - 네이버 뉴스 크롤링
  - 중복 제거 (SimHash 알고리즘)
  - AI 기반 뉴스 분석 및 영향도 평가
  - ChromaDB를 통한 벡터 검색

### 5. Disclosure Service (`services/disclosure_service/`)

- **포트**: 8002
- **역할**: 공시 정보 수집 및 분석
- **주요 기능**:
  - DART API 공시 데이터 수집
  - AI 기반 공시 내용 분석
  - 주요 공시 필터링 및 알림

### 6. Report Service (`services/report_service/`)

- **포트**: 8004
- **역할**: 종합 투자 리포트 생성
- **주요 기능**:
  - 다양한 소스 데이터 통합
  - AI 기반 종합 분석 리포트 생성
  - 투자 의견 및 목표가 제시

### 7. Flow Analysis Service (`services/flow_analysis_service/`)

- **포트**: 8010
- **역할**: 자금 흐름 분석
- **주요 기능**:
  - 기관/외국인 매매 동향 분석
  - 자금 흐름 패턴 분석
  - 투자자별 포지션 변화 추적

### 8. Orchestrator Service (`services/orchestrator/`)

- **포트**: 8000
- **역할**: 서비스 간 작업 조율 및 스케줄링
- **주요 기능**:
  - 서비스 간 작업 순서 조율
  - 스케줄링 관리
  - 작업 상태 모니터링

### 9. Service Manager

- **역할**: 모든 서비스의 생명주기 관리
- **주요 기능**:
  - 서비스 시작/중지/재시작
  - 헬스체크 모니터링
  - 의존성 관리
  - SQLite 기반 상태 추적

## 📡 API 명세서

### API Gateway Base URL

```
http://localhost:8005
```

### 1. 시스템 관리 API

#### 헬스체크

```http
GET /health
```

**응답**:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "gateway": "running",
  "version": "2.0.0"
}
```

#### 서비스 상태 조회

```http
GET /services/status
```

**응답**:

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "services": {
    "news_service": {
      "status": "running",
      "instances": ["http://localhost:8001"],
      "response_time": 0.15,
      "circuit_breaker_state": "closed"
    }
  }
}
```

#### 메트릭 조회

```http
GET /metrics
```

**응답**: Prometheus 형식 메트릭

### 2. 사용자 관리 API

#### 사용자 프로필 생성

```http
POST /users/profile
Content-Type: application/json

{
  "username": "홍길동",
  "phone_number": "01012345678",
  "news_similarity_threshold": 0.7,
  "news_impact_threshold": 0.6
}
```

#### 사용자 설정 조회

```http
GET /api/user/config/{user_id}
```

#### 사용자 종목 설정

```http
POST /api/user/stocks/{user_id}
Content-Type: application/json

{
  "stocks": [
    {"stock_code": "005930", "stock_name": "삼성전자", "enabled": true},
    {"stock_code": "000660", "stock_name": "SK하이닉스", "enabled": true}
  ]
}
```

#### 사용자 AI 모델 설정

```http
POST /api/user/model/{user_id}
Content-Type: application/json

{
  "model_type": "hyperclova"
}
```

### 3. 서비스별 API

#### 뉴스 서비스

```http
# 뉴스 분석 실행
POST /api/news/execute
Headers: X-User-ID: 1

# 최근 뉴스 신호 조회
GET /api/news/signal
```

#### 차트 서비스

```http
# 차트 분석 실행
POST /api/chart/execute
Headers: X-User-ID: 1

# 특정 종목 분석 조회
GET /api/chart/analysis/{stock_code}
```

#### 공시 서비스

```http
# 공시 분석 실행
POST /api/disclosure/execute
Headers: X-User-ID: 1

# 최근 공시 조회
GET /api/disclosure/recent
```

#### 리포트 서비스

```http
# 리포트 생성 실행
POST /api/report/execute
Headers: X-User-ID: 1

# 최신 리포트 조회
GET /api/report/latest
```

### 4. 서비스 관리 API

#### 선택한 서비스 시작

```http
POST /api/services/start-selected
Content-Type: application/json

{
  "services": ["news_service", "chart_service"],
  "user_id": "1"
}
```

#### 개별 서비스 제어

```http
POST /api/services/{service_name}/start
POST /api/services/{service_name}/stop
GET /api/services/{service_name}/status
```

## 🗄️ 데이터베이스 구조

### MySQL 테이블 구조

#### 사용자 관리

```sql
-- 사용자 프로필
CREATE TABLE user_profiles (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) UNIQUE,
    news_similarity_threshold FLOAT DEFAULT 0.7,
    news_impact_threshold FLOAT DEFAULT 0.6,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 사용자 종목 설정
CREATE TABLE user_stocks (
    user_id VARCHAR(50),
    stock_code VARCHAR(20),
    stock_name VARCHAR(100),
    enabled BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_id, stock_code)
);

-- 사용자 AI 모델 설정
CREATE TABLE user_model (
    user_id VARCHAR(50) PRIMARY KEY,
    model_type ENUM('hyperclova', 'openai', 'gemini') DEFAULT 'hyperclova'
);

-- 사용자 원하는 서비스 설정
CREATE TABLE user_wanted_service (
    user_id VARCHAR(50) PRIMARY KEY,
    phone_number VARCHAR(20),
    news_service BOOLEAN DEFAULT FALSE,
    disclosure_service BOOLEAN DEFAULT FALSE,
    report_service BOOLEAN DEFAULT FALSE,
    chart_service BOOLEAN DEFAULT FALSE,
    flow_service BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### 차트 분석 결과

```sql
CREATE TABLE chart_analysis_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    close_price FLOAT DEFAULT NULL,
    volume BIGINT DEFAULT NULL,
    -- 조건 만족 여부
    golden_cross BOOLEAN DEFAULT FALSE,
    dead_cross BOOLEAN DEFAULT FALSE,
    bollinger_touch BOOLEAN DEFAULT FALSE,
    ma20_touch BOOLEAN DEFAULT FALSE,
    rsi_condition BOOLEAN DEFAULT FALSE,
    volume_surge BOOLEAN DEFAULT FALSE,
    macd_golden_cross BOOLEAN DEFAULT FALSE,
    support_resistance_break BOOLEAN DEFAULT FALSE,
    details JSON,
    INDEX idx_stock_date (stock_code, date)
);
```

### ChromaDB Collections

- **news_analysis**: 뉴스 벡터 임베딩 저장
- **disclosure_analysis**: 공시 벡터 임베딩 저장
- **report_analysis**: 리포트 벡터 임베딩 저장

## 🚀 배포 및 운영

### 서비스 시작

```bash
# 전체 서비스 시작
python service_manager.py start-core

# 선택적 서비스 시작
python service_manager.py start-services news_service,chart_service

# 서비스 상태 확인
python service_manager.py status
```

### 환경 설정

주요 환경 변수:

- `HYPERASSET_USER_ID`: 현재 사용자 ID
- `MYSQL_HOST`: MySQL 서버 주소
- `REDIS_URL`: Redis 캐시 서버 주소
- `KIS_API_KEY`: KIS API 인증 키
- `DART_API_KEY`: DART API 인증 키
- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰

### 모니터링

- **Prometheus 메트릭**: `http://localhost:8005/metrics`
- **서비스 상태**: `http://localhost:8005/services/status`
- **캐시 통계**: `http://localhost:8005/cache/stats`
- **성능 통계**: `http://localhost:8005/performance/stats`

### 로그 파일

- `service_manager.log`: 서비스 관리자 로그
- `services/*/logs/`: 각 서비스별 로그

## 🔧 개발 및 확장

### 새로운 서비스 추가

1. `services/` 디렉토리에 새 서비스 생성
2. `service_manager.py`의 `service_definitions`에 추가
3. `api_gateway/main.py`에 라우팅 추가

### API 버전 관리

현재 API 버전: `v2.0.0`

- 주요 변경사항은 버전 업그레이드
- 하위 호환성 유지

### 보안 고려사항

- API 키 관리: 환경 변수로 분리
- CORS 설정: 프로덕션에서는 특정 도메인만 허용
- Rate Limiting: API Gateway에서 구현
- 사용자 인증: JWT 토큰 기반 (추후 구현 예정)

---

**최종 업데이트**: 2024년 1월 15일  
**문서 버전**: 2.0.0  
**개발팀**: HyperAsset Development Team
