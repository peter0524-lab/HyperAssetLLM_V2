# 📊 주식 분석 시스템 API 아키텍처 v2 - 완전한 엔드포인트 분석

## 🎯 1. 서비스 개요 및 실행 상태

### 🚀 start_all_services.py 실행 시 시작되는 서비스들

| 서비스명                   | 포트 | 상태          | 주요 기능                      |
| -------------------------- | ---- | ------------- | ------------------------------ |
| **User Service**           | 8006 | ✅ 상시 실행  | 사용자 관리, 프로필, 종목 설정 |
| **News Service**           | 8001 | ✅ 상시 실행  | 뉴스 수집, 분석, 영향도 계산   |
| **Disclosure Service**     | 8002 | ✅ 상시 실행  | 공시 정보 수집 및 분석         |
| **Chart Service**          | 8003 | ✅ 상시 실행  | 차트 분석, 기술적 지표 계산    |
| **Report Service**         | 8004 | ✅ 상시 실행  | 종합 리포트 생성               |
| **API Gateway**            | 8005 | ✅ 상시 실행  | 모든 서비스의 단일 진입점      |
| **Flow Analysis Service**  | 8010 | ✅ 상시 실행  | 자금 흐름 분석                 |
| **Orchestrator Scheduler** | -    | ✅ 백그라운드 | 서비스 스케줄링 및 조정        |

> **답변 1**: 네, `start_all_services.py` 실행 시 **8개의 서비스가 모두 백그라운드에서 상시 실행**됩니다. 각 서비스는 독립적인 FastAPI 서버로 동작하며, API Gateway를 통해 통신합니다.

## 🏗️ 2. 전체 시스템 아키텍처

### 📋 시스템 계층 구조

```
Frontend/Client
    ↓
API Gateway (8005) - 단일 진입점
    ↓
┌─────────────────────────────────────────────────────┐
│              Microservices Layer                     │
├─────────────┬─────────────┬─────────────┬───────────┤
│ User        │ News        │ Disclosure  │ Chart     │
│ Service     │ Service     │ Service     │ Service   │
│ (8006)      │ (8001)      │ (8002)      │ (8003)    │
├─────────────┼─────────────┼─────────────┼───────────┤
│ Report      │ Flow        │ Orchestr.   │ Shared    │
│ Service     │ Analysis    │ Scheduler   │ Modules   │
│ (8004)      │ (8010)      │ (BG)        │           │
└─────────────┴─────────────┴─────────────┴───────────┘
    ↓
Database Layer (MySQL, ChromaDB)
```

## 🔄 3. API 엔드포인트 맵핑

### 🌐 API Gateway (8005) - 모든 요청의 진입점

#### **3.1 시스템 관리 엔드포인트**

| Method | Endpoint           | 목적                  | 연결 서비스 |
| ------ | ------------------ | --------------------- | ----------- |
| `GET`  | `/`                | 시스템 기본 정보      | -           |
| `GET`  | `/health`          | API Gateway 상태 확인 | -           |
| `GET`  | `/metrics`         | Prometheus 메트릭     | -           |
| `GET`  | `/services/status` | 모든 서비스 상태 조회 | 모든 서비스 |

#### **3.2 사용자 관리 API (User Service 프록시)**

| Method   | Endpoint                                  | 목적               | 실제 연결                                    |
| -------- | ----------------------------------------- | ------------------ | -------------------------------------------- |
| `GET`    | `/api/user/health`                        | User Service 상태  | → `8006/health`                              |
| `GET`    | `/api/user/config/{user_id}`              | 전체 설정 조회     | → `8006/users/{user_id}/config`              |
| `POST`   | `/api/user/config/{user_id}`              | 전체 설정 업데이트 | → `8006/users/{user_id}/profile`             |
| `PUT`    | `/api/user/config/{user_id}`              | 전체 설정 수정     | → `8006/users/{user_id}/profile`             |
| `GET`    | `/api/user/stocks/{user_id}`              | 사용자 종목 조회   | → `8006/users/{user_id}/stocks`              |
| `POST`   | `/api/user/stocks/{user_id}`              | 사용자 종목 설정   | → `8006/users/{user_id}/stocks`              |
| `DELETE` | `/api/user/stocks/{user_id}/{stock_code}` | 종목 삭제          | → `8006/users/{user_id}/stocks/{stock_code}` |
| `GET`    | `/api/user/model/{user_id}`               | 모델 설정 조회     | → `8006/users/{user_id}/config`              |
| `POST`   | `/api/user/model/{user_id}`               | 모델 설정 업데이트 | → `8006/users/{user_id}/model`               |
| `GET`    | `/api/user/thresholds/{user_id}`          | 임계값 조회        | → `8006/users/{user_id}/config`              |
| `POST`   | `/api/user/thresholds/{user_id}`          | 임계값 설정        | → `8006/users/{user_id}/profile`             |

