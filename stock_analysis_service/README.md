# 🚀 주식 분석 서비스 (Stock Analysis Service)

## 📋 목차

- [시스템 개요](#시스템-개요)
- [아키텍처](#아키텍처)
- [서비스 구성](#서비스-구성)
- [실행 방법](#실행-방법)
- [API 문서](#api-문서)
- [테스트](#테스트)
- [기술 스택](#기술-스택)

## 🎯 시스템 개요

주식 분석 서비스는 **마이크로서비스 아키텍처** 기반의 실시간 주식 데이터 분석 플랫폼입니다.
뉴스, 공시, 차트, 자금흐름 등 다양한 데이터를 수집하고 분석하여 투자 인사이트를 제공합니다.

### ✨ 주요 기능

- 📰 **실시간 뉴스 분석**: 주식 관련 뉴스 수집 및 영향도 분석
- 📊 **공시 정보 분석**: DART API 연동 공시 데이터 분석
- 📈 **차트 패턴 분석**: 기술적 분석 및 패턴 인식
- 💰 **자금흐름 분석**: 기관/외국인 매매 동향 분석
- 📋 **주간 리포트**: 종합 분석 리포트 생성
- 👤 **사용자 설정**: 개인화된 분석 설정 관리
- 🔄 **오케스트레이션**: 서비스 간 워크플로우 관리
- 🌐 **API Gateway**: 통합 API 엔드포인트 제공

## 🏗️ 아키텍처

### 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           🖥️  클라이언트 레이어                                    │
│                     웹 애플리케이션 / 모바일 앱 / API 클라이언트                    │
└─────────────────────────────────┬───────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          🌐 API Gateway (포트: 8005)                            │
│                    라우팅 • 인증 • 캐싱 • 모니터링 • 로드밸런싱                    │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬──────────────────────────────────┘
   │      │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐┌─────┐
│🎭   ││📰   ││📊   ││📈   ││📋   ││👤   ││💰   │
│Orch ││News ││Disc ││Chart││Repo ││User ││Flow │
│:8000││:8001││:8002││:8003││:8004││:8006││:8010│
└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘
   │      │      │      │      │      │      │
   └──────┼──────┼──────┼──────┼──────┼──────┘
          │      │      │      │      │
          ▼      ▼      ▼      ▼      ▼
     ┌─────────────────────────────────────┐
     │        🤖 LLM Manager               │
     │   HyperCLOVA • Gemini • OpenAI     │
     │         Claude • Grok               │
     └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              📊 데이터 레이어                                      │
├─────────────────────────────────┬───────────────────────────────────────────────┤
│          🗄️ MySQL              │            🧠 ChromaDB                        │
│        관계형 데이터베이스          │          벡터 데이터베이스                      │
│                                 │                                               │
│ • 사용자 설정 및 프로필           │ • 뉴스 임베딩 및 유사도 검색                    │
│ • 주식 기본 정보                 │ • 공시 문서 벡터화                            │
│ • 분석 결과 메타데이터            │ • 리포트 내용 검색                            │
│ • 시스템 로그 및 메트릭           │ • LLM 기반 의미 검색                          │
└─────────────────────────────────┴───────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                             🌐 외부 API 연동                                      │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────────┤
│   📡 DART API   │   📡 KIS API    │  📡 뉴스 API    │     📱 Telegram Bot         │
│                 │                 │                 │                             │
│ • 공시 정보 수집 │ • 실시간 시세    │ • 뉴스 데이터   │ • 실시간 알림 발송           │
│ • 기업 정보     │ • 차트 데이터    │ • 기사 분석     │ • 맞춤형 알림               │
│ • 재무 데이터   │ • 거래량 정보    │ • 키워드 추출   │ • 상황별 템플릿              │
└─────────────────┴─────────────────┴─────────────────┴─────────────────────────────┘
```

### 🔄 마이크로서비스 상세 구조

```
🎭 Orchestrator Service (포트: 8000)
├── 📋 워크플로우 관리
├── ⏰ 스케줄링 및 크론 작업
├── 🔄 서비스 간 조정
└── 📊 상태 모니터링

📰 News Service (포트: 8001)                📊 Disclosure Service (포트: 8002)
├── 🕷️ 뉴스 크롤링 (5분/1시간 간격)          ├── 📡 DART API 연동
├── 🧠 AI 기반 영향도 분석                   ├── 🤖 LLM 기반 공시 분석
├── 🔍 중복 제거 (SimHash + 벡터)           ├── 📈 중요도 필터링
└── 📱 고영향 뉴스 알림                      └── 💾 분석 결과 저장

📈 Chart Service (포트: 8003)               📋 Report Service (포트: 8004)
├── 📊 KIS API 실시간 차트                   ├── 📄 주간 종합 리포트
├── 🔍 8가지 기술적 패턴 분석                ├── 🔗 증권사 리서치 통합
├── 📈 지지/저항 라인 계산                   ├── 📊 트렌드 키워드 분석
└── 💡 매매 신호 생성                       └── 📱 PDF 리포트 생성

👤 User Service (포트: 8006)                💰 Flow Analysis Service (포트: 8010)
├── 👥 사용자 프로필 관리                    ├── 💹 기관/외국인 매매 분석
├── ⚙️ 개인화 설정                          ├── 📊 자금 흐름 패턴 인식
├── 📝 관심 종목 관리                       ├── 🎯 대량 거래 감지
└── 🔔 알림 설정                           └── 📈 매매 타이밍 분석
```

### 🌊 데이터 플로우

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  📡 외부 API │───▶│  🔄 수집     │───▶│  🧠 AI 분석  │───▶│  📊 결과     │
│             │    │             │    │             │    │             │
│ • DART      │    │ • 뉴스 크롤링│    │ • LLM 분석  │    │ • 영향도    │
│ • KIS       │    │ • 공시 수집 │    │ • 패턴 인식 │    │ • 신호 생성 │
│ • 뉴스 API  │    │ • 차트 수집 │    │ • 유사도 검색│    │ • 리포트    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                                ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  📱 알림     │◀───│  🌐 API     │◀───│  💾 저장     │◀───│  ✅ 검증     │
│             │    │  Gateway    │    │             │    │             │
│ • Telegram  │    │             │    │ • MySQL     │    │ • 품질 체크 │
│ • 실시간    │    │ • 라우팅    │    │ • ChromaDB  │    │ • 중복 제거 │
│ • 맞춤형    │    │ • 캐싱      │    │ • 벡터 DB   │    │ • 임계값    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 시스템 특징

#### 🔄 **마이크로서비스 아키텍처**

- **독립적 배포**: 각 서비스별 독립적인 개발/배포 가능
- **기술 스택 다양성**: 서비스별 최적화된 기술 선택
- **확장성**: 필요한 서비스만 스케일링 가능
- **장애 격리**: 한 서비스 장애가 전체 시스템에 미치는 영향 최소화

#### 🌐 **API Gateway 패턴**

- **통합 엔드포인트**: 모든 클라이언트 요청의 단일 진입점
- **라우팅 및 로드밸런싱**: 요청을 적절한 서비스로 라우팅
- **인증 및 권한 관리**: 중앙화된 보안 처리
- **캐싱 및 모니터링**: 성능 최적화 및 시스템 모니터링

#### 🤖 **LLM Manager 패턴**

- **다중 LLM 지원**: HyperCLOVA, Gemini, OpenAI, Claude 통합
- **사용자별 모델 선택**: 개인화된 AI 모델 사용
- **통일된 인터페이스**: 모든 LLM에 대한 일관된 API 제공

## 🔧 서비스 구성

| 서비스                 | 포트 | 역할            | 주요 기능                         |
| ---------------------- | ---- | --------------- | --------------------------------- |
| **API Gateway**        | 8005 | 통합 API 관리   | 라우팅, 인증, 캐싱, 모니터링      |
| **Orchestrator**       | 8000 | 워크플로우 관리 | 서비스 조정, 스케줄링, 상태 관리  |
| **News Service**       | 8001 | 뉴스 분석       | 뉴스 수집, 영향도 분석, 중복 제거 |
| **Disclosure Service** | 8002 | 공시 분석       | DART 공시 수집, LLM 분석          |
| **Chart Service**      | 8003 | 차트 분석       | 기술적 분석, 패턴 인식            |
| **Report Service**     | 8004 | 리포트 생성     | 주간 종합 리포트, PDF 생성        |
| **User Service**       | 8006 | 사용자 관리     | 설정 관리, 개인화                 |
| **Flow Analysis**      | 8010 | 자금흐름 분석   | 기관/외국인 매매 분석             |

### 📊 데이터 저장소

#### MySQL (관계형 데이터)

- 사용자 설정 및 프로필
- 주식 기본 정보
- 분석 결과 메타데이터
- 시스템 로그 및 메트릭

#### ChromaDB (벡터 데이터베이스)

- 뉴스 임베딩 및 유사도 검색
- 공시 문서 벡터화
- 리포트 내용 검색
- LLM 기반 의미 검색

## 🚀 실행 방법

### 1. 환경 설정

#### 가상환경 활성화

```bash
cd stock_analysis_service
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows
```

#### 필수 패키지 설치

```bash
pip install -r requirements.txt
```

#### 환경 변수 설정

`config/env_local.py` 파일에서 다음 설정을 확인하세요:

- MySQL 데이터베이스 연결 정보
- 외부 API 키 (DART, KIS, HyperCLOVA 등)
- Telegram Bot 토큰

### 2. 데이터베이스 초기화

```bash
python3 init_database.py
```

### 3. 모든 서비스 실행

#### 자동 실행 스크립트 (권장)

```bash
# macOS/Linux
chmod +x start_all_services.sh
./start_all_services.sh

# Windows
start_all_services.bat
```

#### 수동 실행 (개발용)

각 서비스를 개별적으로 실행:

```bash
# 환경 변수 설정
export PYTHONPATH=/path/to/stock_analysis_service

# 1. Orchestrator Service
cd services/orchestrator
nohup python3 main.py > ../../orchestrator_service.log 2>&1 &

# 2. News Service
cd ../news_service
nohup python3 main.py > ../../news_service.log 2>&1 &

# 3. Disclosure Service
cd ../disclosure_service
nohup python3 disclosure_service.py > ../../disclosure_service.log 2>&1 &

# 4. Chart Service
cd ../chart_service
nohup python3 chart_service.py > ../../chart_service.log 2>&1 &

# 5. Report Service
cd ../report_service
nohup python3 report_service.py > ../../report_service.log 2>&1 &

# 6. User Service
cd ../user_service
nohup python3 user_service.py > ../../user_service.log 2>&1 &

# 7. Flow Analysis Service
cd ../flow_analysis_service
nohup python3 flow_analysis_service.py --api > ../../flow_analysis_service.log 2>&1 &

# 8. API Gateway (마지막에 실행)
cd ../api_gateway
nohup python3 main.py > ../../api_gateway.log 2>&1 &
```

### 4. 서비스 상태 확인

#### 개별 서비스 헬스체크

```bash
curl http://localhost:8000/health  # Orchestrator
curl http://localhost:8001/health  # News Service
curl http://localhost:8002/health  # Disclosure Service
curl http://localhost:8003/health  # Chart Service
curl http://localhost:8004/health  # Report Service
curl http://localhost:8005/health  # API Gateway
curl http://localhost:8006/health  # User Service
curl http://localhost:8010/health  # Flow Analysis
```

#### 통합 테스트

```bash
python3 test_api_gateway.py
```

### 5. 서비스 종료

```bash
# 모든 Python 서비스 종료
pkill -f "python3.*service"
pkill -f "python3.*main.py"
```

## 📚 API 문서

### API Gateway 엔드포인트

#### 기본 엔드포인트

- `GET /health` - API Gateway 헬스체크
- `GET /services/status` - 모든 서비스 상태 조회
- `GET /metrics` - Prometheus 메트릭

#### 서비스별 API (모든 API는 `/api/` 접두사 사용)

##### 🎭 Orchestrator API

- `GET /api/orchestrator/health` - 헬스체크
- `GET /api/orchestrator/services` - 서비스 목록
- `POST /api/orchestrator/start/{service_name}` - 서비스 시작
- `POST /api/orchestrator/stop/{service_name}` - 서비스 중지

##### 📰 News API

- `GET /api/news/health` - 헬스체크
- `GET /api/news/signal` - 최근 뉴스 신호
- `POST /api/news/execute` - 뉴스 분석 실행

##### 📊 Disclosure API

- `GET /api/disclosure/health` - 헬스체크
- `GET /api/disclosure/recent` - 최근 공시 조회
- `POST /api/disclosure/execute` - 공시 분석 실행

##### 📈 Chart API

- `GET /api/chart/health` - 헬스체크
- `GET /api/chart/analysis/{stock_code}` - 종목 차트 분석
- `POST /api/chart/execute` - 차트 분석 실행

##### 📋 Report API

- `GET /api/report/health` - 헬스체크
- `GET /api/report/latest` - 최근 리포트
- `GET /api/report/history` - 리포트 이력

##### 👤 User API

- `GET /api/user/health` - 헬스체크
- `GET /api/user/config/{user_id}` - 사용자 설정 조회
- `PUT /api/user/config/{user_id}` - 사용자 설정 업데이트
- `GET /api/user/stocks/{user_id}` - 관심 종목 조회

##### 💰 Flow Analysis API

- `GET /api/flow/health` - 헬스체크
- `GET /api/flow/analysis/{stock_code}` - 자금흐름 분석
- `POST /api/flow/execute` - 분석 실행

### API 사용 예시

```bash
# 뉴스 서비스 상태 확인
curl -X GET "http://localhost:8005/api/news/health"

# 특정 종목 차트 분석
curl -X GET "http://localhost:8005/api/chart/analysis/005930"

# 사용자 설정 조회
curl -X GET "http://localhost:8005/api/user/config/1"

# 모든 서비스 상태 조회
curl -X GET "http://localhost:8005/services/status"
```

## 🧪 테스트

### 연결성 테스트

```bash
# API Gateway와 모든 서비스 연결 테스트
python3 test_api_gateway.py
```

### 개별 서비스 테스트

```bash
# 뉴스 서비스 테스트
python3 services/news_service/test_news.py

# 공시 서비스 테스트
python3 test_disclosure_service.py

# 차트 서비스 테스트
python3 test_chart_analysis_data.py
```

### 성능 테스트

```bash
# API Gateway 성능 테스트
python3 test_performance.py
```

## 🛠️ 기술 스택

### 백엔드 프레임워크

- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증 및 설정 관리

### 데이터베이스

- **MySQL**: 관계형 데이터 저장
- **ChromaDB**: 벡터 데이터베이스 (임베딩 검색)

### 외부 API 연동

- **DART API**: 공시 정보 수집
- **KIS API**: 주식 시세 데이터
- **뉴스 API**: 실시간 뉴스 수집

### AI/ML 서비스

- **HyperCLOVA**: 네이버 클라우드 LLM
- **Google Gemini**: 구글 AI 모델
- **OpenAI GPT**: OpenAI API
- **Claude**: Anthropic AI 모델

### 모니터링 및 메트릭

- **Prometheus**: 메트릭 수집
- **Structlog**: 구조화된 로깅
- **Circuit Breaker**: 장애 격리

### 알림 서비스

- **Telegram Bot**: 실시간 알림 발송

### 개발 도구

- **Python 3.9+**: 주 개발 언어
- **AsyncIO**: 비동기 프로그래밍
- **aiohttp**: 비동기 HTTP 클라이언트
- **SQLAlchemy**: ORM (선택적)

## 📁 프로젝트 구조

```
stock_analysis_service/
├── services/                 # 마이크로서비스들
│   ├── api_gateway/         # API Gateway
│   ├── orchestrator/        # 오케스트레이터
│   ├── news_service/        # 뉴스 서비스
│   ├── disclosure_service/  # 공시 서비스
│   ├── chart_service/       # 차트 서비스
│   ├── report_service/      # 리포트 서비스
│   ├── user_service/        # 사용자 서비스
│   └── flow_analysis_service/ # 자금흐름 서비스
├── shared/                  # 공통 모듈
│   ├── apis/               # 외부 API 클라이언트
│   ├── database/           # 데이터베이스 연결
│   └── llm/               # LLM Manager
├── config/                 # 설정 파일
├── database/              # DB 스키마
├── static/               # 정적 파일
├── templates/            # 템플릿 파일
├── logs/                # 로그 파일
└── tests/              # 테스트 파일
```

## 🔧 설정 및 환경변수

### 필수 환경변수

```bash
# 데이터베이스
DATABASE_HOST=your-mysql-host
DATABASE_USER=your-username
DATABASE_PASSWORD=your-password
DATABASE_NAME=your-database
DATABASE_CONNECTION_LIMIT=1

# 외부 API
DART_API_KEY=your-dart-api-key
KIS_APP_KEY=your-kis-app-key
KIS_APP_SECRET=your-kis-app-secret
HYPERCLOVA_API_KEY=your-hyperclova-key

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

## 🚨 트러블슈팅

### 일반적인 문제들

#### 1. MySQL 연결 한계 초과

**증상**: `(1040, 'Too many connections')` 에러
**해결책**:

- `DATABASE_CONNECTION_LIMIT=1` 설정
- MySQL `max_connections` 증가

#### 2. 포트 충돌

**증상**: `Address already in use` 에러
**해결책**:

```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8005
# 프로세스 종료
kill -9 <PID>
```

#### 3. PYTHONPATH 문제

**증상**: `ModuleNotFoundError: No module named 'shared'`
**해결책**:

```bash
export PYTHONPATH=/path/to/stock_analysis_service
```

#### 4. 권한 문제

**증상**: Permission denied
**해결책**:

```bash
chmod +x start_all_services.sh
```

### 로그 확인

```bash
# 서비스별 로그 확인
tail -f orchestrator_service.log
tail -f news_service.log
tail -f api_gateway.log
```

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원 및 문의

- 이슈 리포트: [GitHub Issues](https://github.com/your-repo/issues)
- 문서: [Wiki](https://github.com/your-repo/wiki)
- 이메일: your-email@example.com

---

**Made with ❤️ by Stock Analysis Team**
