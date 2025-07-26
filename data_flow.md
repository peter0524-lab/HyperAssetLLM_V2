# 📊 주식 분석 시스템 - 완전한 데이터 흐름 분석

## 🎯 **개요**

이 문서는 Frontend에서 Backend로 전송되는 사용자 데이터의 완전한 흐름을 분석합니다.

### **Frontend에서 전송하는 데이터**

`user_id` (문자열)

`user_name` (사용자명)

`phone_number` (전화번호)

`news_similarity_threshold` (뉴스 유사도 임계값)

`news_impact_threshold` (뉴스 영향도 임계값)

`model_type` (LLM 모델 타입)

`stock_code` (종목 코드)

`stock_name` (종목명)

---

## 🔄 **데이터 흐름 단계별 분석**

### **1단계: 사용자 프로필 생성**

```
Frontend → API Gateway → User Service → MySQL
```

**API 엔드포인트:** `POST /api/user/profile`

**요청 데이터:**

```json
{
  "username": "테스트유저1",
  "phone_number": "01012345678",
  "news_similarity_threshold": 0.8,
  "news_impact_threshold": 0.7
}
```

**처리 과정:**

1. Frontend가 사용자 기본 정보를 API Gateway로 전송
2. API Gateway가 User Service로 라우팅
3. User Service에서 고유한 `user_id` 생성 (해시 기반)
4. MySQL `user_profiles` 테이블에 저장
5. 생성된 `user_id` 반환

**응답 데이터:**

```json
{
  "success": true,
  "message": "사용자 프로필이 성공적으로 생성되었습니다",
  "data": {
    "user_id": "803873f4ace4ff32885d"
  }
}
```

### **2단계: 종목 설정**

```
Frontend → API Gateway → User Service → MySQL
```

**API 엔드포인트:** `POST /api/user/stocks/{user_id}`

**요청 데이터:**

```json
{
  "stocks": [
    { "stock_code": "005930", "stock_name": "삼성전자" },
    { "stock_code": "000660", "stock_name": "SK하이닉스" }
  ]
}
```

**처리 과정:**

1. Frontend가 선택한 종목 정보를 전송
2. API Gateway가 User Service로 라우팅
3. User Service에서 각 종목을 `user_stocks` 테이블에 저장
4. 외래키 제약조건으로 `user_profiles`와 연결

### **3단계: LLM 모델 설정**

```
Frontend → API Gateway → User Service → MySQL
```

**API 엔드포인트:** `POST /api/user/model/{user_id}`

**요청 데이터:**

```json
{
  "model_type": "gemini"
}
```

**처리 과정:**

1. Frontend가 선택한 LLM 모델 정보를 전송
2. API Gateway가 User Service로 라우팅
3. User Service에서 `user_model` 테이블에 저장 (UPSERT)

---

## ⚙️ **설정 관리 시스템**

### **User Config Manager (중앙 집중식)**

**역할:**

- 모든 사용자 설정의 중앙 관리
- 5분 TTL 메모리 캐시 제공
- 각 서비스에서 통합된 인터페이스로 설정 조회

**캐시 전략:**

```python
cache_key = f"user_config_{user_id}"
cache_ttl = 300  # 5분
```

**설정 변경 시 반영 과정:**

1. 설정 변경 → MySQL 저장
2. 해당 사용자 캐시 무효화 (`_clear_cache(user_id)`)
3. 다음 요청 시 새로운 설정 자동 로드

---

## 🚀 **서비스 실행 흐름**

### **분석 서비스 호출**

```
Frontend → API Gateway → 각 서비스 → User Config Manager → MySQL
```

**API 엔드포인트:** `POST /api/{service}/execute`

- `/api/news/execute` (뉴스 분석)
- `/api/disclosure/execute` (공시 분석)
- `/api/chart/execute` (차트 분석)
- `/api/report/execute` (보고서 생성)
- `/api/flow/execute` (자금 흐름 분석)

**처리 과정:**