#### **3.3 뉴스 서비스 API**

| Method | Endpoint                   | 목적              | 실제 연결               |
| ------ | -------------------------- | ----------------- | ----------------------- |
| `GET`  | `/api/news/health`         | News Service 상태 | → `8001/health`         |
| `GET`  | `/api/news/signal`         | 뉴스 시그널 조회  | → `8001/signal`         |
| `POST` | `/api/news/execute`        | 뉴스 수집 실행    | → `8001/execute`        |
| `POST` | `/api/news/check-schedule` | 스케줄 확인       | → `8001/check-schedule` |

#### **3.4 공시 서비스 API**

| Method | Endpoint                         | 목적                    | 실제 연결               |
| ------ | -------------------------------- | ----------------------- | ----------------------- |
| `GET`  | `/api/disclosure/health`         | Disclosure Service 상태 | → `8002/health`         |
| `POST` | `/api/disclosure/execute`        | 공시 수집 실행          | → `8002/execute`        |
| `POST` | `/api/disclosure/check-schedule` | 스케줄 확인             | → `8002/check-schedule` |
| `GET`  | `/api/disclosure/recent`         | 최근 공시 조회          | → `8002/signal`         |

#### **3.5 차트 분석 서비스 API**

| Method | Endpoint                           | 목적               | 실제 연결                     |
| ------ | ---------------------------------- | ------------------ | ----------------------------- |
| `GET`  | `/api/chart/health`                | Chart Service 상태 | → `8003/health`               |
| `POST` | `/api/chart/execute`               | 차트 분석 실행     | → `8003/execute`              |
| `POST` | `/api/chart/check-schedule`        | 스케줄 확인        | → `8003/check-schedule`       |
| `GET`  | `/api/chart/analysis/{stock_code}` | 개별 종목 분석     | → `8003/analyze/{stock_code}` |

#### **3.6 리포트 서비스 API**

| Method | Endpoint                     | 목적                | 실제 연결               |
| ------ | ---------------------------- | ------------------- | ----------------------- |
| `GET`  | `/api/report/health`         | Report Service 상태 | → `8004/health`         |
| `POST` | `/api/report/execute`        | 리포트 생성 실행    | → `8004/execute`        |
| `POST` | `/api/report/check-schedule` | 스케줄 확인         | → `8004/check-schedule` |
| `GET`  | `/api/report/latest`         | 최신 리포트 조회    | → `8004/signal`         |
| `GET`  | `/api/report/history`        | 리포트 히스토리     | → `8004/signal`         |

#### **3.7 플로우 분석 서비스 API**

| Method | Endpoint                          | 목적                  | 실제 연결               |
| ------ | --------------------------------- | --------------------- | ----------------------- |
| `GET`  | `/api/flow/health`                | Flow Service 상태     | → `8010/health`         |
| `POST` | `/api/flow/execute`               | 플로우 분석 실행      | → `8010/execute`        |
| `POST` | `/api/flow/check-schedule`        | 스케줄 확인           | → `8010/check-schedule` |
| `GET`  | `/api/flow/analysis/{stock_code}` | 개별 종목 플로우 분석 | → `8010/signal`         |

## 🔄 4. 서비스 간 통신 패턴

### 📊 4.1 Frontend → Backend 데이터 흐름 (test_frontend_data_flow.py)

#### **1단계: 사용자 프로필 생성**

```
Frontend → API Gateway (8005) → User Service (8006)
     또는
Frontend → User Service (8006) 직접 호출
```

- **Endpoint**: `POST /users/profile`
- **데이터**: 사용자명, 전화번호, 임계값 설정

#### **2단계: 종목 설정**

```
Frontend → API Gateway (8005) → User Service (8006)
```

- **Endpoint**: `POST /api/user/stocks/{user_id}`
- **데이터**: 관심 종목 리스트, 활성화 상태

#### **3단계: 모델 설정**

```
Frontend → API Gateway (8005) → User Service (8006)
```

- **Endpoint**: `POST /api/user/model/{user_id}`
- **데이터**: 선택한 AI 모델 (hyperclova, chatgpt 등)

#### **4단계: 서비스 실행**

```
Frontend → API Gateway (8005) → 각 분석 서비스
```

- 뉴스, 공시, 차트, 리포트, 플로우 분석 서비스 순차 실행

### 📊 4.2 서비스 간 내부 통신

#### **User Service → 다른 서비스들**

