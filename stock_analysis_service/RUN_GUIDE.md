# 🚀 주식 분석 시스템 실행 가이드

## ✅ 완료된 구현

**8개 마이크로서비스 + 오케스트레이터 + 공유 모듈 = 100% 완성!**

### 📋 구현된 서비스 목록

1. **🔧 오케스트레이터 서비스** (`services/orchestrator/main.py`)
   - 모든 서비스 자동 관리 및 헬스체크
   - FastAPI 웹 인터페이스 (포트: 8000)
   - 자동 재시작 및 복구 기능

2. **📰 뉴스 크롤링 서비스** (`services/news_service/news_service.py`)
   - 장중 5분, 장외 1시간 간격 크롤링
   - 중복 제거 + LLM 영향력 평가
   - 과거 사례 검색 + 텔레그램 알림

3. **📋 공시 서비스** (`services/disclosure_service/disclosure_service.py`)
   - DART API 연동 공시 수집
   - 키워드 기반 필터링 + LLM 분석
   - 유사 사례 검색 + 알림

4. **📊 차트 분석 서비스** (`services/chart_service/chart_service.py`)
   - KIS API 실시간 차트 데이터
   - 8개 조건식 모니터링 (골든크로스, 볼린저밴드 등)
   - 조건 만족 시 즉시 알림

5. **🔔 알림 서비스** (`services/notification_service/notification_service.py`)
   - 텔레그램 봇 통합 알림
   - 메시지 템플릿 관리
   - 알림 히스토리 및 우선순위 처리

6. **📋 주간 보고서 서비스** (`services/report_service/report_service.py`)
   - 매주 일요일 18:00 자동 실행
   - 리서치 보고서 크롤링 (네이버 금융 PDF)
   - 핵심 키워드 생성 및 종합 분석

7. **🔍 주가 원인 분석 서비스** (`services/analysis_service/analysis_service.py`)
   - 10% 이상 + 1000만주 이상 급등락 감지
   - LLM 기반 원인 분석
   - 과거 유사 사례 검색

8. **📈 모니터링 대시보드** (`services/monitoring_service/monitoring_service.py`)
   - Streamlit 실시간 대시보드 (포트: 8501)
   - 시스템 메트릭 및 서비스 상태 모니터링
   - 에러 추적 및 성능 지표

## 🛠️ 시스템 요구사항

### 필수 환경변수 (8개)
```bash
# MySQL 데이터베이스
MYSQL_HOST=your_mysql_host
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=your_database_name

# API 키들
NAVER_CLOVA_API_KEY=nv-bf80899d661e4ec6bc01257f024f0c29CG8M
DART_API_KEY=c734e72eb6cdc78a5677e7650e050652f2e78f0b
TELEGRAM_BOT_TOKEN=7804706615:AAF_1WH5LZFa5mWktH3CZiHHKf98WRp4Buo
TELEGRAM_CHAT_ID=1002263561615
```

### 데이터베이스 구조
- **5개 MySQL 테이블**: 뉴스, 공시, 차트 조건, 알림 히스토리, 주간 키워드
- **4개 ChromaDB 컬렉션**: 고영향 뉴스, 과거 사례, 공시, 주간 보고서

## 🚀 실행 방법

### 1단계: 패키지 설치
```bash
# Windows
.\install.bat

# Mac/Linux  
./install.sh
```

### 2단계: 환경변수 설정
```bash
# config/env_local.py 파일에서 설정 확인
```

### 3단계: 전체 시스템 실행
```bash
# 오케스트레이터를 통한 자동 실행 (권장)
python services/orchestrator/main.py

# 개별 서비스 실행도 가능
python -m services.news_service.news_service
python -m services.disclosure_service.disclosure_service
# ... 기타 서비스들
```

### 4단계: 웹 인터페이스 접근
- **오케스트레이터 API**: http://localhost:8000
- **모니터링 대시보드**: http://localhost:8501

## 📊 주요 기능

### 🔄 실시간 모니터링
- 장중(09:00-15:30): 5분 간격 뉴스, 10분 간격 급등락 분석
- 장외: 1시간 간격 공시 및 뉴스 체크
- 24시간: 시스템 메트릭 수집

### 📱 알림 시스템
- **뉴스 알림**: 영향도 0.7 이상
- **공시 알림**: 영향도 0.7 이상  
- **차트 알림**: 8개 조건 만족 시
- **급등락 분석**: 10% 이상 변동 + 1000만주 이상

### 📈 주간 보고서
- 매주 일요일 18:00 자동 생성
- 리서치 보고서 PDF 분석
- 핵심 키워드 추출 및 저장

### 🎯 대상 종목
- 기본: 006800 (미래에셋증권)
- 확장 가능: `config/stocks.json`에서 설정

## 🔧 API 엔드포인트

### 오케스트레이터 API (포트: 8000)
```
GET  /services              # 모든 서비스 상태 조회
POST /services/start-all     # 모든 서비스 시작
POST /services/stop-all      # 모든 서비스 중단
POST /services/{name}/start  # 개별 서비스 시작
POST /services/{name}/stop   # 개별 서비스 중단
POST /services/{name}/restart # 개별 서비스 재시작
```

## 🏗️ 아키텍처 설계

### 마이크로서비스 구조
```
오케스트레이터 (8000)
├── 뉴스 서비스 (8001)
├── 공시 서비스 (8002)  
├── 차트 분석 (8003)
├── 알림 서비스 (8004)
├── 주간 보고서 (8005)
├── 원인 분석 (8006)
└── 모니터링 (8501)
```

### 공유 모듈
```
shared/
├── database/           # MySQL + ChromaDB 클라이언트
├── llm/               # HyperCLOVA X API
├── apis/              # KIS, DART, Telegram API
└── utils/             # 공통 유틸리티
```

## 🔍 모니터링 & 디버깅

### 로그 확인
- 각 서비스별 개별 로그 출력
- 오케스트레이터에서 통합 상태 관리
- 텔레그램으로 크리티컬 에러 알림

### 성능 지표
- CPU, 메모리, 디스크 사용률
- 서비스별 처리량 및 응답 시간
- 데이터베이스 연결 상태

## ⚠️ 주의사항

1. **API 호출 제한**: 각 API별 호출 빈도 제한 준수
2. **데이터 정리**: 벡터 DB는 매일 자정 임시 데이터 삭제
3. **메모리 관리**: 차트 분석 시 메모리 사용량 높을 수 있음
4. **네트워크**: 크롤링 시 안정적인 인터넷 연결 필요

## 🔄 자동 복구 기능

- **프로세스 크래시**: 자동 재시작 (최대 3회)
- **메모리 누수**: 정기적 프로세스 재시작
- **네트워크 오류**: 재시도 로직 내장
- **데이터베이스 연결**: 자동 재연결