1. Frontend가 분석 실행 요청
2. API Gateway가 `X-User-ID` 헤더에 `user_id` 포함하여 각 서비스로 라우팅
3. 각 서비스에서 헤더에서 `user_id` 추출
4. User Config Manager를 통해 사용자 설정 조회
5. 사용자별 맞춤 분석 실행

**헤더 전달:**

```http
X-User-ID: 803873f4ace4ff32885d
```

---

## 🗄️ **데이터베이스 스키마**

### **user_profiles 테이블**

```sql
user_id VARCHAR(50) PRIMARY KEY,
username VARCHAR(100) NOT NULL,
phone_number VARCHAR(20),
news_similarity_threshold FLOAT DEFAULT 1.1,
news_impact_threshold FLOAT DEFAULT 0.5,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

### **user_stocks 테이블**

```sql
user_id VARCHAR(50) NOT NULL,
stock_code VARCHAR(10) NOT NULL,
stock_name VARCHAR(100) NOT NULL,
enabled TINYINT(1) DEFAULT 1,
PRIMARY KEY (user_id, stock_code),
FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
```

### **user_model 테이블**

```sql
user_id VARCHAR(50) PRIMARY KEY,
model_type ENUM('hyperclova','chatgpt','claude','grok','gemini') DEFAULT 'hyperclova',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
```

---

## 🔄 **실시간 설정 반영**

### **현재 구현 방식: 캐시 기반**

**장점:**

- 빠른 응답 속도 (메모리 캐시)
- 데이터베이스 부하 감소
- 중앙 집중식 관리

**동작 방식:**

1. 각 서비스는 요청 시마다 User Config Manager 호출
2. 캐시가 유효하면 메모리에서 반환
3. 캐시가 만료되었으면 MySQL에서 최신 데이터 조회
4. 설정 변경 시 해당 사용자 캐시만 무효화

### **설정 변경 감지:**

```python
# 각 서비스에서
if service.current_user_id != user_id:
    await service.set_user_id(user_id)  # 설정 재로드
```

---

## 🔒 **보안 및 인증**

### **현재 상태:**

- ❌ **인증 시스템 미구현**
- ❌ **토큰/세션 관리 없음**
- ❌ **API 인가 없음**

### **보안 고려사항:**

- AuthMiddleware 파일이 존재하지만 비어있음
- 향후 JWT 토큰 기반 인증 구현 필요
- CORS 설정은 현재 모든 Origin 허용 (`"*"`)

---

## 📈 **성능 최적화**

### **연결 풀링:**

- API Gateway에서 각 서비스별 aiohttp.ClientSession 풀 관리
- 커넥션 재사용으로 성능 향상

### **Circuit Breaker:**

- 각 서비스별 Circuit Breaker 패턴 적용
- 장애 전파 방지

### **캐싱 전략:**

- User Config Manager: 5분 TTL 메모리 캐시
- 향후 Redis 캐시 도입 가능 (설정 존재)

---

## 🔮 **향후 개선 사항**

### **1. 실시간 알림 시스템**

- WebSocket 연결로 설정 변경 즉시 반영
- Server-Sent Events (SSE) 활용

### **2. 인증/인가 시스템**

- JWT 토큰 기반 인증
- Role-based Access Control (RBAC)

### **3. 분산 캐시**

- Redis Cluster 도입
- 서비스 간 캐시 동기화

### **4. 이벤트 기반 아키텍처**

- Message Queue (RabbitMQ/Kafka) 도입
- 비동기 이벤트 처리

---

## 📊 **데이터 흐름 요약**

1. **사용자 등록:** Frontend → API Gateway → User Service → MySQL
2. **설정 관리:** User Config Manager (캐시 + MySQL)
3. **서비스 실행:** Frontend → API Gateway → 각 서비스 → User Config Manager
4. **실시간 반영:** 캐시 무효화 + 다음 요청 시 자동 로드

**핵심 특징:**

- 중앙 집중식 설정 관리
- 캐시 기반 성능 최적화
- 마이크로서비스 아키텍처
- 외래키 제약조건으로 데이터 무결성 보장