```
User Service (8006) → News Service (8001): 사용자 설정 전달
User Service (8006) → Disclosure Service (8002): 관심 종목 전달
User Service (8006) → Chart Service (8003): 분석 대상 종목 전달
User Service (8006) → Report Service (8004): 리포트 설정 전달
User Service (8006) → Flow Analysis Service (8010): 분석 파라미터 전달
```

#### **각 서비스별 사용자 설정 엔드포인트**

| 서비스                | 설정 수신 엔드포인트       | 설정 조회 엔드포인트         |
| --------------------- | -------------------------- | ---------------------------- |
| News Service          | `POST /set-user/{user_id}` | `GET /user-config/{user_id}` |
| Disclosure Service    | `POST /set-user/{user_id}` | `GET /user-config/{user_id}` |
| Chart Service         | `POST /set-user/{user_id}` | `GET /user-config/{user_id}` |
| Report Service        | `POST /set-user/{user_id}` | `GET /user-config/{user_id}` |
| Flow Analysis Service | `POST /set-user/{user_id}` | `GET /user-config/{user_id}` |

### 📊 4.3 스케줄링 및 오케스트레이션

#### **Orchestrator Scheduler의 역할**

- **자동 스케줄링**: 정해진 시간에 각 서비스 실행
- **상태 모니터링**: 모든 서비스의 헬스체크
- **장애 복구**: 서비스 다운 시 자동 재시작
- **리소스 관리**: 시스템 리소스 최적화

#### **스케줄러 → 서비스 통신**

```
Scheduler → API Gateway (8005) → 각 서비스
```

- 정해진 시간에 `/execute` 엔드포인트 호출
- `/check-schedule` 으로 다음 실행 시간 확인

## 🔐 5. 보안 및 인증

### 🛡️ 5.1 API Gateway 보안 기능

- **Rate Limiting**: 요청 속도 제한
- **Circuit Breaker**: 장애 전파 방지
- **Request Validation**: 입력 데이터 검증
- **CORS 설정**: 크로스 오리진 요청 제어

### 🔑 5.2 사용자 인증 흐름

```
Client → API Gateway → User Service (사용자 확인) → 각 분석 서비스
```

- **X-User-ID 헤더**: 사용자 식별
- **전화번호 기반 인증**: 중복 방지
- **세션 관리**: 사용자별 설정 캐싱

## 📈 6. 모니터링 및 로깅

### 📊 6.1 메트릭 수집

- **Prometheus 메트릭**: `/metrics` 엔드포인트
- **응답 시간 측정**: 모든 API 호출 추적
- **에러율 모니터링**: 실패 요청 추적
- **서비스 상태**: 실시간 헬스체크

### 📝 6.2 로그 관리

- **구조화된 로깅**: JSON 형태 로그
- **서비스별 로그 파일**: 각 서비스마다 개별 로그
- **에러 추적**: 스택 트레이스 포함
- **성능 로깅**: 응답 시간 및 처리량 기록

## 🔄 7. 데이터 흐름 요약

### 📊 7.1 사용자 등록 → 서비스 실행 전체 플로우

```
1. 사용자 프로필 생성 (User Service)
2. 종목 설정 (API Gateway → User Service)
3. 모델 설정 (API Gateway → User Service)
4. 설정 검증 (API Gateway → User Service)
5. 뉴스 수집 실행 (API Gateway → News Service)
6. 공시 수집 실행 (API Gateway → Disclosure Service)
7. 차트 분석 실행 (API Gateway → Chart Service)
8. 리포트 생성 실행 (API Gateway → Report Service)
9. 플로우 분석 실행 (API Gateway → Flow Analysis Service)
```

### 📊 7.2 실시간 데이터 처리

- **WebSocket 연결**: Flow Analysis Service의 실시간 데이터
- **캐싱 레이어**: 자주 요청되는 데이터 캐시
- **백그라운드 작업**: 대용량 데이터 처리 큐

---

## 🎯 핵심 포인트

1. **API Gateway (8005)**가 모든 외부 요청의 **단일 진입점** 역할
2. **User Service (8006)**가 사용자 설정의 **중앙 저장소** 역할
3. 각 분석 서비스는 **독립적**으로 동작하되, **사용자 설정을 공유**
4. **Orchestrator Scheduler**가 **자동화된 실행** 담당
5. 모든 서비스는 **start_all_services.py 실행 시 상시 동작**
6. **Frontend → API Gateway → Microservices** 구조로 확장성 확보

이 아키텍처는 **마이크로서비스 패턴**을 기반으로 한 **확장 가능하고 유지보수 용이한** 시스템입니다.
